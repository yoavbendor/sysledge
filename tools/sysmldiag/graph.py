"""In-memory view of the nomograph SysML knowledge graph.

Loads `.nomograph/index.json` (the derived source of truth) into element and
relationship tables and exposes typed, *sorted* accessors. Everything is
deterministic: accessors return results ordered by qualified name so the
diagram emitters produce byte-stable output that can be golden-tested.

No SysML parsing happens here — we only consume what nomograph already indexed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


# Relationship kinds as emitted by nomograph (see `nomograph-sysml query`).
REL_MEMBER = "Member"
REL_TYPED_BY = "TypedBy"
REL_IMPORT = "Import"
REL_SATISFY = "Satisfy"
REL_VERIFY = "Verify"
REL_SPECIALIZE = "Specialize"
REL_CONNECT = "Connect"

# RFLP layers, ordered top-to-bottom for overview diagrams.
LAYER_ORDER = ["Requirements", "Function", "Logical", "Physical"]


@dataclass(frozen=True)
class Element:
    qualified_name: str
    kind: str
    file_path: str | None = None
    doc: str | None = None
    layer: str | None = None
    members: tuple[str, ...] = ()
    attributes: tuple[str, ...] = ()
    start_line: int = 0

    @property
    def name(self) -> str:
        """Last `::` segment — the short, human-facing name."""
        return self.qualified_name.split("::")[-1]

    @property
    def source_ref(self) -> str | None:
        """`file_path:line` anchor a human can click to reach the source."""
        if not self.file_path:
            return None
        return f"{self.file_path}:{self.start_line + 1}"


@dataclass(frozen=True)
class Relationship:
    source: str
    target: str
    kind: str
    file_path: str | None = None


@dataclass
class Graph:
    elements: dict[str, Element] = field(default_factory=dict)
    relationships: list[Relationship] = field(default_factory=list)

    # ---- loading --------------------------------------------------------
    @classmethod
    def load(cls, index_path: str | Path) -> "Graph":
        data = json.loads(Path(index_path).read_text())
        g = cls()
        for e in data.get("elements", []):
            span = e.get("span") or {}
            el = Element(
                qualified_name=e["qualified_name"],
                kind=e.get("kind", "unknown"),
                file_path=e.get("file_path"),
                doc=(e.get("doc") or None),
                layer=e.get("layer"),
                members=tuple(e.get("members") or ()),
                attributes=tuple(e.get("attributes") or ()),
                start_line=int(span.get("start_line", 0)),
            )
            g.elements[el.qualified_name] = el
        for r in data.get("relationships", []):
            g.relationships.append(
                Relationship(
                    source=r["source"],
                    target=r["target"],
                    kind=r.get("kind", "unknown"),
                    file_path=r.get("file_path"),
                )
            )
        return g

    # ---- element queries ------------------------------------------------
    def by_kind(self, *kinds: str) -> list[Element]:
        ks = set(kinds)
        return sorted(
            (e for e in self.elements.values() if e.kind in ks),
            key=lambda e: e.qualified_name,
        )

    def get(self, qname: str) -> Element | None:
        return self.elements.get(qname)

    def resolve(self, ref: str) -> Element | None:
        """Resolve a relationship endpoint to an element.

        Endpoints are usually qualified names, but usage paths like
        `factory.stream` appear too. Fall back to a suffix match so those still
        link to *something* sensible (the deepest matching declared element).
        """
        if ref in self.elements:
            return self.elements[ref]
        tail = ref.split("::")[-1].split(".")[-1]
        candidates = [e for e in self.elements.values() if e.name == tail]
        if len(candidates) == 1:
            return candidates[0]
        return None

    # ---- relationship queries ------------------------------------------
    def rels(self, kind: str) -> list[Relationship]:
        return sorted(
            (r for r in self.relationships if r.kind == kind),
            key=lambda r: (r.source, r.target),
        )

    def members_of(self, qname: str) -> list[Element]:
        out = [
            self.elements[r.target]
            for r in self.rels(REL_MEMBER)
            if r.source == qname and r.target in self.elements
        ]
        return sorted(out, key=lambda e: e.qualified_name)

    def type_of(self, qname: str) -> Element | None:
        """The definition a usage is TypedBy (e.g. a part_usage's part_def)."""
        for r in self.rels(REL_TYPED_BY):
            if r.source == qname:
                return self.resolve(r.target)
        return None


# ---- label / id helpers (shared by every emitter) ----------------------
_ID_SAFE = re.compile(r"[^A-Za-z0-9]")


def mermaid_id(text: str) -> str:
    """Stable, collision-resistant Mermaid node id from any string."""
    return _ID_SAFE.sub("_", text)


def short(ref: str) -> str:
    """Short label from a qualified name or usage path."""
    return ref.split("::")[-1]


def escape_label(text: str) -> str:
    """Make a label safe inside a Mermaid `["..."]` quoted node."""
    return text.replace('"', "'").replace("\n", " ").strip()


def first_sentence(doc: str | None, limit: int = 80) -> str:
    """First sentence of a doc comment, trimmed — used for node tooltips."""
    if not doc:
        return ""
    s = re.split(r"(?<=[.!?])\s", doc.strip(), maxsplit=1)[0]
    s = " ".join(s.split())
    return (s[: limit - 1] + "…") if len(s) > limit else s
