# Installing the sysledge toolset on a dev host

This installs everything needed to **validate, index, and diagram** the SysML v2
models, plus the optional **LLM agent** features (doc → model ingestion) with
**bring-your-own-key** support for Anthropic and OpenAI.

| Component | What it does | Required? | Needs |
|---|---|---|---|
| `nomograph-sysml` | validate + index the SysML models | **yes** | Rust/`cargo` |
| `sysmldiag` (this repo) | derive Mermaid diagrams from the index | **yes** | Python ≥ 3.10 |
| `mermaid-cli` (`mmdc`) | render diagrams to SVG | optional | Node ≥ 18 |
| LLM client (`sysmldiag.llm`) | doc → SysML ingestion (Layer B) | optional | an API key |

The diagram generator and the LLM client have **no third-party Python
dependencies** (stdlib only) — the only compiled/heavy pieces are the Rust CLI
and (optionally) Node for SVG.

---

## 1. Quick start (automated)

From the repo root:

```bash
bash scripts/install.sh
```

It uses **[uv](https://docs.astral.sh/uv/)** automatically when it's on PATH
(falling back to plain pip otherwise). Idempotent and re-runnable. Useful flags:

```bash
bash scripts/install.sh --uv         # force uv (default when uv is installed)
bash scripts/install.sh --pip        # force plain pip instead of uv
bash scripts/install.sh --no-rust    # nomograph-sysml already installed
bash scripts/install.sh --no-svg     # skip mermaid-cli (use .mmd / GitHub rendering)
bash scripts/install.sh --no-pip     # don't install the package; use PYTHONPATH instead
bash scripts/install.sh --check-llm  # also ping the configured LLM provider
```

The script installs each component, then verifies by running the test suite,
validating the models, building the index, and generating the diagrams.

---

## 2. Manual installation

### 2a. nomograph-sysml (required)

Needs the Rust toolchain. If you don't have `cargo`, install rustup from
<https://rustup.rs>, then:

```bash
cargo install sysml-cli      # provides the `nomograph-sysml` binary
nomograph-sysml --version
```

### 2b. sysmldiag (required)

Install it as a package to get the `sysmldiag` / `sysmldiag-llm` console scripts.
**uv is the recommended installer.** On a shared dev host without root, use one of
the user-space options (do **not** use `--system`, which writes to `/usr` and needs
root):

```bash
# uv — install the CLIs into ~/.local/bin (no root, no venv to activate). Recommended.
uv tool install --editable .
uv tool update-shell          # one-time: ensure ~/.local/bin is on PATH
sysmldiag --help

# uv — or into an explicit project venv
uv venv && source .venv/bin/activate
uv pip install -e .

# uv — or just run from the project venv without installing globally
uv run sysmldiag --help       # auto-creates .venv and installs the project

# uv — system interpreter (CI / containers where you own /usr or are root)
uv pip install --system -e .
```

Plain pip works too (fallback):

```bash
python3 -m pip install --user -e .                   # user site (~/.local), no root
# or, inside a venv:
python3 -m venv .venv && source .venv/bin/activate && python3 -m pip install -e .
```

Or run with no install at all, straight from the source tree:

```bash
PYTHONPATH=tools python3 -m sysmldiag --help
```

### 2c. mermaid-cli (optional — for SVG)

```bash
npm install -g @mermaid-js/mermaid-cli   # provides `mmdc`
```

`mmdc` uses headless Chromium (via Puppeteer). In containers/CI it needs
`--no-sandbox`; the repo ships `tools/sysmldiag/puppeteer.json` with that flag and
`sysmldiag` passes it automatically. Override with
`SYSMLDIAG_PUPPETEER_CONFIG=/path/to/config.json` if needed.

Without `mmdc` everything still works — you get the `.mmd` files and a
`diagrams.md` that GitHub/GitLab/VS Code render inline with zero tooling.

---

## 3. Document ingestion (multi-doc, PDF, Word)

The Layer B ingestion eval converts architecture docs to SysML. It accepts any mix
of formats and multiple files in one run.

| Format | Extension | Extra install needed |
|---|---|---|
| Markdown, plain text, reStructuredText, AsciiDoc | `.md` `.txt` `.rst` `.adoc` | none (stdlib) |
| PDF | `.pdf` | `sysmldiag[pdf]` → installs `pypdf` |
| Word | `.docx` | `sysmldiag[docx]` → installs `python-docx` |

Install the extras you need alongside the base package:

```bash
# uv (recommended)
uv tool install --editable '.[pdf,docx]'    # or: '.[ingest]' for both at once

# pip
pip install -e '.[pdf,docx]'
```

Run with multiple docs (they are concatenated with per-file provenance headers
before being sent to the LLM):

```bash
PYTHONPATH=tools python3 -m sysmldiag.ingest_eval.eval \
    --doc overview.md \
    --doc architecture.pdf \
    --doc details.docx \
    --system MySystem
```

Each `--doc` file's filename appears in the LLM prompt as a `### Source:` header
so the model can attribute facts to distinct sources in `@Provenance`.

---

## 4. LLM / agent setup (bring your own key)

Only the **optional** Layer B ingestion eval (`sysmldiag.ingest_eval`) uses an
LLM. It speaks to **Anthropic** or **OpenAI** (or any OpenAI-compatible endpoint,
e.g. Azure OpenAI or a local Gemma/vLLM server). Keys are read from the
environment — nothing is stored or hard-coded.

### Environment variables

| Variable | Meaning | Default |
|---|---|---|
| `SYSMLDIAG_LLM_PROVIDER` | `anthropic` or `openai` | `anthropic` |
| `SYSMLDIAG_LLM_MODEL` | model id | provider default (small/cheap) |
| `SYSMLDIAG_LLM_BASE_URL` | override API base URL | provider default |
| `SYSMLDIAG_LLM_API_KEY` | key override (any provider) | — |
| `ANTHROPIC_API_KEY` | key when provider = anthropic | — |
| `OPENAI_API_KEY` | key when provider = openai | — |

Default models (kept small/cheap by policy): Anthropic `claude-haiku-4-5-20251001`,
OpenAI `gpt-4o-mini`.

### Examples

**Anthropic (default provider):**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
sysmldiag-llm --check          # pings the provider; prints OK / FAIL
```

**OpenAI:**
```bash
export SYSMLDIAG_LLM_PROVIDER=openai
export OPENAI_API_KEY="sk-..."
sysmldiag-llm --check
```

**Local / OpenAI-compatible (e.g. a Gemma server):**
```bash
export SYSMLDIAG_LLM_PROVIDER=openai
export SYSMLDIAG_LLM_BASE_URL="http://localhost:8000/v1"
export SYSMLDIAG_LLM_MODEL="gemma-2-9b-it"
export OPENAI_API_KEY="none"    # most local servers ignore the key
sysmldiag-llm --check
```

Inspect the resolved config (key redacted) any time:
```bash
sysmldiag-llm --show
```

### Run the ingestion eval

Convert an architecture document → SysML → diagrams, asserting the model is rich
and every view renders:

```bash
PYTHONPATH=tools python3 -m sysmldiag.ingest_eval.eval \
    --doc tools/sysmldiag/ingest_eval/medhead/source.md --system MedHead
# exit 0 = pass, 3 = no LLM configured (skipped), 1 = failure
```

---

## 5. Verify the install

```bash
# deterministic renderer tests (no LLM, no network)
PYTHONPATH=tools python3 -m unittest discover -s tools/sysmldiag/tests -p 'test_*.py' -t tools

# models validate, index builds, diagrams generate
nomograph-sysml validate lib/*.sysml models/nanos3reader/*.sysml
nomograph-sysml index lib models --output .nomograph/index.json
bash .nomograph/scripts/diagrams.sh
# -> open reports/diagrams/diagrams.md
```

---

## 6. Everyday usage

```bash
sysmldiag --views all --format both        # all diagrams + SVG (if mmdc present)
sysmldiag --views bdd,requirements         # just some aspects
bash .nomograph/scripts/diagrams.sh        # convenience wrapper
```

See `docs/diagrams.md` for the view catalogue and `tools/sysmldiag/README.md` for
internals and testing.

---

## 7. Troubleshooting

- **`Permission denied … /usr/local/lib/python3.x/dist-packages`** (or `/usr/...`)
  — an install tried to write to the system interpreter without root. On a shared
  host use a user-space install: `uv tool install --editable .` (uv) or
  `python3 -m pip install --user -e .` (pip). `scripts/install.sh` now does this
  automatically when no venv is active and you're not root. Avoid `uv pip install
  --system` unless you own `/usr`.
- **`sysmldiag: command not found`** after a user-space install — `~/.local/bin`
  isn't on PATH. Run `uv tool update-shell` (uv) and restart the shell, or add it:
  `export PATH="$HOME/.local/bin:$PATH"`. You can always fall back to
  `PYTHONPATH=tools python3 -m sysmldiag …`.
- **`cargo: command not found`** — install Rust from <https://rustup.rs>, restart
  the shell, re-run.
- **`mmdc` fails to launch Chromium** — container/sandbox issue; the bundled
  `puppeteer.json` (`--no-sandbox`) is applied automatically. If you still hit it,
  set `SYSMLDIAG_PUPPETEER_CONFIG` to a config with the right args, or use
  `--no-svg` / Mermaid sources.
- **LLM `--check` says "no API key"** — the key env var for the selected provider
  isn't set in this shell. Confirm with `sysmldiag-llm --show`.
- **Permission errors from `npm install -g`** — prefix with `sudo`, or use a Node
  version manager (nvm) so global installs land in your home dir.
