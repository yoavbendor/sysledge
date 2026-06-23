# Maintenance log

Append-only record of every ingest / fix / refactor against the knowledge base. Newest last.

---

## 2026-06-22 — Ingest: nanos3reader (pilot)

**Verb:** Ingest (first model). **Source:** `nanos3reader@ff28f0b` (see `raw/nanos3reader/manifest.yaml`).

Built the first system model end-to-end as the pilot for Domain 2:

- `lib/concepts.sysml` — `Provenance` metadata def + reusable `ByteRangeReadStream` / credential interfaces.
- `lib/scalar_values.sysml` — minimal stdlib stub so primitive types don't dangle in the index.
- `models/nanos3reader/` — requirements (15), structure (parts + crypto/TLS variation points),
  behavior (resolve-credentials, build-authorization, load-window, seek, open), verification (3 cases),
  allocation (15 satisfy links). Every fact carries `@Provenance` into the source above.

**Validation:** all files `valid: true`. Index: 127 elements / 224 relationships.
`check`: OrphanRequirements 0, MissingVerification 0.

**Honest gaps recorded (not hidden):** 9 requirements are satisfied but have **no automated verification**
in the repo — KeepAlivePerObject, CredentialChain, RefreshTemporaryCredentials,
SelfExplainingCredentialFailure, WrongRegionRedirect, RetryWithBackoff, MinimalDependencies,
SmallStaticBuild, ReadOnlyByDesign. This reflects the actual test suite (SigV4 known-answer + MinIO
integration + crypto-backend parity only). See `reports/traceability-matrix.md` (15/15 satisfied,
6/15 verified). Remaining `check` notes are tool-opinion on external boundary ports / port defs.

**Decisions applied:** monorepo (more GitLab systems to follow); raw stored as a git-revision manifest
(S3 deferred); `satisfy`/`verify` target requirement definitions (nomograph is definition-centric).

---

## 2026-06-23 — Widen: graphical rendering

**Verb:** Widen (presentation). Added on-demand graphical views of the models for humans:

- `.nomograph/scripts/diagrams.sh` derives **Mermaid** diagrams from the knowledge graph
  (satisfy/verify/specialize) → `reports/diagrams/{traceability,structure-variants}.mmd` and a
  GitHub-renderable `diagrams.md`. Traceability nodes are coloured green=verified / amber=unverified.
- Also generated nomograph's own outputs: `reports/traceability-matrix.html` and `reports/health-badge.svg`.

nomograph's native `render` is tabular (markdown/html/csv) + an SVG badge; box-and-arrow diagrams come
from the Mermaid derivation. Documented as a standard operation in docs/conventions.md.

---

## 2026-06-23 — Refactor/Widen: `sysmldiag` diagram component

**Verb:** Refactor (presentation tooling) + Widen (new aspects). Replaced the 88-line bash/sed
`diagrams.sh` (2 diagrams) with **`tools/sysmldiag`**, a deterministic SysML v2 → Mermaid generator
that reads `.nomograph/index.json`. **No LLM is in the rendering path** — diagrams are fully derived
from the index, so they are golden-testable and faithful (never guessed).

**Views (6), one per SysML aspect:** `requirements` (satisfy/verify, coloured verified/partial/orphan),
`bdd` (classDiagram: attributes, specialization, composition, ports), `ibd` (ports + connections),
`behavior` (action decomposition + parameters), `package_map` (layer-coloured model browser),
`allocation` (RFLP cross-layer overview). Output: `reports/diagrams/*.mmd` + GitHub-native
`diagrams.md` (renders inline) + `manifest.json`; each diagram links nodes back to `file:line`.

**Gaps surfaced on purpose:** views report unverified/orphan requirements, how little interconnection
is modeled (1 `Connect`), and that action succession/flow is not yet captured — i.e. the diagrams
double as a to-do list for the next ingest pass.

**Testing.** Layer A (deterministic CI gate, no LLM/network): golden-file + structural-lint + edge-case
tests — `PYTHONPATH=tools python3 -m unittest sysmldiag.tests.test_sysmldiag` (11 tests, green).
Layer B (optional): `tools/sysmldiag/ingest_eval/` converts an architecture document → SysML → diagrams
and asserts structural richness, proving the pipeline scales. The extractor uses a **small/cheap** model
by policy (default `claude-haiku-4-5-20251001`; pluggable to a local OpenAI-compatible Gemma endpoint),
and is never part of the CI gate. Fixture: a paraphrased MedHead architecture brief
(`ingest_eval/medhead/source.md`) — test-only, `maturity = "concept"`, kept out of the nano* models.

**Carried over (superseded files):** the old `reports/diagrams/{traceability,structure-variants}.mmd`
are replaced by the new view set; `diagrams.sh` is now a thin wrapper over `python3 -m sysmldiag`.
Tier-A authentic-notation rendering (PlantUML SysML profile / SysML kernel) documented as a future,
optional renderer in `docs/diagrams.md`.
