"""Layer B ingestion agents: doc chunk + knowledge graph -> list[Patch].

Each agent is a small, single-purpose function that turns a piece of source
documentation into proposed `Patch` objects. Agents **only ever enqueue patches**;
they never write `.sysml` — `authority.py` is the single writer, and it validates
every edit. That keeps machine-generated facts safe by construction.

Design (per the plan's "lean + pydantic" decision):
- LLM calls go through the existing `llm.complete(system, user, cfg)`; the callable
  is **injectable** so the whole suite runs offline with a fake.
- Doc text is loaded by the existing `ingest_eval.doc_reader`; chunking is stdlib
  markdown-heading splitting.
- The LLM returns **JSON**, parsed straight into `Patch.parse(...)` — pydantic
  rejects malformed/unsourced output at the boundary, so a bad item is skipped, not
  fatal, and never reaches the queue.
- **Provenance is authoritative, not model-supplied.** The agent computes each
  fragment's `@Provenance.source` from the manifest source-id + doc + heading and
  substitutes it in; the model only marks *where* the annotation goes (`<SOURCE>`).
- `ReconcilerAgent` and `PortMapperAgent` are **deterministic** (no LLM): the former
  uses the indexed `Graph` to dedupe/flag, the latter parses markdown tables.

Guardrails honored: no fact without `@Provenance` (maturity always `"concept"` for
extracted facts); never silently overwrite a sourced fact (contradictions are flagged
to `reports/review/` + `log.md`, never emitted as edits); reuse before redefine
(reconcile drops duplicates the index already has).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from ..graph import Graph
from ..llm import complete as llm_complete
from .queue import Patch, PatchError

__all__ = [
    "Chunk",
    "ScanResult",
    "Contradiction",
    "ReconcileResult",
    "AgentError",
    "chunk_markdown",
    "scan",
    "connect",
    "reconcile",
    "write_review",
    "port_map",
]

# Placeholder the model is told to emit verbatim; the agent substitutes the real
# (authoritative) provenance source string before building the Patch.
SOURCE_TOKEN = "<SOURCE>"

# Route a fragment to the model file + aspect package by its declared kind. Mirrors
# the pilot layout: models/<system>/{structure,requirements,behavior}.sysml with
# packages <Base>{Structure,Requirements,Behavior}.
ASPECT_BY_KIND: dict[str, tuple[str, str]] = {
    "part": ("structure.sysml", "Structure"),
    "item": ("structure.sysml", "Structure"),
    "port": ("structure.sysml", "Structure"),
    "interface": ("structure.sysml", "Structure"),
    "connection": ("structure.sysml", "Structure"),
    "requirement": ("requirements.sysml", "Requirements"),
    "constraint": ("requirements.sysml", "Requirements"),
    "action": ("behavior.sysml", "Behavior"),
    "state": ("behavior.sysml", "Behavior"),
}
DEFAULT_ASPECT = ("structure.sysml", "Structure")

Completer = Callable[..., str]


class AgentError(RuntimeError):
    """An agent could not interpret a model response (e.g. non-JSON output)."""


# --------------------------------------------------------------------------- chunking
@dataclass(frozen=True)
class Chunk:
    heading: str
    text: str
    source: str  # full @Provenance source ref, e.g. "sys@abc:README.md#range-reads"


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "section"


_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def chunk_markdown(text: str, *, source_id: str, doc_name: str) -> list[Chunk]:
    """Split markdown into one chunk per ATX heading (heading + its body).

    Each chunk's `source` is the authoritative provenance ref
    `<source_id>:<doc_name>#<heading-slug>`. Text before the first heading becomes a
    `(preamble)` chunk; a doc with no headings yields a single chunk.
    """
    lines = text.splitlines()
    chunks: list[Chunk] = []
    heading = "(preamble)"
    buf: list[str] = []

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            chunks.append(
                Chunk(
                    heading=heading,
                    text=body,
                    source=f"{source_id}:{doc_name}#{_slug(heading)}",
                )
            )

    for line in lines:
        m = _HEADING.match(line)
        if m:
            flush()
            heading = m.group(2).strip()
            buf = [line]
        else:
            buf.append(line)
    flush()
    return chunks


# ----------------------------------------------------------------------- JSON helpers
def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _loads_json_array(text: str) -> list[dict]:
    """Parse a model response into a list of dicts. Tolerates code fences and a
    single bare object; raises AgentError on anything non-JSON."""
    body = _strip_fences(text)
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise AgentError(f"model did not return JSON: {e}: {body[:200]!r}") from e
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise AgentError(f"expected a JSON array, got {type(data).__name__}")
    return [d for d in data if isinstance(d, dict)]


# --------------------------------------------------------------------- ScannerAgent
_SCAN_SYSTEM = """You convert one section of architecture documentation into SysML v2
model fragments. Return ONLY a JSON array (no prose, no markdown fences). Each item:
  {"kind": "<part|requirement|action|item|port>",
   "name": "<PascalCaseName>",
   "sysml": "<a single SysML v2 def, e.g. `part def Name { ... }`>"}
Rules for each "sysml" fragment:
- Exactly one definition (part def / requirement def / action def / item def).
- It MUST contain `@Provenance { source = "%s"; maturity = "concept"; }` verbatim,
  because this is extracted, unverified information. Copy that source string exactly.
- PascalCase for definition names; reuse primitive types String/Integer/Boolean/Real.
- Emit only facts actually stated in the section; do not invent.""" % SOURCE_TOKEN


def _scan_user(chunk: Chunk) -> str:
    return (
        f"Section heading: {chunk.heading}\n\n"
        f"Section text:\n'''\n{chunk.text}\n'''\n\n"
        "Produce the JSON array now."
    )


@dataclass
class ScanResult:
    patches: list[Patch] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (name, reason)


def scan(
    chunk: Chunk,
    *,
    package_base: str,
    model_dir: str,
    complete: Completer = llm_complete,
    cfg=None,
) -> ScanResult:
    """Emit `add` patches for the defs found in `chunk`. Malformed items (failing
    `Patch.parse`) are skipped with a reason, never enqueued."""
    raw = complete(_SCAN_SYSTEM, _scan_user(chunk), cfg)
    result = ScanResult()
    for item in _loads_json_array(raw):
        name = str(item.get("name", "?"))
        sysml = item.get("sysml")
        if not isinstance(sysml, str) or not sysml.strip():
            result.skipped.append((name, "missing sysml fragment"))
            continue
        kind = _norm_kind(str(item.get("kind", "part")))
        rel_file, suffix = ASPECT_BY_KIND.get(kind, DEFAULT_ASPECT)
        fragment = sysml.replace(SOURCE_TOKEN, chunk.source)
        try:
            patch = Patch.parse(
                {
                    "op": "add",
                    "target_file": f"{model_dir.rstrip('/')}/{rel_file}",
                    "target_package": f"{package_base}{suffix}",
                    "sysml": fragment,
                    "provenance": {"source": chunk.source, "maturity": "concept"},
                    "agent": "ScannerAgent",
                    "rationale": f"scanned from {chunk.heading}",
                }
            )
        except PatchError as e:
            result.skipped.append((name, str(e).splitlines()[0]))
            continue
        result.patches.append(patch)
    return result


# --------------------------------------------------------------------- ConnectorAgent
_CONNECT_SYSTEM = """You identify connections/compositions between EXISTING parts of a
system and express them in SysML v2. Return ONLY a JSON array (no prose, no fences).
Each item: {"name": "<short label>", "sysml": "<one `connect a.x to b.y;` or composition>"}.
Rules:
- Only reference part names from the provided list of existing parts.
- Each fragment MUST contain `@Provenance { source = "%s"; maturity = "concept"; }` verbatim.
- If the section states no connection between existing parts, return [].""" % SOURCE_TOKEN


def _connect_user(chunk: Chunk, part_names: list[str]) -> str:
    listed = ", ".join(part_names) if part_names else "(none indexed yet)"
    return (
        f"Existing parts: {listed}\n\n"
        f"Section heading: {chunk.heading}\n\n"
        f"Section text:\n'''\n{chunk.text}\n'''\n\n"
        "Produce the JSON array of connections now."
    )


def connect(
    chunk: Chunk,
    graph: Graph,
    *,
    package_base: str,
    model_dir: str,
    complete: Completer = llm_complete,
    cfg=None,
) -> ScanResult:
    """Emit `add` patches expressing connections between parts already in the index.
    Seeded with existing part names so the model can only wire up real elements."""
    part_names = [e.name for e in graph.by_kind("part", "part_def")]
    raw = complete(_CONNECT_SYSTEM, _connect_user(chunk, part_names), cfg)
    rel_file, suffix = ASPECT_BY_KIND["connection"]
    result = ScanResult()
    for item in _loads_json_array(raw):
        name = str(item.get("name", "?"))
        sysml = item.get("sysml")
        if not isinstance(sysml, str) or not sysml.strip():
            result.skipped.append((name, "missing sysml fragment"))
            continue
        fragment = sysml.replace(SOURCE_TOKEN, chunk.source)
        try:
            result.patches.append(
                Patch.parse(
                    {
                        "op": "add",
                        "target_file": f"{model_dir.rstrip('/')}/{rel_file}",
                        "target_package": f"{package_base}{suffix}",
                        "sysml": fragment,
                        "provenance": {"source": chunk.source, "maturity": "concept"},
                        "agent": "ConnectorAgent",
                        "rationale": f"connection from {chunk.heading}",
                    }
                )
            )
        except PatchError as e:
            result.skipped.append((name, str(e).splitlines()[0]))
    return result


# ------------------------------------------------------------------ ReconcilerAgent
@dataclass(frozen=True)
class Contradiction:
    name: str
    existing: str  # qualified name already in the index
    existing_kind: str
    new_source: str
    detail: str


@dataclass
class ReconcileResult:
    patches: list[Patch] = field(default_factory=list)  # kept (novel) patches
    dropped: list[str] = field(default_factory=list)  # duplicate names dropped
    contradictions: list[Contradiction] = field(default_factory=list)


_DEF_DECL = re.compile(
    r"\b(part|requirement|action|item|attribute|connection|interface|port|state|constraint)"
    r"\s+def\s+(\w+)"
)
_USAGE_DECL = re.compile(r"\b(port|part|attribute|item)\s+(\w+)\s*[:{;]")


def _frag_decl(sysml: str) -> tuple[str, str]:
    """(kind, name) declared by a fragment; ('', '') if not recognizable."""
    m = _DEF_DECL.search(sysml)
    if m:
        return _norm_kind(m.group(1)), m.group(2)
    m = _USAGE_DECL.search(sysml)
    if m:
        return _norm_kind(m.group(1)), m.group(2)
    return "", ""


def _norm_kind(kind: str) -> str:
    """Normalize a kind token from a fragment or a Graph element ('part_def' -> 'part')."""
    return re.split(r"[ _]", kind.strip().lower(), maxsplit=1)[0]


def reconcile(patches: list[Patch], graph: Graph) -> ReconcileResult:
    """Reconcile freshly-scanned `add` patches against the indexed model.

    - name not in the index            -> keep (novel fact);
    - name present, same kind          -> drop (duplicate; reuse before redefine);
    - name present, *different* kind   -> contradiction (flag for review, never emit).

    Never proposes an overwrite of an existing element (hard guardrail #2/#4)."""
    by_name: dict[str, list] = {}
    for el in graph.elements.values():
        by_name.setdefault(el.name, []).append(el)

    result = ReconcileResult()
    for p in patches:
        kind, name = _frag_decl(p.sysml)
        existing = by_name.get(name)
        if not name or not existing:
            result.patches.append(p)
            continue
        same_kind = next((e for e in existing if _norm_kind(e.kind) == kind), None)
        if same_kind is not None:
            result.dropped.append(name)
            continue
        other = existing[0]
        result.contradictions.append(
            Contradiction(
                name=name,
                existing=other.qualified_name,
                existing_kind=other.kind,
                new_source=p.provenance.source,
                detail=(
                    f"scanner proposes {kind or 'element'} {name!r} but the index already "
                    f"has {other.qualified_name} ({other.kind})"
                ),
            )
        )
    return result


def write_review(contradictions: list[Contradiction], repo_root: Path) -> Optional[Path]:
    """Surface contradictions to `reports/review/` and append a `log.md` line each.
    Returns the review file path, or None if there were none. (IO only — kept
    separate from `reconcile` so the logic is testable offline.)"""
    if not contradictions:
        return None
    repo_root = Path(repo_root)
    review_dir = repo_root / "reports" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d")
    path = review_dir / f"contradictions-{stamp}.md"
    lines = [f"# Reconciliation contradictions — {time.strftime('%Y-%m-%d')}\n"]
    for c in contradictions:
        lines.append(
            f"- **{c.name}** — {c.detail}. New source `{c.new_source}`. "
            f"Existing `{c.existing}`. *Human review required; not auto-applied.*"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    log = repo_root / "log.md"
    with log.open("a", encoding="utf-8") as f:
        for c in contradictions:
            f.write(
                f"\n- {time.strftime('%Y-%m-%d')} **contradiction** `{c.name}` "
                f"(new source={c.new_source}): {c.detail} — flagged to "
                f"reports/review/{path.name}, not applied.\n"
            )
    return path


# ------------------------------------------------------------------- PortMapperAgent
_TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")


def _parse_md_table(text: str) -> list[dict[str, str]]:
    """Parse GitHub-style markdown tables into row dicts keyed by lower-cased header.
    Returns [] when no table is present (stdlib; deterministic — no LLM)."""
    rows: list[list[str]] = []
    for line in text.splitlines():
        m = _TABLE_ROW.match(line)
        if m:
            rows.append([c.strip() for c in m.group(1).split("|")])
    if len(rows) < 2:
        return []
    header = [h.lower() for h in rows[0]]
    out: list[dict[str, str]] = []
    for r in rows[1:]:
        if all(set(c) <= {"-", ":", ""} for c in r):  # separator row
            continue
        if len(r) != len(header):
            continue
        out.append(dict(zip(header, r)))
    return out


def port_map(
    chunk: Chunk,
    *,
    package_base: str,
    model_dir: str,
    anchor: Optional[str] = None,
) -> list[Patch]:
    """Turn a markdown interface table in `chunk` into `port` patches (deterministic).

    Recognized columns (case-insensitive): a name column (`name`/`port`/`signal`) and
    a `type` column; an optional `direction`/`dir` becomes a `// in|out` note. When
    `anchor` is given the ports are a `modify` on that part; otherwise they are added
    to `structure.sysml`."""
    rel_file, suffix = ASPECT_BY_KIND["port"]
    patches: list[Patch] = []
    for row in _parse_md_table(chunk.text):
        name = row.get("name") or row.get("port") or row.get("signal")
        ptype = row.get("type") or row.get("datatype")
        if not name or not ptype:
            continue
        name = _camel(name)
        direction = (row.get("direction") or row.get("dir") or "").strip().lower()
        note = f"  // {direction}" if direction else ""
        fragment = (
            f"port {name} : {_pascal(ptype)} {{{note}\n"
            f'    @Provenance {{ source = "{chunk.source}"; maturity = "concept"; }}\n'
            f"}}"
        )
        try:
            patches.append(
                Patch.parse(
                    {
                        "op": "modify" if anchor else "add",
                        "target_file": f"{model_dir.rstrip('/')}/{rel_file}",
                        "target_package": f"{package_base}{suffix}",
                        "anchor": anchor,
                        "sysml": fragment,
                        "provenance": {"source": chunk.source, "maturity": "concept"},
                        "agent": "PortMapperAgent",
                        "rationale": f"interface table in {chunk.heading}",
                    }
                )
            )
        except PatchError:
            continue
    return patches


def _camel(text: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", text.strip())
    parts = [p for p in parts if p]
    if not parts:
        return "port"
    return parts[0][:1].lower() + parts[0][1:] + "".join(p.title() for p in parts[1:])


def _pascal(text: str) -> str:
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", text.strip()) if p]
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Item"
