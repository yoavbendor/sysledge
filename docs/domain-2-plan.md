# Domain 2 — Building & Maintaining the System Models

*The SysML v2 knowledge base for a "second brain" your AI agents can reason over.*

## 0. Goal

Give AI agents a **single source of truth** about each system so their advice is
grounded in **facts and plans, not guesses**. The knowledge base is a set of
**SysML v2 textual models** in git: human-readable, diffable, machine-validatable,
and able to represent every aspect of a system (requirements, structure,
interfaces, behavior, hardware, configuration, verification, and the trace links
between them).

Two domains were identified. This plan covers **Domain 2: producing and keeping
the models correct, complete, and reusable** — i.e. *validating, augmenting,
fixing, widening, developing, and refactoring* the models. Domain 1 (agents
*consuming* the models to advise) is a separate plan and is only referenced here
where it sets requirements on Domain 2.

## 1. The core idea: Karpathy's "second brain", with SysML as the wiki

We adopt [Karpathy's LLM-wiki method](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
but swap the markdown wiki for SysML v2 models and the markdown linter for a real
model validator.

| Karpathy layer            | Our equivalent                                                        |
|---------------------------|-----------------------------------------------------------------------|
| Raw Sources (immutable)   | `raw/` — word/pdf/html/excel/xml/json/text/markdown, never edited      |
| Wiki (LLM-maintained)     | `models/` — SysML v2 `.sysml` packages, the source of truth            |
| Schema / `CLAUDE.md`      | `CLAUDE.md` + `docs/conventions.md` — the modeling ontology & rules    |
| `index.md`                | `models/index.sysml` (+ generated catalog) — entry point for retrieval |
| `log.md`                  | `log.md` — append-only record of every ingest / fix / refactor         |
| Ingest / Query / Lint     | Ingest / Query / **Validate** (nomograph) — see §5                      |

Karpathy's insight applies directly: *the hard part of a knowledge base is the
bookkeeping, not the thinking* — and that is exactly what agents are good at.
Humans curate sources and ask good questions; agents do the extraction,
cross-linking, deduplication, and consistency maintenance.

## 2. Tooling: [nomograph/sysml](https://gitlab.com/nomograph/sysml)

A Rust CLI + **MCP server** that lets AI *query, validate, and render* SysML v2.
It is the spine of Domain 2:

- **Validate** — every model change is machine-checked. Invalid SysML never
  merges. This is what makes "facts not guesses" enforceable.
- **Query** — agents pull precise slices of the model instead of re-reading
  everything (the retrieval half of the second brain).
- **Render** — diagrams for human review of agent-proposed changes.
- **MCP** — exposed to the editing agents *and* to Cursor/VSCode, so the same
  validated model serves both the maintenance agents (Domain 2) and the advisory
  agents/humans (Domain 1).

Setup tasks: pin a nomograph version, wire the MCP server into the agent runtime
and into Cursor/VSCode, and add a CI job that runs `validate` on every PR.

## 3. Repository architecture

`sysledge` is the knowledge-base monorepo. Proposed layout:

```
sysledge/
  CLAUDE.md                 # schema doc: how agents must model & maintain (the rules)
  log.md                    # append-only ingest/maintenance log
  docs/
    domain-2-plan.md        # this file
    conventions.md          # the modeling ontology (§4)
  raw/                      # immutable source material, by system
    <system>/<source-id>/…  # original word/pdf/xls/xml/json/etc + a sidecar .meta.yaml
  lib/                      # SHARED model libraries — the "common/variant parts" solution
    parts/                  # reusable PartDefinitions (hardware, software components)
    interfaces/             # reusable PortDefinitions / InterfaceDefinitions
    concepts/               # reusable RequirementDefinitions, ItemDefinitions, units
  models/
    index.sysml             # top-level package importing every system
    <system>/
      requirements.sysml
      structure.sysml       # parts, ports, connections
      behavior.sysml        # actions, states, sequences
      variants.sysml        # variation points & configured variants
      verification.sysml     # verification cases linked to requirements
      allocation.sysml      # logical<->physical, requirement<->part trace
  tools/                    # ingest/transform scripts, CI helpers
```

Key decisions baked in:
- **One repo, many systems** so shared libraries (`lib/`) can be reused across
  systems — directly addressing "many common or near-equal/variant parts."
- **`raw/` is immutable.** Every source gets a stable `source-id` and a
  `.meta.yaml` sidecar (origin, date, hash, system, version). This is the
  provenance anchor.
- Models are organized by **aspect** (requirements / structure / behavior / …)
  so diffs are small and reviewable.

## 4. Modeling conventions (the ontology) — `docs/conventions.md`

This is the most important deliverable: a precise, enforced mapping from "things
in the system" to SysML v2 constructs, so every agent models the same way.

**Aspect → construct mapping (starting set):**

| System aspect                 | SysML v2 construct                                  |
|-------------------------------|-----------------------------------------------------|
| Requirement / spec clause     | `requirement def` + `requirement` usage             |
| Physical / SW component       | `part def` / `part`                                 |
| Interface / connection        | `port def`, `interface def`, `connect`              |
| Behavior / process / script   | `action def`, `action`, `state def`                 |
| Config / parameter            | `attribute` (typed, with units from `lib/concepts`) |
| Data / message / artifact     | `item def` / `item`                                 |
| Logical↔physical, req↔part    | `allocation`                                        |
| Test / acceptance             | `verification case`                                 |

**Cross-cutting rules:**
- **Provenance is mandatory.** Every model element that asserts a fact carries
  metadata linking to its `source-id` (and ideally page/section). An element with
  no source is a *hypothesis*, must be tagged as such, and is a lint failure if it
  claims to be fact. This is the mechanism that keeps agents honest.
- **Reuse before redefine.** New parts/interfaces must first be searched for in
  `lib/`. Variants are modeled with **specialization/redefinition and variation
  points** (`variant`, `:>` redefinition), not copy-paste. The librarian agent
  (§6) promotes anything duplicated ≥2× into `lib/`.
- **Implementation stage is first-class.** Tag each element with its maturity
  (`concept` → `designed` → `implemented` → `verified`) so Domain 1 agents can
  distinguish "planned" from "real."
- **Naming & namespacing** conventions per system and per library.

## 5. The ingestion & maintenance pipeline

### 5a. Ingest (raw → model)
1. **Land & register** the raw file in `raw/<system>/<source-id>/` with its
   `.meta.yaml`.
2. **Normalize** to text/markdown + structure:
   - *Structured* sources (excel/xml/json) → deterministic transforms
     (`tools/`) → SysML fragments (e.g. a parts list/BOM → `part` usages, a config
     file → `attribute` values). Prefer code over LLM where the mapping is
     mechanical — it's exact and cheap.
   - *Unstructured* sources (word/pdf/html/text/markdown) → LLM extraction into
     candidate SysML fragments **with provenance** attached.
3. **Reconcile** the candidate against existing models: reuse `lib/` elements,
   attach to the right package, flag conflicts with existing facts as explicit
   review items (never silently overwrite).
4. **Validate** with nomograph; iterate until clean.
5. **Open a PR**; append a `log.md` entry.

### 5b. The six maintenance verbs, as agent operations
These are the verbs from the request, each a defined, repeatable workflow:

- **Validate** — run nomograph + custom lints (provenance present? requirements
  have verification? orphan parts? contradictions across systems?). The Karpathy
  "lint" pass, but model-aware.
- **Augment** — ingest new sources / fill modeled-but-empty stubs.
- **Fix** — correct elements that conflict with a newer authoritative source;
  record the supersession in `log.md`.
- **Widen** — extend coverage to aspects not yet modeled (e.g. add behavior to a
  system that only had structure).
- **Develop** — add forward-looking *planned* elements (maturity `concept`),
  clearly separated from implemented facts.
- **Refactor** — deduplicate into `lib/`, split variants into variation points,
  rename for convention. Pure structure change; semantics-preserving, validated.

Everything is **diff-driven**: when a raw source or the real system changes,
agents reconcile the delta rather than rebuilding.

## 6. Agents & guardrails

Specialized agent roles (can be one model with different prompts/tools):
- **Extractor** — raw → candidate SysML fragments, always with provenance.
- **Reconciler** — merges candidates, detects/flags contradictions.
- **Librarian** — owns `lib/`; promotes duplicates, manages variants.
- **Validator** — runs nomograph + lints; gatekeeps PRs.
- **Reviewer** — prepares human-readable diff + rendered diagrams for sign-off.

**Hard guardrails (encode in `CLAUDE.md`):**
1. Never assert a fact without a `source-id`. Unsourced ⇒ tag `hypothesis`.
2. Never delete/overwrite a sourced fact silently — supersede with a logged reason.
3. Never merge SysML that fails `nomograph validate`.
4. Surface contradictions as first-class review items, don't auto-resolve.

## 7. Governance / git workflow

- Branch per change → PR → CI (`nomograph validate` + lints) → human review of the
  **diff + rendered diagram** → merge. The git diff *is* the change record.
- `log.md` is the append-only narrative (what was ingested/fixed/refactored, by
  whom, against which source).

## 8. Quality metrics (track in CI)

- **Validity**: 100% of models pass nomograph (gate).
- **Traceability**: % of fact elements with provenance; % of requirements with a
  verification case.
- **Reuse / duplication ratio**: copies that should be `lib/` references (drives
  refactor work).
- **Coverage**: aspects modeled per system; maturity distribution.
- **Freshness**: sources ingested vs. landed.

## 9. Phased rollout

- **Phase 0 — Bootstrap (1 pilot).** Stand up tooling (nomograph CLI + MCP + CI),
  write `CLAUDE.md` and `docs/conventions.md`, create the repo skeleton.
  **Pilot = `nanos3reader`** — it's small, self-contained, and already well
  documented (README + tests), so we can hand-validate the model end to end.
- **Phase 1 — First model, full loop.** Ingest the pilot's README/code/tests,
  produce requirements + structure + behavior + verification models, run the six
  verbs once manually, prove the validate gate and provenance rules.
- **Phase 2 — Libraries & variants.** Bring in a second system; extract shared
  parts/interfaces/concepts into `lib/`; model the first real variants. This is
  where the "common/near-equal parts" payoff appears.
- **Phase 3 — Automate.** Run the agent roles on a schedule / on source changes;
  Domain 1 agents start consuming the validated models via the same MCP server.

## 10. Open decisions (need your input before Phase 0)

1. **Monorepo vs. per-system repos.** Plan assumes monorepo (best for shared
   libraries). Confirm?
2. **`raw/` storage.** Commit raw binaries into git, or keep them in S3 (you
   already have `nanos3reader`!) and commit only `.meta.yaml` pointers? S3 +
   pointers keeps the repo light and is a natural fit.
3. **Pilot choice.** `nanos3reader` as the first system to model — agreed, or a
   different real system you'd rather prove this on?
4. **nomograph maturity.** Confirm its `validate`/`query` cover the SysML
   constructs in §4 for our version, or whether we need a fallback validator.
