#!/usr/bin/env bash
set -euo pipefail

MODEL_DIR="${1:-.}"
ERRORS=0

for f in $(find "$MODEL_DIR" -name '*.sysml' -type f); do
    RESULT=$(nomograph-sysml validate "$f" 2>/dev/null)
    VALID=$(echo "$RESULT" | jq -r '.valid')
    if [ "$VALID" != "true" ]; then
        echo "INVALID: $f" >&2
        echo "$RESULT" | jq '.diagnostics[]' >&2
        ERRORS=$((ERRORS + 1))
    fi
done

if [ "$ERRORS" -eq 0 ]; then
    echo '{"valid":true,"files_checked":"all"}' 
else
    echo "{\"valid\":false,\"errors\":$ERRORS}" 
    exit 1
fi
