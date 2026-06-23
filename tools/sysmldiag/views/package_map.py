"""Model map — Mermaid flowchart of package containment.

The "browser" view: every package and the definitions it contains, coloured by
RFLP layer. This is the at-a-glance index of what the model covers.
"""

from __future__ import annotations

from . import ViewResult, register
from ..graph import (
    Graph,
    LAYER_ORDER,
    escape_label,
    mermaid_id,
    short,
)

_LAYER_CLASS = {
    "Requirements": "lreq",
    "Function": "lfun",
    "Logical": "llog",
    "Physical": "lphy",
}

_DEFINITION_KINDS = {
    "part_definition",
    "requirement_definition",
    "action_definition",
    "attribute_definition",
    "port_definition",
    "interface_definition",
    "verification_definition",
    "metadata_definition",
}


@register("package_map")
def view(g: Graph) -> ViewResult:
    packages = g.by_kind("package_definition")

    lines = ["flowchart TD"]
    lines += [
        "  classDef lreq fill:#fdedec,stroke:#cb4335,color:#7b241c;",
        "  classDef lfun fill:#fef5e7,stroke:#ca6f1e,color:#7e5109;",
        "  classDef llog fill:#eaf2f8,stroke:#2980b9,color:#1b4f72;",
        "  classDef lphy fill:#eafaf1,stroke:#229954,color:#145a32;",
        "  classDef lnone fill:#f4f6f7,stroke:#909497,color:#515a5a;",
    ]
    nodes: list[tuple[str, str]] = []

    for pkg in packages:
        defs = [
            m for m in g.members_of(pkg.qualified_name) if m.kind in _DEFINITION_KINDS
        ]
        if not defs:
            continue
        pid = "pkg_" + mermaid_id(pkg.qualified_name)
        lines.append(f'  subgraph {pid}["{escape_label(short(pkg.qualified_name))}"]')
        for d in defs:
            did = mermaid_id(d.qualified_name)
            cls = _LAYER_CLASS.get(d.layer or "", "lnone")
            lines.append(f'    {did}["{escape_label(short(d.qualified_name))}"]:::{cls}')
            if d.source_ref:
                nodes.append((short(d.qualified_name), d.source_ref))
        lines.append("  end")

    counts = {layer: 0 for layer in LAYER_ORDER}
    for e in g.elements.values():
        if e.kind in _DEFINITION_KINDS and e.layer in counts:
            counts[e.layer] += 1
    summary = ", ".join(f"{layer}: {n}" for layer, n in counts.items() if n)

    return ViewResult(
        name="package_map",
        title="Model map (packages)",
        description="Every package and the definitions it contains, by RFLP layer.",
        mermaid="\n".join(lines),
        legend=f"Colour = RFLP layer. Definitions per layer — {summary}.",
        nodes=sorted(set(nodes)),
        notes=[],
    )
