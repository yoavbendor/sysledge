# MedHead — captured ingestion example (snapshot, not a golden)

This directory is a **checked-in showcase** of the Layer B pipeline:
an architecture document → SysML model (extracted by an LLM) → diagrams. It lets
a human see "doc → diagram" working **without running an LLM**.

## What's here

- `medhead.sysml` — the SysML v2 model **extracted from `../source.md`** by a
  small model (Claude Haiku 4.5) following the project's dialect. It validates
  (`nomograph-sysml validate`) and everything is `maturity = "concept"`.
- `diagrams/` — the six views generated deterministically from that model by
  `sysmldiag`, plus rendered `svg/`. Open `diagrams/diagrams.md`.

## Important: this is a snapshot, not a test oracle

LLM extraction is **non-deterministic**, so these files are *one captured run*,
not a golden the CI gate compares against. Re-running the eval will produce a
similar-but-different model. The deterministic guarantees live elsewhere:

- `sysmldiag` rendering is deterministic and golden-tested in `../../tests/`.
- The Layer B eval (`../eval.py`) asserts **structural properties** (validates,
  ≥4 parts, ≥3 requirements, all views render + lint), not exact text.

## Why MedHead is here at all

It is a **test fixture only** — an original paraphrase of a public architecture
document (see `../source.md` for provenance) used to exercise the diagrams on
richer input than the nanos3reader pilot. It is deliberately **not** part of the
nano* knowledge base under `models/`.

## What this run demonstrated

Indexed to 99 elements: **16 part definitions, 9 connections, 5 requirements**.
The 9-edge event-bus fan-in populates the **IBD/interconnection** view — the
aspect that is thin/empty for the pilot — confirming the views scale with data.

## Reproduce

```
# with a small model configured (Haiku by default, or a local Gemma endpoint):
PYTHONPATH=tools python3 -m sysmldiag.ingest_eval.eval \
    --doc tools/sysmldiag/ingest_eval/medhead/source.md --system MedHead

# regenerate these diagrams from the captured model:
nomograph-sysml index lib tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml \
    --output /tmp/medhead.json
PYTHONPATH=tools python3 -m sysmldiag --index /tmp/medhead.json \
    --out tools/sysmldiag/ingest_eval/medhead/expected/diagrams --title MedHead --format both
```
