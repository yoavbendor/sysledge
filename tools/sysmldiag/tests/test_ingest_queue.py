"""Offline tests for the patch queue (sysmldiag.ingest.queue)."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from sysmldiag.ingest.queue import Patch, PatchError, Queue, new_id


def _d(**over) -> dict:
    base = dict(
        op="add",
        target_file="models/nanos3reader/structure.sysml",
        target_package="Nanos3reader",
        sysml='part def Widget {\n    @Provenance { source = "repo@abc:README.md#x"; maturity = "concept"; }\n}',
        provenance={"source": "repo@abc:README.md#x", "maturity": "concept"},
        agent="ScannerAgent",
        rationale="found a widget",
    )
    base.update(over)
    return base


def _patch(**over) -> Patch:
    return Patch.parse(_d(**over))


class PatchValidateTest(unittest.TestCase):
    def test_valid_patch_parses(self):
        _patch()  # no raise

    def test_add_without_provenance_annotation_rejected(self):
        with self.assertRaises(PatchError) as e:
            _patch(sysml="part def Widget {}")
        self.assertIn("@Provenance", str(e.exception))

    def test_missing_source_rejected(self):
        with self.assertRaises(PatchError):
            _patch(provenance={"maturity": "concept"})

    def test_bad_maturity_rejected(self):
        with self.assertRaises(PatchError):
            _patch(provenance={"source": "s", "maturity": "guess"})

    def test_unknown_op_rejected(self):
        with self.assertRaises(PatchError):
            _patch(op="frobnicate")

    def test_path_escape_rejected(self):
        with self.assertRaises(PatchError):
            _patch(target_file="../etc/passwd")

    def test_path_outside_models_or_lib_rejected(self):
        with self.assertRaises(PatchError):
            _patch(target_file="docs/conventions.md")

    def test_remove_op_does_not_require_provenance_in_sysml(self):
        # remove/promote ops carry no fragment facts; only the provenance dict is required.
        _patch(op="remove", sysml="", anchor="Widget")


class NewIdTest(unittest.TestCase):
    def test_sortable_monotonic(self):
        a = new_id()
        time.sleep(0.001)
        b = new_id()
        self.assertLess(a, b)

    def test_unique(self):
        self.assertEqual(len({new_id() for _ in range(200)}), 200)


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.q = Queue(self.root)

    def test_enqueue_and_iter_fifo(self):
        self.q.enqueue(_patch(rationale="first"))
        time.sleep(0.001)
        self.q.enqueue(_patch(rationale="second"))
        seen = [patch.rationale for _, patch in self.q.iter_incoming()]
        self.assertEqual(seen, ["first", "second"])

    def test_cannot_build_invalid_patch(self):
        with self.assertRaises(PatchError):
            _patch(provenance={"source": "s", "maturity": "nope"})

    def test_roundtrip_serialization(self):
        p = _patch()
        path = self.q.enqueue(p)
        loaded = Patch.from_json(path.read_text())
        self.assertEqual(loaded.id, p.id)
        self.assertEqual(loaded.sysml, p.sysml)
        self.assertEqual(loaded.provenance, p.provenance)

    def test_move_to_applied(self):
        path = self.q.enqueue(_patch())
        dest = self.q.move(path, "applied", extra={"result": "valid"})
        self.assertTrue(dest.exists())
        self.assertFalse(path.exists())
        self.assertIn("applied", str(dest))

    def test_move_rejects_bad_status(self):
        path = self.q.enqueue(_patch())
        with self.assertRaises(ValueError):
            self.q.move(path, "incoming")


if __name__ == "__main__":
    unittest.main()
