#!/usr/bin/env bash
# Generate human-facing diagrams from the SysML knowledge graph.
#
# nomograph-sysml renders TABLES (markdown/html/csv) and an SVG status badge, but not box-and-arrow
# diagrams. This script derives Mermaid diagrams from the indexed relationships (satisfy / verify /
# composition / specialization) so the models can be shown graphically on request. Output: .mmd files
# under reports/diagrams/, renderable anywhere Mermaid is supported (GitHub, VS Code, mermaid.live, or
# the project's Mermaid renderer).
#
# Usage: .nomograph/scripts/diagrams.sh [index.json]
set -euo pipefail

INDEX="${1:-.nomograph/index.json}"
OUT="reports/diagrams"
mkdir -p "$OUT"

# Short, mermaid-safe label from a qualified name (last "::" segment, dots kept).
short() { sed -E 's/.*:://; s/ \(.*$//'; }
# Mermaid-safe node id.
nid() { echo "$1" | sed -E 's/[^A-Za-z0-9]/_/g'; }

q() { nomograph-sysml query --index "$INDEX" --compact --limit 500 "$@" 2>/dev/null | jq -r '.matches[]'; }

# ---- 1. Requirements traceability -------------------------------------------------------------------
# requirement  <-- satisfy -- part      ;  requirement <-- verify -- verification case
# Requirements are coloured: green = verified, amber = satisfied-but-unverified (an honest gap).
{
  echo "flowchart LR"
  echo "  classDef verified fill:#d5f5e3,stroke:#27ae60,color:#145a32;"
  echo "  classDef partial  fill:#fdebd0,stroke:#e67e22,color:#7e5109;"
  echo "  classDef part     fill:#eaf2f8,stroke:#2980b9,color:#1b4f72;"
  echo "  classDef vcase    fill:#f4ecf7,stroke:#8e44ad,color:#4a235a;"

  verified="$(q --rel verify | sed -E 's/ -> Verify -> /\t/; s/ \(.*$//')"

  # satisfy edges + requirement nodes
  q --rel satisfy | sed -E 's/ -> Satisfy -> /\t/; s/ \(.*$//' | while IFS=$'\t' read -r partq reqq; do
    part="$(echo "$partq" | short)";  preq="$(echo "$reqq" | short)"
    pid="P_$(nid "$part")";           rid="R_$(nid "$preq")"
    echo "  ${pid}([\"$part\"]):::part -->|satisfies| ${rid}[\"$preq\"]"
    if echo "$verified" | grep -q "	${reqq}$"; then echo "  class ${rid} verified;"; else echo "  class ${rid} partial;"; fi
  done

  # verify edges + verification-case nodes
  echo "$verified" | while IFS=$'\t' read -r caseq reqq; do
    [ -z "$caseq" ] && continue
    vc="$(echo "$caseq" | short)";  preq="$(echo "$reqq" | short)"
    vid="V_$(nid "$vc")";           rid="R_$(nid "$preq")"
    echo "  ${vid}[/\"$vc\"/]:::vcase -.->|verifies| ${rid}"
  done
} | awk '!seen[$0]++' > "$OUT/traceability.mmd"

# ---- 2. Structure: composition + variation ----------------------------------------------------------
# Specialize edges capture the variant backends (OpenSslSha256 :> Sha256Backend, etc.).
{
  echo "flowchart TD"
  echo "  classDef def fill:#eaf2f8,stroke:#2980b9,color:#1b4f72;"
  q --rel specialize --source-kind part_definition | sed -E 's/ -> Specialize -> /\t/; s/ \(.*$//' \
    | while IFS=$'\t' read -r subq superq; do
        sub="$(echo "$subq" | short)"; sup="$(echo "$superq" | short)"
        echo "  $(nid "$sup")([\"$sup\"]):::def --> $(nid "$sub")([\"$sub\"]):::def"
      done
} | awk '!seen[$0]++' > "$OUT/structure-variants.mmd"

# ---- 3. GitHub-renderable markdown (graphical view with zero local tooling) -------------------------
# GitHub, GitLab, and VS Code render ```mermaid fenced blocks as diagrams inline, so this file IS the
# human-facing graphical view of the model — open it in the repo and the diagrams draw themselves.
{
  echo "# nanos3reader — model diagrams"
  echo
  echo "_Generated from the SysML knowledge graph by \`.nomograph/scripts/diagrams.sh\`. Do not hand-edit._"
  echo
  echo "## Requirements traceability"
  echo "Blue = component, green requirement = verified by a test, amber requirement = satisfied but not yet verified."
  echo
  echo '```mermaid'
  cat "$OUT/traceability.mmd"
  echo '```'
  echo
  echo "## Structure — variant backends"
  echo
  echo '```mermaid'
  cat "$OUT/structure-variants.mmd"
  echo '```'
} > "$OUT/diagrams.md"

echo "{\"generated\":[\"$OUT/traceability.mmd\",\"$OUT/structure-variants.mmd\",\"$OUT/diagrams.md\"]}"
