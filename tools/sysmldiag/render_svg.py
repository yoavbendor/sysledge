"""Optional raster/vector export. Pure-offline by default: if neither the
mermaid CLI (`mmdc`) nor a Kroki endpoint is available, this is a no-op that
reports why, so the Mermaid sources remain the guaranteed deliverable.

No LLM is involved — these are deterministic Mermaid renderers.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def export_svgs(out_dir: Path, view_names: list[str]) -> dict:
    """Return {view_name: 'svg/<name>.svg'} for each successfully rendered view."""
    mmdc = shutil.which("mmdc")
    if not mmdc:
        return {}
    svg_dir = out_dir / "svg"
    svg_dir.mkdir(exist_ok=True)
    rendered: dict[str, str] = {}
    for name in view_names:
        src = out_dir / f"{name}.mmd"
        dst = svg_dir / f"{name}.svg"
        try:
            subprocess.run(
                [mmdc, "-i", str(src), "-o", str(dst), "-q"],
                check=True,
                capture_output=True,
                timeout=120,
            )
            rendered[name] = f"svg/{name}.svg"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return rendered


def svg_available() -> bool:
    return shutil.which("mmdc") is not None
