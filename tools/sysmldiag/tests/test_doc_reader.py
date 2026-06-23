"""Offline tests for the doc_reader module.

Exercises format dispatch, multi-doc joining, and graceful error paths
(missing optional deps, bad paths, unsupported extensions) — no LLM, no network.
"""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from unittest import mock

from sysmldiag.ingest_eval.doc_reader import (
    DocReadError,
    TEXT_SUFFIXES,
    read_doc,
    read_docs,
)


def _tmp_file(tmp_path_factory, content: str, suffix: str) -> Path:
    td = Path(tmp_path_factory())
    td.mkdir(parents=True, exist_ok=True)
    p = td / f"doc{suffix}"
    p.write_text(content, encoding="utf-8")
    return p


import tempfile

def _tf(content: str, suffix: str) -> Path:
    td = Path(tempfile.mkdtemp())
    p = td / f"doc{suffix}"
    p.write_text(content, encoding="utf-8")
    return p


class ReadTextTest(unittest.TestCase):
    def test_md(self):
        p = _tf("# Hello\nWorld", ".md")
        self.assertIn("Hello", read_doc(p))

    def test_txt(self):
        p = _tf("plain text", ".txt")
        self.assertEqual(read_doc(p), "plain text")

    def test_rst(self):
        p = _tf("Title\n=====\nBody", ".rst")
        self.assertIn("Title", read_doc(p))

    def test_unknown_extension_falls_back_to_text(self):
        p = _tf("some content", ".log")
        self.assertEqual(read_doc(p), "some content")

    def test_missing_file_raises(self):
        with self.assertRaises(DocReadError):
            read_doc(Path("/nonexistent/file.md"))


class MultiDocTest(unittest.TestCase):
    def test_single_doc_no_header(self):
        p = _tf("content", ".md")
        result = read_docs([p])
        self.assertEqual(result, "content")

    def test_multi_doc_adds_source_headers(self):
        a = _tf("alpha", ".md")
        b = _tf("beta", ".txt")
        result = read_docs([a, b])
        self.assertIn("### Source: doc.md", result)
        self.assertIn("### Source: doc.txt", result)
        self.assertIn("alpha", result)
        self.assertIn("beta", result)
        # joined by the separator
        self.assertIn("---", result)

    def test_multi_doc_order_preserved(self):
        a = _tf("FIRST", ".md")
        b = _tf("SECOND", ".md")
        result = read_docs([a, b])
        self.assertLess(result.index("FIRST"), result.index("SECOND"))


class PdfMissingDepTest(unittest.TestCase):
    def test_pdf_without_pypdf_raises(self):
        p = _tf("", ".pdf")
        with mock.patch.dict("sys.modules", {"pypdf": None}):
            with self.assertRaises(DocReadError) as ctx:
                read_doc(p)
        self.assertIn("pypdf", str(ctx.exception))
        self.assertIn("sysmldiag[pdf]", str(ctx.exception))


class DocxMissingDepTest(unittest.TestCase):
    def test_docx_without_python_docx_raises(self):
        p = _tf("", ".docx")
        with mock.patch.dict("sys.modules", {"docx": None}):
            with self.assertRaises(DocReadError) as ctx:
                read_doc(p)
        self.assertIn("python-docx", str(ctx.exception))
        self.assertIn("sysmldiag[docx]", str(ctx.exception))


class PdfExtractTest(unittest.TestCase):
    def test_pdf_with_mock_pypdf(self):
        """Exercise the pypdf path with a fake PdfReader."""
        fake_page = mock.MagicMock()
        fake_page.extract_text.return_value = "Page one text"
        fake_reader = mock.MagicMock()
        fake_reader.pages = [fake_page]
        fake_pypdf = mock.MagicMock()
        fake_pypdf.PdfReader.return_value = fake_reader

        p = _tf("", ".pdf")
        with mock.patch.dict("sys.modules", {"pypdf": fake_pypdf}):
            result = read_doc(p)
        self.assertIn("Page one text", result)

    def test_pdf_empty_content_raises(self):
        fake_page = mock.MagicMock()
        fake_page.extract_text.return_value = ""
        fake_reader = mock.MagicMock()
        fake_reader.pages = [fake_page]
        fake_pypdf = mock.MagicMock()
        fake_pypdf.PdfReader.return_value = fake_reader

        p = _tf("", ".pdf")
        with mock.patch.dict("sys.modules", {"pypdf": fake_pypdf}):
            with self.assertRaises(DocReadError) as ctx:
                read_doc(p)
        self.assertIn("empty", str(ctx.exception))


class DocxExtractTest(unittest.TestCase):
    def test_docx_with_mock_python_docx(self):
        """Exercise the python-docx path with a fake Document."""
        fake_para = mock.MagicMock()
        fake_para.text = "Paragraph text"
        fake_doc = mock.MagicMock()
        fake_doc.paragraphs = [fake_para]
        fake_docx_mod = mock.MagicMock()
        fake_docx_mod.Document.return_value = fake_doc

        p = _tf("", ".docx")
        with mock.patch.dict("sys.modules", {"docx": fake_docx_mod}):
            result = read_doc(p)
        self.assertIn("Paragraph text", result)


if __name__ == "__main__":
    unittest.main()
