"""Read architecture documents into plain text for LLM ingestion.

Supported formats (extensible):
    .md / .txt / .rst / .adoc  — read as UTF-8 (stdlib only, always works)
    .pdf                       — requires `pypdf`  (install: pip install 'sysmldiag[pdf]')
    .docx                      — requires `python-docx` (install: pip install 'sysmldiag[docx]')

Multiple files are joined with a provenance header per file so the LLM and the
resulting `@Provenance` annotations can reference distinct sources.
"""

from __future__ import annotations

import importlib
from pathlib import Path

TEXT_SUFFIXES = {".md", ".txt", ".rst", ".adoc", ".asciidoc"}


class DocReadError(ValueError):
    pass


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise DocReadError(f"cannot read {path}: {e}") from e


def _read_pdf(path: Path) -> str:
    try:
        pypdf = importlib.import_module("pypdf")
    except ModuleNotFoundError:
        raise DocReadError(
            f"PDF support requires 'pypdf': install with `pip install 'sysmldiag[pdf]'`"
            f" or `uv tool install --editable '.[pdf]'`"
        )
    reader = pypdf.PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(p.strip() for p in pages if p.strip())
    if not text:
        raise DocReadError(f"{path}: PDF text extraction yielded empty content (scanned/image PDF?)")
    return text


def _read_docx(path: Path) -> str:
    try:
        docx = importlib.import_module("docx")
    except ModuleNotFoundError:
        raise DocReadError(
            f"Word support requires 'python-docx': install with `pip install 'sysmldiag[docx]'`"
            f" or `uv tool install --editable '.[docx]'`"
        )
    doc = docx.Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs)
    if not text:
        raise DocReadError(f"{path}: Word document appears empty")
    return text


def read_doc(path: Path) -> str:
    """Return plain text for one document file."""
    suf = path.suffix.lower()
    if suf in TEXT_SUFFIXES:
        return _read_text(path)
    if suf == ".pdf":
        return _read_pdf(path)
    if suf == ".docx":
        return _read_docx(path)
    # Try reading as text for unknown extensions; warn but don't fail.
    try:
        return _read_text(path)
    except DocReadError:
        raise DocReadError(
            f"unsupported format '{path.suffix}' for {path}. "
            f"Supported: {sorted(TEXT_SUFFIXES | {'.pdf', '.docx'})}"
        )


def read_docs(paths: list[Path]) -> str:
    """Return all documents joined with per-file provenance headers.

    Each section is delimited so the LLM (and the resulting @Provenance
    annotations) can attribute facts to distinct sources.
    """
    if len(paths) == 1:
        return read_doc(paths[0])

    sections: list[str] = []
    for p in paths:
        text = read_doc(p)
        sections.append(f"### Source: {p.name}\n\n{text}")
    return "\n\n---\n\n".join(sections)
