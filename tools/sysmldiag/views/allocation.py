"""Allocation / RFLP overview — Mermaid flowchart.

Cross-layer satisfy edges: parts (Logical/Physical) realizing requirements (R).
Layers are drawn as columns so the system reads top-down R -> L/P, the spine an
advisory agent follows to answer "is requirement X implemented, and by what?".
"""

from __future__ import annotations

from . import ViewResult, register
from ..graph import (
    Graph,
    REL_SATISFY,
    escape_label,
    mermaid_id,
    short,
)


@register("allocation")
def view(g: Graph) -> ViewResult:
    satisfy = g.rels(REL_SATISFY)

    lines = ["flowchart LR"]
    lines += [
        "  classDef req fill:#fdedec,stroke:#cb4335,color:#7b241c;",
        "  classDef impl fill:#eaf2f8,stroke:#2980b9,color:#1b4f72;",
    ]
    nodes: list[tuple[str, str]] = []
    parts: set[str] = set()
    reqs: set[str] = set()
    edges: list[tuple[str, str]] = []

    for r in satisfy:
        pid = "I_" + mermaid_id(r.source)
        rid = "R_" + mermaid_id(r.target)
        parts.add(f'  {pid}(["{escape_label(short(r.source))}"]):::impl')
        rdef = g.resolve(r.target)
        reqs.add(f'  {rid}["{escape_label(short(r.target))}"]:::req')
        edges.append((pid, rid))
        if rdef and rdef.source_ref:
            nodes.append((short(r.target), rdef.source_ref))

    lines.append('  subgraph impl["Implementation (Logical/Physical)"]')
    lines += sorted(parts)
    lines.append("  end")
    lines.append('  subgraph reqs["Requirements"]')
    lines += sorted(reqs)
    lines.append("  end")
    for pid, rid in sorted(set(edges)):
        lines.append(f"  {pid} -->|satisfies| {rid}")

    n_reqs = len({r.target for r in satisfy})
    return ViewResult(
        name="allocation",
        title="Allocation (RFLP overview)",
        description="Which implementation part realizes which requirement, across layers.",
        mermaid="\n".join(lines),
        legend="Red = requirement, blue = implementing part. Arrow = satisfies.",
        nodes=sorted(set(nodes)),
        notes=[
            f"{len(set(edges))} satisfy link(s) binding parts to {n_reqs} requirement(s)."
        ],
    )
