#!/usr/bin/env bash
# Generate human-facing diagrams from the SysML knowledge graph.
#
# Thin wrapper around the `sysmldiag` component (tools/sysmldiag), a deterministic
# SysML v2 -> Mermaid generator. It emits one diagram per SysML aspect
# (requirements, BDD, IBD, behavior, model map, allocation) under reports/diagrams/
# as .mmd files plus a GitHub-native diagrams.md that renders inline (zero tooling).
# No LLM is used in the rendering path. SVG export is attempted only if `mmdc` is
# installed; otherwise it is skipped and the Mermaid sources remain the deliverable.
#
# Usage: .nomograph/scripts/diagrams.sh [index.json] [out-dir]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INDEX="${1:-.nomograph/index.json}"
OUT="${2:-reports/diagrams}"

cd "$REPO_ROOT"
PYTHONPATH="tools" python3 -m sysmldiag \
    --index "$INDEX" \
    --out "$OUT" \
    --title nanos3reader \
    --format both
