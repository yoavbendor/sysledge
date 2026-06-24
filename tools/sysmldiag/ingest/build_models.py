"""Multi-system driver: config + docs -> agents -> queue -> apply -> reindex.

Reads `sysledge.toml` (a list of `[[systems]]`), and for each system walks its docs
through the Layer B agents (`agents.py`), enqueues the resulting patches, and lets the
apply-authority (`authority.py`) validate-or-roll-back each one. After anything lands it
reindexes, regenerates the diagrams, and keeps `models/index.sysml` importing the
system's packages.

This is the orchestration glue only — it owns no model-writing of its own (that stays in
`authority.py`). Every external effect (LLM, validator, reindex, diagram regen) is an
injected callable, so the whole driver is exercised offline in tests with fakes.

Config (`sysledge.toml`):

    [[systems]]
    id = "nanos3reader"               # also the raw/<id>/ registry dir
    package = "Nanos3reader"          # package base; aspects append Structure/Requirements/Behavior
    model_dir = "models/nanos3reader"
    docs = ["raw/nanos3reader/*.md"]  # globs or files, relative to the repo root
    source_id = "nanos3reader@ff28f0b"  # optional; else derived from raw/<id>/manifest.yaml
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from ..ingest_eval.doc_reader import DocReadError, read_doc
from ..graph import Graph
from ..llm import LLMError
from ..llm import complete as llm_complete
from . import agents
from .authority import drain, nomograph_validator
from .queue import Queue

# tomllib is stdlib on 3.11+; fall back to the tiny `tomli` backport on 3.10.
try:  # pragma: no cover - import shim
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover
    import tomli as _toml  # type: ignore

INDEX_FILE = "models/index.sysml"
# Distinct aspect packages an agent may write, in index order.
ASPECTS = [("Requirements", "requirements.sysml"), ("Structure", "structure.sysml"),
           ("Behavior", "behavior.sysml")]


# --------------------------------------------------------------------------- config
@dataclass
class SystemConfig:
    id: str
    package: str
    model_dir: str
    docs: list[str] = field(default_factory=list)
    source_id: Optional[str] = None


def load_systems(config_path: Path) -> list[SystemConfig]:
    data = _toml.loads(Path(config_path).read_text(encoding="utf-8"))
    out: list[SystemConfig] = []
    for s in data.get("systems", []):
        out.append(
            SystemConfig(
                id=s["id"],
                package=s["package"],
                model_dir=s["model_dir"],
                docs=list(s.get("docs", [])),
                source_id=s.get("source_id"),
            )
        )
    return out


_MANIFEST_ID = re.compile(r"^\s*-\s*id:\s*(\S+)", re.M)


def source_id_for(repo_root: Path, cfg: SystemConfig) -> str:
    """The provenance source-id prefix: explicit in config, else the first `id:` in
    `raw/<id>/manifest.yaml`, else the bare system id."""
    if cfg.source_id:
        return cfg.source_id
    manifest = Path(repo_root) / "raw" / cfg.id / "manifest.yaml"
    if manifest.exists():
        m = _MANIFEST_ID.search(manifest.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return cfg.id


def resolve_docs(repo_root: Path, patterns: list[str]) -> list[Path]:
    repo_root = Path(repo_root)
    found: list[Path] = []
    for pat in patterns:
        matches = sorted(repo_root.glob(pat))
        if matches:
            found.extend(matches)
        elif (repo_root / pat).exists():
            found.append(repo_root / pat)
    # de-dup, keep order
    seen: set[Path] = set()
    return [p for p in found if not (p in seen or seen.add(p))]


# ----------------------------------------------------------------------- side effects
def _reindex(repo_root: Path) -> tuple[bool, str]:
    r = subprocess.run(
        ["nomograph-sysml", "index", "lib", "models", "--output", ".nomograph/index.json"],
        cwd=repo_root, capture_output=True, text=True,
    )
    return r.returncode == 0, (r.stdout + r.stderr)[-500:]


def _regen_diagrams(repo_root: Path) -> tuple[bool, str]:
    r = subprocess.run(
        [sys.executable, "-m", "sysmldiag", "--views", "all"],
        cwd=repo_root, capture_output=True, text=True,
        env={**_env_with_tools()},
    )
    return r.returncode == 0, (r.stdout + r.stderr)[-500:]


def _env_with_tools() -> dict:
    import os
    env = dict(os.environ)
    tools = str(Path(__file__).resolve().parents[2])  # .../tools
    env["PYTHONPATH"] = tools + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def ensure_index_imports(repo_root: Path, package_base: str, model_dir: str) -> list[str]:
    """Make sure `models/index.sysml` imports each existing aspect package of the system.
    Returns the import lines that were added (empty if already present)."""
    index = Path(repo_root) / INDEX_FILE
    if not index.exists():
        return []
    text = index.read_text(encoding="utf-8")
    added: list[str] = []
    for suffix, fname in ASPECTS:
        if not (Path(repo_root) / model_dir / fname).exists():
            continue
        stmt = f"import {package_base}{suffix}::*;"
        if stmt in text:
            continue
        added.append(stmt)
    if not added:
        return []
    close = text.rfind("}")
    insertion = "".join(f"    {s}\n" for s in added)
    new = text[:close] + insertion + text[close:]
    index.write_text(new, encoding="utf-8")
    return added


# ----------------------------------------------------------------------------- driver
@dataclass
class BuildReport:
    system: str
    source_id: str
    docs: int = 0
    scanned: int = 0
    kept: int = 0
    dropped: int = 0
    contradictions: int = 0
    enqueued: int = 0
    applied: int = 0
    rejected: int = 0
    imports_added: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def build_system(
    cfg: SystemConfig,
    repo_root: Path,
    *,
    complete: Callable[..., str] = llm_complete,
    llm_cfg=None,
    use_llm: bool = True,
    do_connect: bool = False,
    validator: Callable = nomograph_validator,
    reindex: Callable[[Path], tuple[bool, str]] = _reindex,
    regen_diagrams: Callable[[Path], tuple[bool, str]] = _regen_diagrams,
    dry_run: bool = False,
) -> BuildReport:
    """Run the full ingest loop for one system. Returns a count report.

    LLM/validator/reindex/diagram steps are injected so this runs offline in tests."""
    repo_root = Path(repo_root)
    sid = source_id_for(repo_root, cfg)
    report = BuildReport(system=cfg.id, source_id=sid)

    graph = _load_graph(repo_root)
    docs = resolve_docs(repo_root, cfg.docs)
    report.docs = len(docs)

    scan_patches = []
    extra_patches = []  # port-map + connect (not reconciled against the index)
    for doc in docs:
        try:
            text = read_doc(doc)
        except DocReadError as e:
            report.notes.append(f"skip {doc.name}: {e}")
            continue
        for chunk in agents.chunk_markdown(text, source_id=sid, doc_name=doc.name):
            extra_patches.extend(
                agents.port_map(chunk, package_base=cfg.package, model_dir=cfg.model_dir)
            )
            if use_llm:
                try:
                    scan_patches.extend(
                        agents.scan(
                            chunk, package_base=cfg.package, model_dir=cfg.model_dir,
                            complete=complete, cfg=llm_cfg,
                        ).patches
                    )
                    if do_connect:
                        extra_patches.extend(
                            agents.connect(
                                chunk, graph, package_base=cfg.package, model_dir=cfg.model_dir,
                                complete=complete, cfg=llm_cfg,
                            ).patches
                        )
                except (LLMError, agents.AgentError) as e:
                    report.notes.append(f"agent error on {chunk.heading!r}: {e}")

    report.scanned = len(scan_patches)

    # Reconcile scanned defs against the existing index: dedupe + flag contradictions.
    rec = agents.reconcile(scan_patches, graph)
    report.kept = len(rec.patches)
    report.dropped = len(rec.dropped)
    report.contradictions = len(rec.contradictions)
    if rec.contradictions:
        path = agents.write_review(rec.contradictions, repo_root)
        if path:
            report.notes.append(f"{len(rec.contradictions)} contradiction(s) -> {path}")

    # Enqueue everything that should be applied, then hand off to the apply-authority.
    queue = Queue(repo_root).ensure_dirs()
    for p in rec.patches + extra_patches:
        queue.enqueue(p)
        report.enqueued += 1

    if report.enqueued == 0:
        return report

    results = drain(repo_root, validator=validator, dry_run=dry_run)
    report.applied = sum(r.status == "applied" for r in results)
    report.rejected = sum(r.status == "rejected" for r in results)

    if report.applied and not dry_run:
        ok, detail = reindex(repo_root)
        if not ok:
            report.notes.append(f"reindex failed: {detail}")
        report.imports_added = ensure_index_imports(repo_root, cfg.package, cfg.model_dir)
        ok, detail = regen_diagrams(repo_root)
        if not ok:
            report.notes.append(f"diagram regen failed: {detail}")
    return report


def _load_graph(repo_root: Path) -> Graph:
    index = Path(repo_root) / ".nomograph" / "index.json"
    if index.exists():
        try:
            return Graph.load(index)
        except Exception:
            pass
    return Graph()


# -------------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="sysledge-build",
        description="Ingest documents into the SysML models per sysledge.toml.",
    )
    ap.add_argument("--repo", default=".", type=Path, help="repo root (default: .)")
    ap.add_argument("--config", default="sysledge.toml", type=Path, help="config file")
    ap.add_argument("--system", help="only build this system id")
    ap.add_argument("--connect", action="store_true", help="also run the ConnectorAgent (LLM)")
    ap.add_argument("--no-llm", action="store_true", help="skip LLM agents; deterministic only")
    ap.add_argument("--dry-run", action="store_true", help="validate edits but revert all")
    args = ap.parse_args(argv)

    config = args.repo / args.config if not args.config.is_absolute() else args.config
    if not config.exists():
        print(f"no config at {config}")
        return 2
    systems = load_systems(config)
    if args.system:
        systems = [s for s in systems if s.id == args.system]
        if not systems:
            print(f"system {args.system!r} not found in {config}")
            return 2

    rc = 0
    for cfg in systems:
        rep = build_system(
            cfg, args.repo,
            use_llm=not args.no_llm, do_connect=args.connect, dry_run=args.dry_run,
        )
        print(
            f"[{rep.system}] docs={rep.docs} scanned={rep.scanned} kept={rep.kept} "
            f"dropped={rep.dropped} contradictions={rep.contradictions} "
            f"enqueued={rep.enqueued} applied={rep.applied} rejected={rep.rejected}"
            + (f" imports+={rep.imports_added}" if rep.imports_added else "")
        )
        for n in rep.notes:
            print(f"    note: {n}")
        if rep.rejected:
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
