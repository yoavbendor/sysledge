"""Block Definition Diagram — Mermaid classDiagram.

part definitions become classes; their attributes (TypedBy) become members,
their ports are tagged members. Specialize relations become inheritance,
owned part usages become composition.
"""

from __future__ import annotations

from . import ViewResult, register
from ..graph import (
    Graph,
    REL_SPECIALIZE,
    escape_label,
    mermaid_id,
    short,
)


@register("bdd")
def view(g: Graph) -> ViewResult:
    part_defs = g.by_kind("part_definition")
    def_names = {e.qualified_name for e in part_defs}

    lines = ["classDiagram"]
    nodes: list[tuple[str, str]] = []

    for pd in part_defs:
        cid = mermaid_id(short(pd.qualified_name))
        lines.append(f"  class {cid}[\"{escape_label(short(pd.qualified_name))}\"] {{")
        for m in g.members_of(pd.qualified_name):
            t = g.type_of(m.qualified_name)
            tname = short(t.qualified_name) if t else "?"
            if m.kind == "attribute_usage":
                lines.append(f"    +{m.name} : {tname}")
            elif m.kind in ("port_usage", "interface_usage"):
                stereo = m.kind.split("_")[0]
                lines.append(f"    +{m.name} : «{stereo}» {tname}")
        lines.append("  }")
        if pd.source_ref:
            nodes.append((short(pd.qualified_name), pd.source_ref))

    # Inheritance: Super <|-- Sub  (variation points / backends)
    for r in g.rels(REL_SPECIALIZE):
        sub = g.resolve(r.source)
        sup = g.resolve(r.target)
        if not sub or not sup:
            continue
        lines.append(
            f"  {mermaid_id(short(sup.qualified_name))} <|-- "
            f"{mermaid_id(short(sub.qualified_name))}"
        )

    # Composition: Owner *-- Part  (owner has a part usage typed by another def)
    comps: set[tuple[str, str, str]] = set()
    for pd in part_defs:
        for m in g.members_of(pd.qualified_name):
            if m.kind != "part_usage":
                continue
            t = g.type_of(m.qualified_name)
            if t and t.qualified_name in def_names:
                comps.add(
                    (
                        mermaid_id(short(pd.qualified_name)),
                        mermaid_id(short(t.qualified_name)),
                        m.name,
                    )
                )
    for owner, part, role in sorted(comps):
        lines.append(f'  {owner} *-- {part} : {role}')

    return ViewResult(
        name="bdd",
        title="Block definition diagram",
        description="Part definitions, their attributes/ports, inheritance and composition.",
        mermaid="\n".join(lines),
        legend=(
            "`<|--` = specialization (variant backend), `*--` = composition "
            "(owned part). «port»/«interface» tag connection points."
        ),
        nodes=sorted(set(nodes)),
        notes=[],
    )
