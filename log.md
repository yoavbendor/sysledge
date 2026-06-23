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
