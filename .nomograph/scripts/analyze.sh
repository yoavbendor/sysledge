#!/usr/bin/env bash
set -euo pipefail

MODEL_DIR="${1:-.}"
INDEX_PATH="${2:-.nomograph/index.json}"

echo "=== Indexing $MODEL_DIR ===" >&2
nomograph-sysml index "$MODEL_DIR" --output "$INDEX_PATH"

echo "=== Running all checks ===" >&2
nomograph-sysml check all --index "$INDEX_PATH"
