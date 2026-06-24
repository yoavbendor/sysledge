"""Offline tests for the ingestion agents (sysmldiag.ingest.agents).

No network and no nomograph: the LLM is a fake callable and the knowledge graph is
constructed in memory. Covers chunking, scanner JSON parsing + provenance injection,
reconciliation (dedupe / contradiction flagging), and the deterministic port mapper.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sysmldiag.graph import Element, Graph
from sysmldiag.ingest.agents import (
    AgentError,
    _loads_json_array,
    chunk_markdown,
    connect,
    port_map,
    reconcile,
    scan,
    write_review,
)
from sysmldiag.ingest.queue import Patch

DOC = """Intro line before any heading.

## Range reads

The reader issues HTTP range GETs.

## SigV4 signing

Requests are signed with AWS SigV4.
"""


def _fake(reply: str):
    """A stand-in for llm.complete that returns canned text."""
    def _complete(system, user, cfg=None):
        return reply
    return _complete


def _graph(*elements: Element) -> Graph:
    g = Graph()
    for e in elements:
        g.elements[e.qualified_name] = e
    return g


class ChunkMarkdownTest(unittest.TestCase):
    def test_splits_on_headings_and_carries_source(self):
        chunks = chunk_markdown(DOC, source_id="sys@abc", doc_name="README.md")
        headings = [c.heading for c in chunks]
        self.assertEqual(headings, ["(preamble)", "Range reads", "SigV4 signing"])
        self.assertEqual(chunks[1].source, "sys@abc:README.md#range-reads")
        self.assertIn("range GETs", chunks[1].text)

    def test_no_headings_is_single_chunk(self):
        chunks = chunk_markdown("just prose, no headings", source_id="s", doc_name="x.txt")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].source, "s:x.txt#preamble")


class LoadsJsonArrayTest(unittest.TestCase):
    def test_plain_array(self):
        self.assertEqual(_loads_json_array('[{"a":1}]'), [{"a": 1}])

    def test_strips_code_fences(self):
        self.assertEqual(_loads_json_array('```json\n[{"a":1}]\n```'), [{"a": 1}])

    def test_single_object_wrapped(self):
        self.assertEqual(_loads_json_array('{"a":1}'), [{"a": 1}])

    def test_prose_raises(self):
        with self.assertRaises(AgentError):
            _loads_json_array("Sure! Here is the model:")


_SCAN_REPLY = json.dumps(
    [
        {
            "kind": "part",
            "name": "S3Reader",
            "sysml": 'part def S3Reader {\n    @Provenance { source = "<SOURCE>"; maturity = "concept"; }\n}',
        },
        {
            "kind": "requirement",
            "name": "RangeReads",
            "sysml": 'requirement def RangeReads {\n    @Provenance { source = "<SOURCE>"; maturity = "concept"; }\n}',
        },
        {"kind": "part", "name": "BadOne", "sysml": "part def BadOne { }"},  # no @Provenance
    ]
)


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.chunk = chunk_markdown(DOC, source_id="sys@abc", doc_name="README.md")[1]

    def test_routes_by_kind_and_injects_provenance(self):
        res = scan(
            self.chunk,
            package_base="Nanos3reader",
            model_dir="models/nanos3reader",
            complete=_fake(_SCAN_REPLY),
        )
        self.assertEqual(len(res.patches), 2)
        part, req = res.patches
        self.assertEqual(part.target_file, "models/nanos3reader/structure.sysml")
        self.assertEqual(part.target_package, "Nanos3readerStructure")
        self.assertEqual(req.target_file, "models/nanos3reader/requirements.sysml")
        self.assertEqual(req.target_package, "Nanos3readerRequirements")
        # Provenance is authoritative: placeholder replaced with the chunk's source ref.
        self.assertNotIn("<SOURCE>", part.sysml)
        self.assertIn("sys@abc:README.md#range-reads", part.sysml)
        self.assertEqual(part.provenance.source, self.chunk.source)
        self.assertEqual(part.provenance.maturity, "concept")
        self.assertEqual(part.agent, "ScannerAgent")

    def test_malformed_item_is_skipped_not_fatal(self):
        res = scan(
            self.chunk,
            package_base="Nanos3reader",
            model_dir="models/nanos3reader",
            complete=_fake(_SCAN_REPLY),
        )
        self.assertEqual([n for n, _ in res.skipped], ["BadOne"])

    def test_non_json_reply_raises(self):
        with self.assertRaises(AgentError):
            scan(
                self.chunk,
                package_base="Nanos3reader",
                model_dir="models/nanos3reader",
                complete=_fake("no JSON here"),
            )


def _add(sysml: str, name: str, file: str = "structure.sysml") -> Patch:
    return Patch.parse(
        {
            "op": "add",
            "target_file": f"models/nanos3reader/{file}",
            "target_package": "Nanos3readerStructure",
            "sysml": sysml,
            "provenance": {"source": "sys@abc:README.md#x", "maturity": "concept"},
            "agent": "ScannerAgent",
        }
    )


_PROV = '@Provenance { source = "sys@abc:README.md#x"; maturity = "concept"; }'


class ReconcileTest(unittest.TestCase):
    def setUp(self):
        self.graph = _graph(
            Element(qualified_name="Nanos3readerStructure::S3Reader", kind="part_def"),
        )

    def test_novel_name_kept(self):
        p = _add(f"part def HttpClient {{ {_PROV} }}", "HttpClient")
        res = reconcile([p], self.graph)
        self.assertEqual(res.patches, [p])
        self.assertEqual(res.contradictions, [])

    def test_duplicate_same_kind_dropped(self):
        p = _add(f"part def S3Reader {{ {_PROV} }}", "S3Reader")
        res = reconcile([p], self.graph)
        self.assertEqual(res.patches, [])
        self.assertEqual(res.dropped, ["S3Reader"])

    def test_same_name_different_kind_is_contradiction(self):
        p = _add(f"requirement def S3Reader {{ {_PROV} }}", "S3Reader", "requirements.sysml")
        res = reconcile([p], self.graph)
        self.assertEqual(res.patches, [])
        self.assertEqual(len(res.contradictions), 1)
        c = res.contradictions[0]
        self.assertEqual(c.name, "S3Reader")
        self.assertEqual(c.existing, "Nanos3readerStructure::S3Reader")

    def test_write_review_creates_file_and_logs(self):
        p = _add(f"requirement def S3Reader {{ {_PROV} }}", "S3Reader", "requirements.sysml")
        res = reconcile([p], self.graph)
        root = Path(tempfile.mkdtemp())
        (root / "log.md").write_text("# log\n", encoding="utf-8")
        path = write_review(res.contradictions, root)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        self.assertIn("S3Reader", path.read_text())
        self.assertIn("contradiction", (root / "log.md").read_text())

    def test_write_review_noop_when_empty(self):
        self.assertIsNone(write_review([], Path(tempfile.mkdtemp())))


class PortMapTest(unittest.TestCase):
    def test_parses_interface_table_into_ports(self):
        text = (
            "## Interface\n\n"
            "| Name | Type | Direction |\n"
            "|------|------|-----------|\n"
            "| byte stream | InputStream | in |\n"
            "| ETag | String | out |\n"
        )
        chunk = chunk_markdown(text, source_id="sys@abc", doc_name="iface.md")[0]
        patches = port_map(chunk, package_base="Nanos3reader", model_dir="models/nanos3reader")
        self.assertEqual(len(patches), 2)
        self.assertIn("port byteStream : InputStream", patches[0].sysml)
        self.assertIn("// in", patches[0].sysml)
        self.assertEqual(patches[0].target_file, "models/nanos3reader/structure.sysml")
        self.assertEqual(patches[0].agent, "PortMapperAgent")
        self.assertIn("@Provenance", patches[1].sysml)

    def test_no_table_yields_nothing(self):
        chunk = chunk_markdown("## X\n\nprose only", source_id="s", doc_name="d.md")[0]
        self.assertEqual(port_map(chunk, package_base="N", model_dir="models/n"), [])


class ConnectTest(unittest.TestCase):
    def test_emits_connection_patch_seeded_with_parts(self):
        graph = _graph(
            Element(qualified_name="Nanos3readerStructure::S3Reader", kind="part_def"),
            Element(qualified_name="Nanos3readerStructure::S3Client", kind="part_def"),
        )
        reply = json.dumps(
            [
                {
                    "name": "reader-uses-client",
                    "sysml": f"connect reader.client to client {{ {_PROV} }}",
                }
            ]
        )
        chunk = chunk_markdown("## Wiring\n\nthe reader uses a client", source_id="sys@abc", doc_name="r.md")[0]
        res = connect(
            chunk,
            graph,
            package_base="Nanos3reader",
            model_dir="models/nanos3reader",
            complete=_fake(reply),
        )
        self.assertEqual(len(res.patches), 1)
        self.assertEqual(res.patches[0].agent, "ConnectorAgent")
        self.assertEqual(res.patches[0].target_file, "models/nanos3reader/structure.sysml")


if __name__ == "__main__":
    unittest.main()
