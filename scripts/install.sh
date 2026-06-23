#!/usr/bin/env bash
#
# Installer for the sysledge toolset on a dev host. Idempotent and safe to re-run.
#
# Installs, in order:
#   1. nomograph-sysml      (Rust CLI: validate/index the SysML models)   [needs cargo]
#   2. sysmldiag            (this repo's Python package: pip install -e .) [console scripts]
#   3. mermaid-cli (mmdc)   (optional: render diagrams to SVG)            [needs npm]
# then verifies the install end-to-end.
#
# Usage:  scripts/install.sh [--no-rust] [--no-svg] [--no-pip] [--uv|--pip] [--check-llm] [-h]
#
#   --no-rust    skip installing nomograph-sysml (already present / installed elsewhere)
#   --no-svg     skip mermaid-cli (you only need the .mmd / GitHub-rendered diagrams)
#   --no-pip     don't install the package; use `PYTHONPATH=tools python3 -m sysmldiag`
#   --uv         force the uv installer (default when uv is on PATH)
#   --pip        force plain pip even if uv is available
#   --check-llm  after install, ping the configured LLM provider (needs a key set)
#   -h|--help    this help
#
set -euo pipefail

DO_RUST=1 DO_SVG=1 DO_PIP=1 DO_CHECK_LLM=0 FORCE_INSTALLER=""
for arg in "$@"; do
  case "$arg" in
    --no-rust) DO_RUST=0 ;;
    --no-svg)  DO_SVG=0 ;;
    --no-pip)  DO_PIP=0 ;;
    --uv)      FORCE_INSTALLER=uv ;;
    --pip)     FORCE_INSTALLER=pip ;;
    --check-llm) DO_CHECK_LLM=1 ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '   \033[33m!\033[0m %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# ---- 0. prerequisites ----------------------------------------------------------------
say "Checking prerequisites"
if ! have python3; then echo "python3 is required (>=3.10)." >&2; exit 1; fi
PYV="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
python3 -c 'import sys;exit(0 if sys.version_info[:2]>=(3,10) else 1)' \
  || { echo "python3 >=3.10 required, found $PYV." >&2; exit 1; }
ok "python3 $PYV"

# Choose the Python installer: uv (preferred) unless forced or absent.
INSTALLER="$FORCE_INSTALLER"
if [ -z "$INSTALLER" ]; then INSTALLER=$(have uv && echo uv || echo pip); fi
if [ "$INSTALLER" = uv ] && ! have uv; then
  warn "uv requested but not found — falling back to pip (get uv: https://docs.astral.sh/uv/)."
  INSTALLER=pip
fi
ok "python installer: $INSTALLER$( [ "$INSTALLER" = uv ] && echo " ($(uv --version))" )"

# ---- 1. nomograph-sysml --------------------------------------------------------------
if [ "$DO_RUST" -eq 1 ]; then
  say "Installing nomograph-sysml"
  if have nomograph-sysml; then
    ok "already installed ($(nomograph-sysml --version 2>/dev/null || echo present))"
  elif have cargo; then
    cargo install sysml-cli
    ok "installed nomograph-sysml via cargo"
  else
    warn "cargo not found — install Rust (https://rustup.rs) then re-run, or pass --no-rust."
    warn "nomograph-sysml is required to build the index the diagrams are derived from."
  fi
else
  say "Skipping nomograph-sysml (--no-rust)"
fi

# ---- 2. sysmldiag (Python) -----------------------------------------------------------
if [ "$DO_PIP" -eq 1 ]; then
  say "Installing the sysmldiag package (editable, via $INSTALLER)"
  if [ "$INSTALLER" = uv ]; then
    # Install into the active venv if there is one, else into the system interpreter.
    if [ -n "${VIRTUAL_ENV:-}" ]; then uv pip install -e .; else uv pip install --system -e .; fi
  else
    python3 -m pip install -e .
  fi \
    && ok "installed; console scripts: sysmldiag, sysmldiag-llm" \
    || warn "install failed; you can still run: PYTHONPATH=tools python3 -m sysmldiag"
else
  say "Skipping package install (--no-pip) — use: PYTHONPATH=tools python3 -m sysmldiag"
fi

# ---- 3. mermaid-cli (optional SVG) ---------------------------------------------------
if [ "$DO_SVG" -eq 1 ]; then
  say "Installing mermaid-cli (optional, for SVG export)"
  if have mmdc; then
    ok "already installed"
  elif have npm; then
    npm install -g @mermaid-js/mermaid-cli \
      && ok "installed mmdc" \
      || warn "npm install failed (try with sudo, or pass --no-svg). Mermaid sources still work."
  else
    warn "npm not found — SVG export skipped. Install Node 18+ for SVG, or pass --no-svg."
    warn "Without mmdc you still get .mmd + GitHub-rendered diagrams.md (zero tooling)."
  fi
else
  say "Skipping mermaid-cli (--no-svg)"
fi

# ---- 4. verify -----------------------------------------------------------------------
say "Verifying"
PYTHONPATH=tools python3 -m unittest discover -s tools/sysmldiag/tests -p 'test_*.py' -t tools \
  && ok "Layer A tests pass"

if have nomograph-sysml; then
  bash .nomograph/scripts/validate-model.sh . >/dev/null && ok "all SysML valid"
  nomograph-sysml index lib models --output .nomograph/index.json >/dev/null && ok "index built"
  if have sysmldiag; then FMT=$([ "$DO_SVG" -eq 1 ] && echo both || echo mermaid)
    sysmldiag --format "$FMT" >/dev/null && ok "diagrams generated -> reports/diagrams/"
  else
    PYTHONPATH=tools python3 -m sysmldiag >/dev/null && ok "diagrams generated -> reports/diagrams/"
  fi
else
  warn "nomograph-sysml missing — skipped index/diagram verification."
fi

if [ "$DO_CHECK_LLM" -eq 1 ]; then
  say "Checking LLM provider"
  if have sysmldiag-llm; then sysmldiag-llm --check || true
  else PYTHONPATH=tools python3 -m sysmldiag.llm --check || true; fi
fi

say "Done"
echo "  Diagrams:   open reports/diagrams/diagrams.md"
echo "  Regenerate: bash .nomograph/scripts/diagrams.sh"
echo "  LLM setup:  see INSTALL.md (Anthropic / OpenAI / local, bring-your-own-key)"
