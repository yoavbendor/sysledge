"""Apply-authority: the single, reversible writer to the SysML model tree.

For each queued patch it: snapshots the target file, applies the edit, runs the
nomograph validator (per-file `validate` + cross-file `index`), and either commits
(move patch to applied/, append a log.md entry) or rolls back byte-for-byte (restore
snapshot, move patch to rejected/ with the validator output). This makes
machine-generated edits safe: an invalid fragment can never land, because the model
file is restored the instant validation fails.

The text editing is intentionally best-effort — validation is the real guard, so a
malformed edit simply fails and is reverted rather than corrupting the model.

Stdlib only. The validator is injectable so tests run offline (no nomograph/network).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .queue import Patch, PatchError, Queue


# --------------------------------------------------------------------------- result
@dataclass
class Result:
    patch_id: str
    status: str  # "applied" | "rejected"
    detail: str


# ----------------------------------------------------------------------- validators
def nomograph_validator(repo_root: Path, target_file: Path) -> tuple[bool, str]:
    """Default validator: `nomograph-sysml validate <file>` then a full `index`
    (the index pass catches cross-file dangling references)."""
    val = subprocess.run(
        ["nomograph-sysml", "validate", str(target_file)],
        cwd=repo_root, capture_output=True, text=True,
    )
    out = (val.stdout + val.stderr)
    valid = val.returncode == 0 and '"valid": false' not in out and '"valid":false' not in out
    if not valid:
        return False, f"validate failed:\n{out[-1000:]}"
    idx = subprocess.run(
        ["nomograph-sysml", "index", "lib", "models", "--output", ".nomograph/index.json"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if idx.returncode != 0:
        return False, f"index failed (cross-file refs?):\n{(idx.stdout + idx.stderr)[-1000:]}"
    return True, "valid"


# ----------------------------------------------------------------------- text edits
def _matching_brace(text: str, open_idx: int) -> int:
    """Index of the `}` matching the `{` at `open_idx`."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("unbalanced braces")


def _package_body_end(text: str, name: str) -> int:
    """Index of the closing `}` of `package <name>` (tries the last `::` segment too)."""
    for candidate in (name, name.split("::")[-1]):
        m = re.search(r"\bpackage\s+" + re.escape(candidate) + r"\b", text)
        if m:
            brace = text.index("{", m.end())
            return _matching_brace(text, brace)
    # Fall back to the last top-level closing brace in the file.
    idx = text.rfind("}")
    if idx == -1:
        raise ValueError(f"no package {name!r} and no closing brace in target file")
    return idx


def _element_block(text: str, anchor: str) -> tuple[int, int]:
    """(start, end) char span of the statement/block declaring `anchor`."""
    m = re.search(r"\b" + re.escape(anchor) + r"\b", text)
    if not m:
        raise ValueError(f"anchor {anchor!r} not found")
    start = text.rfind("\n", 0, m.start()) + 1
    semi = text.find(";", m.end())
    brace = text.find("{", m.end())
    if brace != -1 and (semi == -1 or brace < semi):
        end = _matching_brace(text, brace) + 1
    elif semi != -1:
        end = semi + 1
    else:
        end = len(text)
    return start, end


def _indent_for(text: str, pos: int) -> str:
    line_start = text.rfind("\n", 0, pos) + 1
    ws = re.match(r"[ \t]*", text[line_start:pos])
    return ws.group(0) if ws else "    "


def apply_edit(text: str, patch: Patch) -> str:
    """Return the new file text after applying `patch` (pure string transform)."""
    frag = patch.sysml.strip("\n")
    if patch.op in ("add", "promote_to_lib"):
        if patch.anchor:
            _, end = _element_block(text, patch.anchor)
            return text[:end] + "\n\n" + frag + text[end:]
        close = _package_body_end(text, patch.target_package)
        indent = "    "
        block = "\n" + "\n".join(indent + ln if ln.strip() else ln for ln in frag.splitlines()) + "\n"
        return text[:close] + block + text[close:]
    if patch.op == "modify":
        start, end = _element_block(text, patch.anchor or "")
        return text[:start] + frag + "\n" + text[end:].lstrip("\n")
    if patch.op == "remove":
        start, end = _element_block(text, patch.anchor or "")
        tail = text[end:]
        return text[:start].rstrip(" ") + tail.lstrip("\n")
    raise ValueError(f"unsupported op {patch.op!r}")


# ------------------------------------------------------------------- apply authority
def _snapshot(repo_root: Path, rel: str) -> tuple[Path, bytes | None]:
    src = repo_root / rel
    snap_dir = repo_root / ".snapshots" / time.strftime("%Y%m%dT%H%M%S")
    snap = snap_dir / rel
    snap.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, snap)
        return snap, src.read_bytes()
    return snap, None


def _restore(repo_root: Path, rel: str, original: bytes | None) -> None:
    dest = repo_root / rel
    if original is None:
        if dest.exists():
            dest.unlink()
    else:
        dest.write_bytes(original)


def _append_log(repo_root: Path, patch: Patch, target: Path) -> None:
    line = (
        f"\n- {time.strftime('%Y-%m-%d')} **{patch.op}** `{target}` "
        f"(agent={patch.agent}, source={patch.provenance.source}, "
        f"maturity={patch.provenance.maturity}): {patch.rationale or 'patch applied'} "
        f"[patch {patch.id}]\n"
    )
    log = repo_root / "log.md"
    with log.open("a", encoding="utf-8") as f:
        f.write(line)


def apply_one(
    patch: Patch,
    repo_root: Path,
    validator=nomograph_validator,
    dry_run: bool = False,
) -> Result:
    """Snapshot → edit → validate → commit-or-rollback. Never raises on a bad edit;
    returns a rejected Result instead."""
    try:
        patch.validate_patch()
    except PatchError as e:
        return Result(patch.id, "rejected", f"schema: {e}")

    rel = patch.target_file
    target = repo_root / rel
    if not target.exists() and patch.op != "add" and patch.op != "promote_to_lib":
        return Result(patch.id, "rejected", f"target {rel} does not exist for op {patch.op}")

    snap, original = _snapshot(repo_root, rel)
    try:
        text = target.read_text(encoding="utf-8") if target.exists() else f"package {patch.target_package} {{\n}}\n"
        new_text = apply_edit(text, patch)
    except Exception as e:  # best-effort editor; treat failures as rejection
        _restore(repo_root, rel, original)
        return Result(patch.id, "rejected", f"edit failed: {e}")

    # Atomic write of the edited file.
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, target)

    ok, detail = validator(repo_root, target)
    if ok and not dry_run:
        _append_log(repo_root, patch, target)
        return Result(patch.id, "applied", detail)

    # rollback (always, for dry-run; or on failure)
    _restore(repo_root, rel, original)
    if dry_run and ok:
        return Result(patch.id, "applied", f"dry-run ok (reverted): {detail}")
    return Result(patch.id, "rejected", detail)


# ------------------------------------------------------------------------- lock/drain
class LockHeld(RuntimeError):
    pass


def _acquire_lock(queue_base: Path) -> Path:
    lock = queue_base / ".lock"
    queue_base.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            pid = int(lock.read_text().strip() or "0")
            os.kill(pid, 0)  # alive?
            raise LockHeld(f"queue locked by pid {pid}")
        except (ProcessLookupError, ValueError):
            lock.unlink(missing_ok=True)  # stale; retake
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    return lock


def drain(repo_root: Path, validator=nomograph_validator, dry_run: bool = False) -> list[Result]:
    """Process all incoming patches under a single-writer lock. Returns results."""
    repo_root = Path(repo_root)
    q = Queue(repo_root).ensure_dirs()
    lock = _acquire_lock(q.base)
    results: list[Result] = []
    try:
        for path, patch in q.iter_incoming():
            res = apply_one(patch, repo_root, validator=validator, dry_run=dry_run)
            results.append(res)
            if not dry_run:
                q.move(path, res.status, extra={"result": res.detail[:2000]})
    finally:
        lock.unlink(missing_ok=True)
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="sysledge-apply",
        description="Apply queued SysML patches with validate-or-rollback.",
    )
    ap.add_argument("--repo", default=".", type=Path, help="repo root (default: .)")
    ap.add_argument("--once", action="store_true", help="process current incoming then exit")
    ap.add_argument("--dry-run", action="store_true", help="validate edits but revert all")
    args = ap.parse_args(argv)

    try:
        results = drain(args.repo, dry_run=args.dry_run)
    except LockHeld as e:
        print(f"SKIP: {e}")
        return 2

    applied = sum(r.status == "applied" for r in results)
    rejected = sum(r.status == "rejected" for r in results)
    for r in results:
        mark = "✓" if r.status == "applied" else "✗"
        print(f"  {mark} {r.patch_id} [{r.status}] {r.detail.splitlines()[0] if r.detail else ''}")
    print(f"{applied} applied, {rejected} rejected"
          + (" (dry-run)" if args.dry_run else ""))
    return 1 if rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())
