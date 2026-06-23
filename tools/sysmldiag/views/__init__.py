"""View registry: each view is a pure function `Graph -> ViewResult`.

A view maps one SysML v2 *aspect* onto one Mermaid diagram type. Views never
call an LLM and never read the filesystem beyond the graph they are handed, so
their output is fully determined by the index — golden-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..graph import Graph


@dataclass
class ViewResult:
    name: str  # stable slug, also the .mmd filename
    title: str  # human heading
    description: str  # one-line "what this shows"
    mermaid: str  # the diagram body (a complete Mermaid document)
    legend: str = ""  # optional legend prose shown under the diagram
    # (label, source_ref) pairs so a reader can jump picture -> source.
    nodes: list[tuple[str, str]] = field(default_factory=list)
    # Honest gaps the diagram surfaces (e.g. "no flow edges modeled").
    notes: list[str] = field(default_factory=list)


# Populated by register(); ordered for deterministic emission.
_REGISTRY: "dict[str, callable]" = {}


def register(slug: str):
    def deco(fn):
        _REGISTRY[slug] = fn
        return fn

    return deco


def all_views() -> "dict[str, callable]":
    return dict(_REGISTRY)


def render(slug: str, graph: Graph) -> ViewResult:
    return _REGISTRY[slug](graph)


# Import view modules so their @register decorators run. Order = emission order.
from . import requirements  # noqa: E402,F401
from . import bdd  # noqa: E402,F401
from . import ibd  # noqa: E402,F401
from . import behavior  # noqa: E402,F401
from . import package_map  # noqa: E402,F401
from . import allocation  # noqa: E402,F401
