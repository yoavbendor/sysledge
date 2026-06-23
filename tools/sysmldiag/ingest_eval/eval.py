"""Layer B harness: doc -> [LLM] -> SysML -> validate -> index -> diagrams.

Asserts *structural richness* (not exact text, which an LLM cannot guarantee):
the extracted model must validate, yield a minimum number of parts/requirements,
and every diagram view must render and pass the structural lint. This proves the
pipeline and the generator scale to real architecture documents.

Run (needs an API key or local endpoint — see extractor.py):
    PYTHONPATH=tools python3 -m sysmldiag.ingest_eval.eval \
        --doc tools/sysmldiag/ingest_eval/medhead/source.md --system MedHead

Exit codes: 0 pass, 3 skipped (no LLM configured), 1 failure.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from .. import views as views_pkg
from ..graph import Graph
from ..lint import lint_mermaid
from ..llm import LLMConfig, LLMError
from .extractor import extract_sysml

MIN_PARTS = 4
MIN_REQS = 3


def _nomograph(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["nomograph-sysml", *args], capture_output=True, text=True
    )


def run(doc_path: Path, system: str, lib: Path = Path("lib")) -> int:
    doc = doc_path.read_text()
    try:
        cfg = LLMConfig.from_env()
        print(f"LLM: {cfg.redacted()}")
        sysml = extract_sysml(doc, system, cfg)
    except LLMError as e:
        print(f"SKIP: LLM not configured ({e}).")
        print("      Configure a provider — e.g. ANTHROPIC_API_KEY or OPENAI_API_KEY;")
        print("      see `python3 -m sysmldiag.llm --show`.")
        return 3

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        model_file = tmp / f"{system.lower()}.sysml"
        model_file.write_text(sysml)
        print(f"extracted {len(sysml.splitlines())} lines of SysML -> {model_file.name}")

        val = _nomograph("validate", str(model_file))
        if "valid:true" not in val.stdout.replace('"valid": true', "valid:true").replace(
            " ", ""
        ).replace('"valid":true', "valid:true"):
            # Be liberal in parsing nomograph's JSON; treat non-zero exit as fail.
            if val.returncode != 0:
                print("FAIL: extracted SysML did not validate.")
                print(val.stdout[-800:])
                return 1

        # Index with lib/ so shared imports (Concepts, ScalarValues) resolve.
        index = tmp / "index.json"
        index_inputs = [str(model_file)]
        if lib.exists():
            index_inputs.insert(0, str(lib))
        idx = _nomograph("index", *index_inputs, "--output", str(index))
        if idx.returncode != 0 or not index.exists():
            print("FAIL: indexing failed.")
            print(idx.stderr[-800:])
            return 1

        g = Graph.load(index)
        n_parts = len(g.by_kind("part_definition", "part_usage"))
        n_reqs = len(g.by_kind("requirement_definition"))
        print(f"indexed: {len(g.elements)} elements, {n_parts} parts, {n_reqs} requirements")

        problems: list[str] = []
        if n_parts < MIN_PARTS:
            problems.append(f"too few parts ({n_parts} < {MIN_PARTS})")
        if n_reqs < MIN_REQS:
            problems.append(f"too few requirements ({n_reqs} < {MIN_REQS})")

        for slug in views_pkg.all_views():
            issues = lint_mermaid(views_pkg.render(slug, g).mermaid)
            if issues:
                problems.append(f"view {slug}: {issues}")

        if problems:
            print("FAIL:")
            for p in problems:
                print(f"  - {p}")
            return 1

    print("PASS: doc -> model -> diagrams pipeline produced a rich, lintable model.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--doc", required=True, type=Path)
    ap.add_argument("--system", default="MedHead")
    ap.add_argument("--lib", default=Path("lib"), type=Path)
    args = ap.parse_args(argv)
    return run(args.doc, args.system, args.lib)


if __name__ == "__main__":
    raise SystemExit(main())
