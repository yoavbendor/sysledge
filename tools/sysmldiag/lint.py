"""Lightweight structural lint for generated Mermaid.

Not a full Mermaid parser — a cheap, dependency-free sanity gate so CI can catch
the failure modes a generator actually produces (unbalanced subgraphs, bad
headers, unclosed class bodies) without needing Node/`mmdc`. The richer check is
rendering with `mmdc`/Kroki, which `render_svg` does when available.
"""

from __future__ import annotations

_VALID_HEADERS = (
    "flowchart ",
    "graph ",
    "classDiagram",
    "stateDiagram",
    "sequenceDiagram",
    "requirementDiagram",
    "erDiagram",
    "block-beta",
)


def lint_mermaid(text: str) -> list[str]:
    """Return a list of human-readable problems; empty list means it passed."""
    issues: list[str] = []
    lines = [ln.rstrip() for ln in text.splitlines()]
    nonblank = [ln for ln in lines if ln.strip()]
    if not nonblank:
        return ["empty diagram"]

    header = nonblank[0].strip()
    if not header.startswith(_VALID_HEADERS):
        issues.append(f"unrecognized diagram header: {header!r}")

    depth = 0
    brace = 0
    for ln in lines:
        s = ln.strip()
        if s.startswith("subgraph "):
            depth += 1
        elif s == "end":
            depth -= 1
            if depth < 0:
                issues.append("'end' without matching 'subgraph'")
                depth = 0
        brace += s.count("{") - s.count("}")
    if depth != 0:
        issues.append(f"{depth} unclosed subgraph(s)")
    if brace != 0:
        issues.append(f"unbalanced braces (delta {brace})")
    return issues
