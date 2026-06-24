"""Offline tests for the apply-authority (sysmldiag.ingest.authority).

A fake validator stands in for nomograph: a file is "valid" unless it contains the
sentinel BROKEN. No network, no nomograph, no real model tree.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sysmldiag.ingest.authority import (
    LockHeld,
    _acquire_lock,
    apply_edit,
    apply_one,
    drain,
)
from sysmldiag.ingest.queue import Patch, Queue

MODEL = """package Sys {
    part def Existing {
        @Provenance { source = "repo@abc:README.md#e"; maturity = "concept"; }
    }
}
"""


def fake_validator(repo_root: Path, target_file: Path):
    text = Path(target_file).read_text()
    if "BROKEN" in text:
        return False, "validate failed: BROKEN token present"
    return True, "valid"


def _patch(**over) -> Patch:
    base = dict(
        op="add",
        target_file="models/sys/structure.sysml",
        target_package="Sys",
        sysml='part def Widget {\n    @Provenance { source = "repo@abc:README.md#w"; maturity = "concept"; }\n}',
        provenance={"source": "repo@abc:README.md#w", "maturity": "concept"},
        agent="ScannerAgent",
        rationale="add a widget",
    )
    base.update(over)
    return Patch(**base)


class _RepoTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.target = self.root / "models" / "sys" / "structure.sysml"
        self.target.parent.mkdir(parents=True)
        self.target.write_text(MODEL)
        (self.root / "log.md").write_text("# log\n")


class ApplyEditPureTest(unittest.TestCase):
    def test_add_inserts_before_package_close(self):
        out = apply_edit(MODEL, _patch())
        self.assertIn("part def Widget", out)
        self.assertIn("part def Existing", out)  # original preserved
        self.assertTrue(out.rstrip().endswith("}"))

    def test_modify_replaces_anchor_block(self):
        p = _patch(op="modify", anchor="Existing",
                   sysml='part def Existing {\n    @Provenance { source = "s"; maturity = "designed"; }\n}')
        out = apply_edit(MODEL, p)
        self.assertIn('maturity = "designed"', out)
        self.assertNotIn('maturity = "concept"', out)

    def test_remove_deletes_anchor_block(self):
        p = _patch(op="remove", anchor="Existing", sysml="")
        out = apply_edit(MODEL, p)
        self.assertNotIn("Existing", out)


class ApplyOneTest(_RepoTest):
    def test_valid_patch_applied_and_logged(self):
        res = apply_one(_patch(), self.root, validator=fake_validator)
        self.assertEqual(res.status, "applied")
        self.assertIn("Widget", self.target.read_text())
        self.assertIn("add", (self.root / "log.md").read_text())

    def test_invalid_patch_rolled_back(self):
        before = self.target.read_text()
        p = _patch(sysml='part def Bad {\n    @Provenance { source = "s"; maturity = "concept"; }\n    BROKEN\n}')
        res = apply_one(p, self.root, validator=fake_validator)
        self.assertEqual(res.status, "rejected")
        self.assertEqual(self.target.read_text(), before)  # byte-for-byte restore
        self.assertNotIn("Bad", self.target.read_text())
        self.assertNotIn("Bad", (self.root / "log.md").read_text())

    def test_dry_run_reverts_even_when_valid(self):
        before = self.target.read_text()
        res = apply_one(_patch(), self.root, validator=fake_validator, dry_run=True)
        self.assertEqual(res.status, "applied")
        self.assertEqual(self.target.read_text(), before)  # reverted


class DrainTest(_RepoTest):
    def test_drain_routes_applied_and_rejected(self):
        q = Queue(self.root)
        q.enqueue(_patch(rationale="good"))
        q.enqueue(_patch(
            rationale="bad",
            sysml='part def Bad {\n    @Provenance { source = "s"; maturity = "concept"; }\n    BROKEN\n}',
        ))
        results = drain(self.root, validator=fake_validator)
        statuses = sorted(r.status for r in results)
        self.assertEqual(statuses, ["applied", "rejected"])
        self.assertEqual(len(list((self.root / "queue" / "applied").glob("*.json"))), 1)
        self.assertEqual(len(list((self.root / "queue" / "rejected").glob("*.json"))), 1)
        self.assertEqual(len(list((self.root / "queue" / "incoming").glob("*.json"))), 0)


class LockTest(_RepoTest):
    def test_second_lock_is_held(self):
        q = Queue(self.root).ensure_dirs()
        lock = _acquire_lock(q.base)
        try:
            with self.assertRaises(LockHeld):
                _acquire_lock(q.base)
        finally:
            lock.unlink()


if __name__ == "__main__":
    unittest.main()
