"""Offline tests for the multi-system driver (sysmldiag.ingest.build_models).

A temp repo is built on disk; the LLM, validator, reindex, and diagram steps are all
injected fakes, so the full read-docs -> agents -> queue -> apply -> index-imports loop
runs with no network and no nomograph.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sysmldiag.ingest import build_models as bm
from sysmldiag.ingest.build_models import (
    SystemConfig,
    ensure_index_imports,
    load_systems,
    resolve_docs,
    source_id_for,
)

DOC = """## Overview

The reader streams S3 object ranges.

## Interface

| Name | Type | Direction |
|------|------|-----------|
| data | InputStream | in |
"""

SCAN_REPLY = json.dumps(
    [
        {
            "kind": "part",
            "name": "RangeReader",
            "sysml": 'part def RangeReader {\n    @Provenance { source = "<SOURCE>"; maturity = "concept"; }\n}',
        }
    ]
)


def _ok_validator(repo_root, target):
    return True, "valid"


def _noop(repo_root):
    return True, ""


def _fake_complete(system, user, cfg=None):
    # Return the def only for the Overview section; other sections yield nothing.
    return SCAN_REPLY if "Section heading: Overview" in user else "[]"


def _make_repo() -> Path:
    root = Path(tempfile.mkdtemp())
    (root / "models" / "testsys").mkdir(parents=True)
    (root / "models" / "testsys" / "structure.sysml").write_text(
        "package TestsysStructure {\n}\n", encoding="utf-8"
    )
    (root / "models" / "index.sysml").write_text(
        "package SysledgeIndex {\n    import Concepts::*;\n}\n", encoding="utf-8"
    )
    (root / "raw" / "testsys").mkdir(parents=True)
    (root / "raw" / "testsys" / "manifest.yaml").write_text(
        "system: testsys\nsources:\n  - id: testsys@abc123\n    kind: git-repository\n",
        encoding="utf-8",
    )
    (root / "raw" / "testsys" / "overview.md").write_text(DOC, encoding="utf-8")
    (root / "log.md").write_text("# log\n", encoding="utf-8")
    (root / "sysledge.toml").write_text(
        '[[systems]]\nid = "testsys"\npackage = "Testsys"\n'
        'model_dir = "models/testsys"\ndocs = ["raw/testsys/*.md"]\n',
        encoding="utf-8",
    )
    return root


def _cfg() -> SystemConfig:
    return SystemConfig(
        id="testsys", package="Testsys", model_dir="models/testsys",
        docs=["raw/testsys/*.md"],
    )


class ConfigTest(unittest.TestCase):
    def test_load_systems(self):
        root = _make_repo()
        systems = load_systems(root / "sysledge.toml")
        self.assertEqual(len(systems), 1)
        self.assertEqual(systems[0].id, "testsys")
        self.assertEqual(systems[0].package, "Testsys")

    def test_source_id_from_manifest(self):
        root = _make_repo()
        self.assertEqual(source_id_for(root, _cfg()), "testsys@abc123")

    def test_source_id_explicit_override(self):
        cfg = _cfg()
        cfg.source_id = "testsys@override"
        self.assertEqual(source_id_for(Path("/nonexistent"), cfg), "testsys@override")

    def test_resolve_docs_globs(self):
        root = _make_repo()
        docs = resolve_docs(root, ["raw/testsys/*.md"])
        self.assertEqual([d.name for d in docs], ["overview.md"])


class EnsureImportsTest(unittest.TestCase):
    def test_adds_only_existing_aspects_and_is_idempotent(self):
        root = _make_repo()  # only structure.sysml exists
        added = ensure_index_imports(root, "Testsys", "models/testsys")
        self.assertEqual(added, ["import TestsysStructure::*;"])
        idx = (root / "models" / "index.sysml").read_text()
        self.assertIn("import TestsysStructure::*;", idx)
        self.assertNotIn("TestsysRequirements", idx)  # no requirements.sysml
        # second call is a no-op
        self.assertEqual(ensure_index_imports(root, "Testsys", "models/testsys"), [])


class BuildSystemTest(unittest.TestCase):
    def test_full_loop_applies_scan_and_ports(self):
        root = _make_repo()
        rep = bm.build_system(
            _cfg(), root,
            complete=_fake_complete, validator=_ok_validator,
            reindex=_noop, regen_diagrams=_noop,
        )
        self.assertEqual(rep.source_id, "testsys@abc123")
        self.assertEqual(rep.docs, 1)
        self.assertEqual(rep.scanned, 1)
        self.assertEqual(rep.kept, 1)
        self.assertGreaterEqual(rep.enqueued, 2)  # 1 scanned def + >=1 port
        self.assertEqual(rep.rejected, 0)
        self.assertGreaterEqual(rep.applied, 2)

        structure = (root / "models" / "testsys" / "structure.sysml").read_text()
        self.assertIn("part def RangeReader", structure)
        self.assertIn("port data : InputStream", structure)
        # provenance source carried through, placeholder gone
        self.assertIn("testsys@abc123:overview.md#overview", structure)
        self.assertNotIn("<SOURCE>", structure)
        # index import ensured + log appended
        self.assertIn("import TestsysStructure::*;", (root / "models" / "index.sysml").read_text())
        log = (root / "log.md").read_text()
        self.assertIn("agent=ScannerAgent", log)
        self.assertIn("testsys@abc123:overview.md#overview", log)

    def test_no_llm_runs_ports_only(self):
        root = _make_repo()
        rep = bm.build_system(
            _cfg(), root,
            use_llm=False, validator=_ok_validator, reindex=_noop, regen_diagrams=_noop,
        )
        self.assertEqual(rep.scanned, 0)
        self.assertGreaterEqual(rep.applied, 1)  # the port from the interface table
        structure = (root / "models" / "testsys" / "structure.sysml").read_text()
        self.assertIn("port data : InputStream", structure)
        self.assertNotIn("RangeReader", structure)

    def test_dry_run_reverts_everything(self):
        root = _make_repo()
        before = (root / "models" / "testsys" / "structure.sysml").read_text()
        rep = bm.build_system(
            _cfg(), root,
            complete=_fake_complete, validator=_ok_validator,
            reindex=_noop, regen_diagrams=_noop, dry_run=True,
        )
        self.assertGreaterEqual(rep.enqueued, 2)
        after = (root / "models" / "testsys" / "structure.sysml").read_text()
        self.assertEqual(before, after)  # rolled back byte-for-byte
        # index untouched in dry-run
        self.assertNotIn("TestsysStructure", (root / "models" / "index.sysml").read_text())


if __name__ == "__main__":
    unittest.main()
