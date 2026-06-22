#!/usr/bin/env bash
set -euo pipefail

ELEMENT="${1:?Usage: impact.sh <element> [hops] [index-path]}"
HOPS="${2:-3}"
INDEX_PATH="${3:-.nomograph/index.json}"

nomograph-sysml trace "$ELEMENT" --index "$INDEX_PATH" --hops "$HOPS" --direction both --trace-format flat
