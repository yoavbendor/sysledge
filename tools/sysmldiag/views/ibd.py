"""Internal Block / interconnection — Mermaid flowchart.

part usages are nodes, their ports are small nodes, Connect relations are wired
edges between port endpoints. With sparse connectivity this view's main value
is honest: it shows how little of the wiring is actually modeled.
"""

from __future__ import annotations

from . import ViewResult, register
from ..graph import (
    Graph,
    REL_CONNECT,
    escape_label,
    mermaid_id,
    short,
)


@register("ibd")
def view(g: Graph) -> ViewResult:
    connects = g.rels(REL_CONNECT)
    ports = g.by_kind("port_usage", "interface_usage")

    lines = ["flowchart LR"]
    lines.append("  classDef port fill:#fef9e7,stroke:#b7950b,color:#7d6608;")
    lines.append("  classDef part fill:#eaf2f8,stroke:#2980b9,color:#1b4f72;")
    nodes: list[tuple[str, str]] = []
    seen: set[str] = set()

    def port_node(ref: str) -> str:
        pid = "PT_" + mermaid_id(ref)
        if pid not in seen:
            seen.add(pid)
            lines.append(f'  {pid}(["{escape_label(short(ref))}"]):::port')
        return pid

    for r in connects:
        a = port_node(r.source)
        b = port_node(r.target)
        lines.append(f"  {a} <--> {b}")

    # Show declared ports even when unconnected, so missing wiring is visible.
    for p in ports:
        pid = "PT_" + mermaid_id(p.qualified_name)
        if pid not in seen:
            seen.add(pid)
            lines.append(f'  {pid}(["{escape_label(p.name)}"]):::port')
        if p.source_ref:
            nodes.append((p.name, p.source_ref))

    notes = [
        f"{len(connects)} connection(s) across {len(ports)} declared port(s). "
        "Interconnection is under-modeled — add `connect` statements to complete the IBD."
    ]
    if not connects:
        lines.append('  _empty["(no connections modeled yet)"]')

    return ViewResult(
        name="ibd",
        title="Internal connections (IBD)",
        description="Ports and the connections wiring parts together.",
        mermaid="\n".join(lines),
        legend="Yellow = port/interface. `<-->` = a modeled connection.",
        nodes=sorted(set(nodes)),
        notes=notes,
    )
