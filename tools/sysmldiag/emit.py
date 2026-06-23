"""Write views to disk: per-view `.mmd`, a combined GitHub-native `diagrams.md`,
and a `manifest.json`. GitHub/GitLab/VS Code render the fenced ```mermaid blocks
inline, so `diagrams.md` *is* the human-facing graphical view — no toolchain.
"""

from __future__ import annotations

import json
from pathlib import Path

from .views import ViewResult


def write_view_mmd(out_dir: Path, view: ViewResult) -> Path:
    path = out_dir / f"{view.name}.mmd"
    path.write_text(view.mermaid + "\n")
    return path


def _node_table(view: ViewResult) -> list[str]:
    if not view.nodes:
        return []
    rows = ["", "<details><summary>Source elements</summary>", "",
            "| Element | Source |", "|---|---|"]
    for label, ref in view.nodes:
        rows.append(f"| `{label}` | `{ref}` |")
    rows += ["", "</details>", ""]
    return rows


def write_markdown(out_dir: Path, views: list[ViewResult], title: str) -> Path:
    md: list[str] = [
        f"# {title} — model diagrams",
        "",
        "_Generated from the SysML knowledge graph by `tools/sysmldiag`. "
        "Do not hand-edit — re-run the generator._",
        "",
        "## Contents",
        "",
    ]
    for v in views:
        anchor = v.title.lower().replace(" ", "-").replace("(", "").replace(")", "")
        md.append(f"- [{v.title}](#{anchor}) — {v.description}")
    md.append("")

    for v in views:
        md.append(f"## {v.title}")
        md.append("")
        md.append(v.description)
        if v.legend:
            md += ["", f"*{v.legend}*"]
        md += ["", "```mermaid", v.mermaid, "```"]
        if v.notes:
            md.append("")
            for n in v.notes:
                md.append(f"> ⚠️ {n}")
        md += _node_table(v)
        md.append("")

    path = out_dir / "diagrams.md"
    path.write_text("\n".join(md))
    return path


def write_manifest(out_dir: Path, views: list[ViewResult], svgs: dict) -> Path:
    manifest = {
        "generator": "tools/sysmldiag",
        "views": [
            {
                "name": v.name,
                "title": v.title,
                "mmd": f"{v.name}.mmd",
                "svg": svgs.get(v.name),
                "notes": v.notes,
                "node_count": len(v.nodes),
            }
            for v in views
        ],
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path
