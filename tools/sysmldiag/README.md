# sysmldiag

Deterministic **SysML v2 → Mermaid** diagram generator. Reads the nomograph knowledge
graph (`.nomograph/index.json`) and emits one diagram per SysML aspect. **No LLM is used
in the rendering path** — output is fully determined by the index, so it is golden-testable.

See `docs/diagrams.md` for the view catalogue and the aspect→Mermaid mapping.

## Usage

```
PYTHONPATH=tools python3 -m sysmldiag --index .nomograph/index.json \
    --out reports/diagrams --views all --format both
```

- `--views` — `all` or a comma list: `requirements,bdd,ibd,behavior,package_map,allocation`
- `--format` — `mermaid` (default), or `svg`/`both` (attempts `mmdc`, skipped if absent)

Or just: `bash .nomograph/scripts/diagrams.sh`.

## Layout

```
graph.py        load index.json -> deterministic, sorted accessors
views/          one module per aspect: Graph -> ViewResult (pure, no I/O)
emit.py         write .mmd + diagrams.md (GitHub-native) + manifest.json
render_svg.py   optional mmdc/Kroki export; no-op when absent
lint.py         dependency-free structural Mermaid lint (CI sanity gate)
__main__.py     CLI
tests/          Layer A: golden + lint + edge-case (no LLM, no network)
ingest_eval/    Layer B: optional doc -> SysML -> diagram eval (LLM)
```

## Testing

**Layer A — deterministic (CI gate):**

```
PYTHONPATH=tools python3 -m unittest sysmldiag.tests.test_sysmldiag
# update goldens after an intentional change:
PYTHONPATH=tools python3 -m sysmldiag.tests.test_sysmldiag --update-golden
```

**Layer B — optional ingestion eval (LLM, small/cheap by policy):**

```
# default: Anthropic Haiku 4.5
ANTHROPIC_API_KEY=... PYTHONPATH=tools python3 -m sysmldiag.ingest_eval.eval \
    --doc tools/sysmldiag/ingest_eval/medhead/source.md --system MedHead

# local open model (e.g. a Gemma server with an OpenAI-compatible API):
SYSMLDIAG_LLM_PROVIDER=openai SYSMLDIAG_LLM_BASE_URL=http://localhost:8000/v1 \
SYSMLDIAG_LLM_MODEL=gemma-... PYTHONPATH=tools python3 -m sysmldiag.ingest_eval.eval \
    --doc tools/sysmldiag/ingest_eval/medhead/source.md --system MedHead
```

It extracts a SysML model from a document, validates + indexes it via `nomograph-sysml`,
runs every view, and asserts structural richness + clean lint. It asserts *properties*,
not exact text (LLM output varies), and is **never** part of the CI gate. Exit codes:
`0` pass, `3` skipped (no LLM configured), `1` failure.

The MedHead fixture under `ingest_eval/medhead/` is an original paraphrase of a public
architecture document, kept here as a **test fixture only** — it is not part of the nano*
knowledge base, and everything extracted from it is `maturity = "concept"`.
