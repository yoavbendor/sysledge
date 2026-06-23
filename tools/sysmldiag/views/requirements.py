"""Requirements traceability — Mermaid flowchart.

part --satisfies--> requirement <--verifies-- verification case

Requirements are coloured by verification state, which is the honest signal the
knowledge base exists to surface:
  green  = verified (a verification case targets it)
  amber  = satisfied by a part but not yet verified
  grey   = neither satisfied nor verified (an orphan requirement)
"""

from __future__ import annotations

from . import ViewResult, register
from ..graph import (
    Graph,
    REL_SATISFY,
    REL_VERIFY,
    escape_label,
    first_sentence,
    mermaid_id,
    short,
)


@register("requirements")
def view(g: Graph) -> ViewResult:
    satisfy = g.rels(REL_SATISFY)
    verify = g.rels(REL_VERIFY)
    verified_reqs = {r.target for r in verify}
    satisfied_reqs = {r.target for r in satisfy}

    lines = [
        "flowchart LR",
        "  classDef verified fill:#d5f5e3,stroke:#27ae60,color:#145a32;",
        "  classDef partial  fill:#fdebd0,stroke:#e67e22,color:#7e5109;",
        "  classDef orphan   fill:#f2f3f4,stroke:#85929e,color:#424949;",
        "  classDef part     fill:#eaf2f8,stroke:#2980b9,color:#1b4f72;",
        "  classDef vcase    fill:#f4ecf7,stroke:#8e44ad,color:#4a235a;",
    ]
    nodes: list[tuple[str, str]] = []
    seen: set[str] = set()

    def req_class(req: str) -> str:
        if req in verified_reqs:
            return "verified"
        if req in satisfied_reqs:
            return "partial"
        return "orphan"

    def emit_req(req: str):
        rid = "R_" + mermaid_id(req)
        if rid in seen:
            return rid
        seen.add(rid)
        lines.append(f'  {rid}["{escape_label(short(req))}"]:::{req_class(req)}')
        el = g.resolve(req)
        if el and el.source_ref:
            nodes.append((short(req), el.source_ref))
        return rid

    for r in satisfy:
        pid = "P_" + mermaid_id(r.source)
        if pid not in seen:
            seen.add(pid)
            lines.append(f'  {pid}(["{escape_label(short(r.source))}"]):::part')
        rid = emit_req(r.target)
        lines.append(f"  {pid} -->|satisfies| {rid}")

    for r in verify:
        vid = "V_" + mermaid_id(r.source)
        if vid not in seen:
            seen.add(vid)
            lines.append(f'  {vid}[/"{escape_label(short(r.source))}"/]:::vcase')
        rid = emit_req(r.target)
        lines.append(f"  {vid} -.->|verifies| {rid}")

    # Surface orphan requirements (declared but neither satisfied nor verified).
    orphans = [
        e.qualified_name
        for e in g.by_kind("requirement_definition")
        if e.qualified_name not in satisfied_reqs
        and e.qualified_name not in verified_reqs
    ]
    for req in orphans:
        emit_req(req)

    notes = []
    n_unverified = len(satisfied_reqs - verified_reqs)
    if n_unverified:
        notes.append(
            f"{n_unverified} requirement(s) are satisfied but not verified (amber) — "
            "candidate gaps for new verification cases."
        )
    if orphans:
        notes.append(
            f"{len(orphans)} requirement(s) are neither satisfied nor verified (grey)."
        )

    return ViewResult(
        name="requirements",
        title="Requirements traceability",
        description="Which part satisfies which requirement, and which is verified.",
        mermaid="\n".join(lines),
        legend=(
            "Blue rounded = component, purple = verification case. "
            "Green requirement = verified, amber = satisfied-but-unverified, "
            "grey = orphan."
        ),
        nodes=sorted(set(nodes)),
        notes=notes,
    )
