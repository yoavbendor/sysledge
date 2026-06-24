"""Patch queue for machine-generated edits to the SysML models.

A `Patch` is a single proposed edit to one file under `models/` or `lib/`. Agents
(Layer B) only ever *enqueue* patches; the apply-authority (`authority.py`) is the
sole writer to the model tree. This module is the schema + the file-backed queue.

Design notes:
- **Lean + pydantic.** Patches are `pydantic.BaseModel`s, so machine-generated input
  (LLM → JSON) is validated at parse time — the right place to reject a malformed or
  unsourced patch. The rest stays stdlib: atomic `os.replace`, a sortable id, FIFO dirs
  (no filelock/ULID).
- **Guardrail in code, not convention.** Validation rejects any add/modify whose
  fragment lacks `@Provenance` (CLAUDE.md hard guardrail #1) and any patch whose target
  escapes `models/`/`lib/`. `Patch.parse(...)` surfaces every failure as `PatchError`.
- **Atomic, FIFO, crash-safe.** Each patch is a JSON file named by a time-sortable id
  under `queue/{incoming,applied,rejected}/`; producers write a temp file then
  `os.replace` into place (unique names ⇒ no producer lock needed).
"""

from __future__ import annotations

import os
import secrets
import time
from pathlib import Path
from typing import Iterator, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

OPS = ("add", "modify", "remove", "promote_to_lib")
MATURITIES = ("concept", "designed", "implemented", "verified")
EDIT_OPS = ("add", "modify")  # ops whose `sysml` must carry @Provenance
STATUSES = ("incoming", "applied", "rejected")


class PatchError(Exception):
    """A patch violated a hard guardrail (provenance, maturity, path-safety, schema).

    Deliberately not a ValueError so pydantic propagates it from validators unwrapped,
    giving callers a single, uniform exception type via `Patch.parse(...)`.
    """


def new_id() -> str:
    """Lexicographically time-ordered id (no ULID dependency)."""
    return f"{time.time_ns():020d}-{secrets.token_hex(4)}"


class Provenance(BaseModel):
    source: str = Field(min_length=1)
    maturity: Literal["concept", "designed", "implemented", "verified"]


class Patch(BaseModel):
    op: Literal["add", "modify", "remove", "promote_to_lib"]
    target_file: str  # repo-relative, e.g. "models/nanos3reader/structure.sysml"
    target_package: str
    sysml: str = ""
    provenance: Provenance
    agent: str = "unknown"
    rationale: str = ""
    grade: float = 0.0
    anchor: Optional[str] = None  # element name to anchor at, or None to append
    id: str = Field(default_factory=new_id)
    created: float = Field(default_factory=time.time)

    @model_validator(mode="after")
    def _guardrails(self) -> "Patch":
        # No fact without provenance: add/modify fragments must carry @Provenance.
        if self.op in EDIT_OPS and "@Provenance" not in (self.sysml or ""):
            raise PatchError(
                f"{self.op} fragment must carry an @Provenance annotation "
                f"(hard guardrail: no fact without provenance)"
            )
        # Path-safety: repo-relative, under models/ or lib/, no escapes.
        tf = Path(self.target_file)
        if tf.is_absolute() or ".." in tf.parts:
            raise PatchError(f"target_file {self.target_file!r} must be relative, no '..'")
        top = tf.parts[0] if tf.parts else ""
        if top not in ("models", "lib"):
            raise PatchError(
                f"target_file {self.target_file!r} must live under models/ or lib/"
            )
        return self

    # --- parse / (de)serialize --------------------------------------------------
    @classmethod
    def parse(cls, data: dict) -> "Patch":
        """Build a Patch from a (possibly machine-generated) dict, surfacing any
        validation failure as a single `PatchError`."""
        try:
            return cls.model_validate(data)
        except PatchError:
            raise
        except ValidationError as e:
            raise PatchError(str(e)) from e

    def validate_patch(self) -> "Patch":
        """Re-run guardrails (a constructed Patch is already valid). Kept for callers
        that want an explicit gate before enqueue."""
        return Patch.parse(self.model_dump())

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, text: str) -> "Patch":
        try:
            return cls.model_validate_json(text)
        except ValidationError as e:
            raise PatchError(str(e)) from e


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}.{secrets.token_hex(2)}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class Queue:
    """File-backed patch queue rooted at `<root>/queue/`."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.base = self.root / "queue"
        self.dirs = {s: self.base / s for s in STATUSES}

    def ensure_dirs(self) -> "Queue":
        for d in self.dirs.values():
            d.mkdir(parents=True, exist_ok=True)
        return self

    def enqueue(self, patch: Patch) -> Path:
        """Validate and atomically write the patch into incoming/."""
        patch.validate_patch()
        self.ensure_dirs()
        dest = self.dirs["incoming"] / f"{patch.id}.json"
        _atomic_write(dest, patch.to_json())
        return dest

    def iter_incoming(self) -> Iterator[tuple[Path, Patch]]:
        """Yield (path, patch) for incoming patches, FIFO by sortable id."""
        inc = self.dirs["incoming"]
        if not inc.exists():
            return
        for p in sorted(inc.glob("*.json")):
            yield p, Patch.from_json(p.read_text(encoding="utf-8"))

    def move(self, path: Path, status: str, extra: dict | None = None) -> Path:
        """Atomically move a patch file to applied/ or rejected/, merging `extra`."""
        import json

        if status not in ("applied", "rejected"):
            raise ValueError(f"move target must be applied/rejected, got {status!r}")
        self.ensure_dirs()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if extra:
            data.update(extra)
        dest = self.dirs[status] / Path(path).name
        _atomic_write(dest, json.dumps(data, indent=2, sort_keys=True))
        os.remove(path)
        return dest
