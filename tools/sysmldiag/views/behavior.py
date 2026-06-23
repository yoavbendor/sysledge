"""Behavior / actions — Mermaid flowchart.

Shows action definitions and their decomposition (member sub-actions) plus
parameters. Succession/flow ordering is not yet captured by the index, so this
view honestly flags that gap rather than inventing an order.
"""

from __future__ import annotations

from . import ViewResult, register
from ..graph import (
    Graph,
    escape_label,
    first_sentence,
    mermaid_id,
    short,
)


@register("behavior")
def view(g: Graph) -> ViewResult:
    actions = g.by_kind("action_definition", "action_usage")
    action_names = {a.qualified_name for a in actions}

    lines = ["flowchart TD"]
    lines.append("  classDef act fill:#e8f8f5,stroke:#16a085,color:#0e6251;")
    lines.append("  classDef param fill:#fdfefe,stroke:#aab7b8,color:#566573;")
    nodes: list[tuple[str, str]] = []
    seen: set[str] = set()

    def act_node(a) -> str:
        aid = "A_" + mermaid_id(a.qualified_name)
        if aid not in seen:
            seen.add(aid)
            lines.append(f'  {aid}["{escape_label(short(a.qualified_name))}"]:::act')
            if a.source_ref:
                nodes.append((short(a.qualified_name), a.source_ref))
        return aid

    for a in actions:
        aid = act_node(a)
        for m in g.members_of(a.qualified_name):
            if m.qualified_name in action_names:  # sub-action: decomposition
                lines.append(f"  {aid} --> {act_node(m)}")
            elif m.kind == "parameter_usage":
                pid = "PM_" + mermaid_id(m.qualified_name)
                if pid not in seen:
                    seen.add(pid)
                    lines.append(f'  {pid}(["{escape_label(m.name)}"]):::param')
                lines.append(f"  {aid} -.->|param| {pid}")

    if not actions:
        lines.append('  _empty["(no actions modeled yet)"]')

    return ViewResult(
        name="behavior",
        title="Behavior (actions)",
        description="Action decomposition and parameters.",
        mermaid="\n".join(lines),
        legend="Teal = action, grey rounded = parameter. Solid = sub-action.",
        nodes=sorted(set(nodes)),
        notes=[
            "Execution order (succession/flow) is not modeled yet — edges show "
            "containment/parameters only. Add `then`/`succession` to get a true flow."
        ],
    )
