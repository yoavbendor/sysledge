"""Patch queue for machine-generated edits to the SysML models.

A `Patch` is a single proposed edit to one file under `models/` or `lib/`. Agents
(Layer B) only ever *enqueue* patches; the apply-authority (`authority.py`) is the
sole writer to the model tree. This module is the schema + the file-backed queue.

Design notes:
- **Stdlib only.** No pydantic/filelock/ULID — `dataclasses`, atomic `os.replace`,
  and a sortable stdlib id keep the safety net dependency-free.
- **Guardrail in code, not convention.** `Patch.validate()` rejects any add/modify
  whose fragment lacks `@Provenance` (CLAUDE.md hard guardrail #1) and any patch
  whose target escapes `models/`/`lib/`.
- **Atomic, FIFO, crash-safe.** Each patch is a JSON file named by a time-sortable
  id under `queue/{incoming,applied,rejected}/`; producers write a temp file then
  `os.replace` into place (unique names ⇒ no producer lock needed).
"""

from __future__ import annotations

import dataclasses
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

OPS = ("add", "modify", "remove", "promote_to_lib")
MATURITIES = ("concept", "designed", "implemented", "verified")
EDIT_OPS = ("add", "modify")  # ops whose `sysml` must carry @Provenance
STATUSES = ("incoming", "applied", "rejected")


class PatchError(ValueError):
    """A patch violated a hard guardrail (provenance, maturity, path-safety, schema)."""


def new_id() -> str:
    """Lexicographically time-ordered id (no ULID dependency)."""
    return f"{time.time_ns():020d}-{secrets.token_hex(4)}"


@dataclass
class Patch:
    op: str
    target_file: str  # repo-relative, e.g. "models/nanos3reader/structure.sysml"
    target_package: str
    sysml: str
    provenance: dict  # {"source": str, "maturity": str}
    agent: str = "unknown"
    rationale: str = ""
    grade: float = 0.0
    anchor: str | None = None  # element name to anchor at, or None to append
    id: str = field(default_factory=new_id)
    created: float = field(default_factory=time.time)

    # --- validation -------------------------------------------------------------
    def validate(self) -> "Patch":
        """Raise PatchError unless the patch satisfies every hard guardrail."""
        if self.op not in OPS:
            raise PatchError(f"unknown op {self.op!r}; expected one of {OPS}")

        prov = self.provenance or {}
        source = prov.get("source")
        maturity = prov.get("maturity")
        if not source:
            raise PatchError("provenance.source is required (no fact without provenance)")
        if maturity not in MATURITIES:
            raise PatchError(
                f"provenance.maturity {maturity!r} invalid; expected one of {MATURITIES}"
            )

        if self.op in EDIT_OPS and "@Provenance" not in (self.sysml or ""):
            raise PatchError(
                f"{self.op} fragment must carry an @Provenance annotation "
                f"(hard guardrail: no fact without provenance)"
            )

        # Path-safety: must be a repo-relative path under models/ or lib/, no escapes.
        tf = Path(self.target_file)
        if tf.is_absolute() or ".." in tf.parts:
            raise PatchError(f"target_file {self.target_file!r} must be relative, no '..'")
        top = tf.parts[0] if tf.parts else ""
        if top not in ("models", "lib"):
            raise PatchError(
                f"target_file {self.target_file!r} must live under models/ or lib/"
            )
        return self

    # --- (de)serialization ------------------------------------------------------
    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, d: dict) -> "Patch":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})

    @classmethod
    def from_json(cls, text: str) -> "Patch":
        return cls.from_dict(json.loads(text))


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
        patch.validate()
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
