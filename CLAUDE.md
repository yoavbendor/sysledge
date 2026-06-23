# sysledge — agent operating guide

This repo is the **knowledge base** for a family of systems, expressed as SysML v2 models (not wikis) so
AI agents can give advice grounded in **facts and plans, not guesses**. It follows
[Karpathy's LLM-wiki method](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) with the
markdown wiki replaced by SysML v2 and the linter replaced by the `nomograph-sysml` validator.

Read these first: `docs/domain-2-plan.md` (the plan), `docs/conventions.md` (the modeling rules),
`SKILL.md` (the nomograph CLI reference). The current pilot system is `nanos3reader`; more systems
(nanotins, nanolance, nanoarrow2parquet, then HW/embedded) will be added under `models/`.

## The three layers (and where to write)

- `raw/<system>/` — **immutable** source registry. Never edit a fact's source; add new sources.
- `models/` + `lib/` — the SysML v2 source of truth. This is the "wiki" you maintain.
- `docs/` + `CLAUDE.md` — the schema/rules. Change deliberately.

## Tooling

`nomograph-sysml` (Rust CLI + MCP server: run `nomograph-sysml --mcp`). Validate/query/render the models;
never hand-assert what you can derive from the index. Key commands — full list in `SKILL.md`:

```
nomograph-sysml validate <files>                 # syntax gate (must be valid:true)
nomograph-sysml index lib models --output .nomograph/index.json
nomograph-sysml search "<text>" | trace <el> | inspect <el> | query --rel satisfy
nomograph-sysml check all --detail               # completeness/lint
nomograph-sysml render --template traceability-matrix   # tables: markdown|html|csv
nomograph-sysml stat                             # health dashboard (--badge for SVG)
bash .nomograph/scripts/diagrams.sh              # Mermaid diagrams -> reports/diagrams/ (graphical view)
```

## The maintenance loop (Domain 2)

Every change is one of these verbs; each ends at the "done" gate in `docs/conventions.md`:

- **Ingest/Augment** — register a raw source under `raw/<system>/`, extract SysML fragments **with
  `@Provenance`**, reconcile against existing models (reuse `lib/`, don't duplicate), validate, log.
- **Validate/Lint** — `validate` + `check all`; fix real findings, document honest gaps.
- **Fix** — correct a fact that a newer source supersedes; record the supersession in `log.md`.
- **Widen** — model an aspect not yet covered.
- **Develop** — add planned elements as `maturity = "concept"`, clearly separated from implemented facts.
- **Refactor** — promote duplicates into `lib/`, convert copy-paste into variation points; validate that
  meaning is preserved.

## Hard guardrails

1. **No fact without provenance.** Unsourced ⇒ `maturity = "concept"` (hypothesis), never "implemented".
2. **Never silently overwrite a sourced fact.** Supersede with a logged reason.
3. **Never commit SysML that fails `validate`.** It is a hard gate (CI + `.nomograph/scripts/validate-model.sh`).
4. **Surface contradictions and unverified requirements; don't hide them.** Honest gaps are the point.
5. **Reuse before redefine.** Check `lib/` first.

## Where things are

- Pilot model: `models/nanos3reader/{requirements,structure,behavior,verification,allocation}.sysml`
- Shared vocabulary: `lib/concepts.sysml` (Provenance, reusable interfaces), `lib/scalar_values.sysml`
- Generated, do not hand-edit: `reports/`
- Change history: `log.md` (append-only)
