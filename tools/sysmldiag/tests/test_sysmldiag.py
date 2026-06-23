"""Deterministic, offline tests for the diagram generator (Layer A).

No LLM, no network, no `mmdc` required. Run:
    PYTHONPATH=tools python3 -m unittest sysmldiag.tests.test_sysmldiag

Regenerate goldens after an intentional change:
    PYTHONPATH=tools python3 -m sysmldiag.tests.test_sysmldiag --update-golden
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from sysmldiag import views as views_pkg
from sysmldiag.graph import Graph, mermaid_id, short
from sysmldiag.lint import lint_mermaid

FIX = Path(__file__).parent / "fixtures"
GOLDEN = FIX / "golden"
NANOS = FIX / "nanos3reader.index.json"
SYNTH = FIX / "synthetic.index.json"


class GraphTest(unittest.TestCase):
    def setUp(self):
        self.g = Graph.load(NANOS)

    def test_loads_elements_and_rels(self):
        self.assertGreater(len(self.g.elements), 100)
        self.assertTrue(self.g.rels("Satisfy"))
        self.assertTrue(self.g.rels("Specialize"))

    def test_by_kind_sorted(self):
        defs = self.g.by_kind("part_definition")
        self.assertTrue(defs)
        self.assertEqual(
            [d.qualified_name for d in defs],
            sorted(d.qualified_name for d in defs),
        )

    def test_type_of_resolves(self):
        # S3Streambuf has a port 'http' typed by ByteRangeReadPort.
        port = self.g.get("Nanos3readerStructure::S3Streambuf::http")
        self.assertIsNotNone(port)
        t = self.g.type_of(port.qualified_name)
        self.assertIsNotNone(t)
        self.assertEqual(short(t.qualified_name), "ByteRangeReadPort")

    def test_mermaid_id_is_safe(self):
        self.assertEqual(mermaid_id("A::B.c-d"), "A__B_c_d")
        self.assertNotIn("::", mermaid_id("x::y"))


class GoldenTest(unittest.TestCase):
    def setUp(self):
        self.g = Graph.load(NANOS)

    def test_every_view_matches_golden(self):
        for slug in views_pkg.all_views():
            with self.subTest(view=slug):
                got = views_pkg.render(slug, self.g).mermaid + "\n"
                want = (GOLDEN / f"{slug}.mmd").read_text()
                self.assertEqual(got, want, f"{slug} drifted from golden")

    def test_render_is_deterministic(self):
        for slug in views_pkg.all_views():
            a = views_pkg.render(slug, self.g).mermaid
            b = views_pkg.render(slug, self.g).mermaid
            self.assertEqual(a, b)


class LintTest(unittest.TestCase):
    def test_all_views_pass_structural_lint(self):
        g = Graph.load(NANOS)
        for slug in views_pkg.all_views():
            with self.subTest(view=slug):
                issues = lint_mermaid(views_pkg.render(slug, g).mermaid)
                self.assertEqual(issues, [], f"{slug}: {issues}")

    def test_node_ids_have_no_separators(self):
        g = Graph.load(NANOS)
        bdd = views_pkg.render("bdd", g).mermaid
        # class ids must be sanitized (no '::' leaking into Mermaid ids).
        for line in bdd.splitlines():
            if line.strip().startswith("class "):
                ident = line.strip().split()[1].split("[")[0]
                self.assertNotIn("::", ident)


class SyntheticEdgeTest(unittest.TestCase):
    def setUp(self):
        self.g = Graph.load(SYNTH)

    def test_orphan_and_partial_requirements(self):
        m = views_pkg.render("requirements", self.g).mermaid
        self.assertIn(":::orphan", m)  # ReqOrphan
        self.assertIn(":::partial", m)  # ReqSatisfied

    def test_empty_behavior_and_ibd_fallbacks(self):
        self.assertIn("no actions modeled", views_pkg.render("behavior", self.g).mermaid)
        self.assertIn("no connections modeled", views_pkg.render("ibd", self.g).mermaid)

    def test_notes_surface_gaps(self):
        notes = views_pkg.render("requirements", self.g).notes
        self.assertTrue(any("neither satisfied nor verified" in n for n in notes))


def _update_golden():
    g = Graph.load(NANOS)
    GOLDEN.mkdir(exist_ok=True)
    for slug in views_pkg.all_views():
        (GOLDEN / f"{slug}.mmd").write_text(views_pkg.render(slug, g).mermaid + "\n")
    print(f"updated {len(views_pkg.all_views())} golden file(s)")


if __name__ == "__main__":
    if "--update-golden" in sys.argv:
        _update_golden()
    else:
        unittest.main()
