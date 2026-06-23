"""CLI: python3 -m sysmldiag --index .nomograph/index.json --out reports/diagrams

Generates Mermaid diagrams for every (or selected) SysML aspect. Deterministic
and offline; SVG export is attempted only when `mmdc` is present.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import views as views_pkg
from .emit import write_manifest, write_markdown, write_view_mmd
from .graph import Graph
from .render_svg import export_svgs, svg_available


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sysmldiag", description=__doc__)
    ap.add_argument("--index", default=".nomograph/index.json")
    ap.add_argument("--out", default="reports/diagrams")
    ap.add_argument(
        "--views",
        default="all",
        help="comma-separated view slugs, or 'all' (default). "
        f"Available: {','.join(views_pkg.all_views())}",
    )
    ap.add_argument("--title", default="nanos3reader")
    ap.add_argument(
        "--format",
        choices=["mermaid", "svg", "both"],
        default="mermaid",
        help="'svg'/'both' attempt mmdc export, skipped gracefully if absent.",
    )
    args = ap.parse_args(argv)

    index_path = Path(args.index)
    if not index_path.exists():
        print(f"error: index not found: {index_path}", file=sys.stderr)
        return 2

    g = Graph.load(index_path)
    available = views_pkg.all_views()
    slugs = list(available) if args.views == "all" else args.views.split(",")
    unknown = [s for s in slugs if s not in available]
    if unknown:
        print(f"error: unknown view(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = [views_pkg.render(s, g) for s in slugs]
    for v in results:
        write_view_mmd(out_dir, v)

    svgs: dict = {}
    if args.format in ("svg", "both"):
        if svg_available():
            svgs = export_svgs(out_dir, [v.name for v in results])
        else:
            print(
                "note: mmdc not found — skipping SVG export (Mermaid sources written).",
                file=sys.stderr,
            )

    write_markdown(out_dir, results, args.title)
    write_manifest(out_dir, results, svgs)

    print(
        f"generated {len(results)} view(s) -> {out_dir}/  "
        f"({'svg: ' + str(len(svgs)) if svgs else 'mermaid only'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
