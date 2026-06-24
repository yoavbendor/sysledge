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

---

## 2026-06-23 — Tooling: dev-host install + multi-provider LLM (BYO key)

**Verb:** Refactor/Develop (tooling). Made the toolset installable on a dev host and generalized the
optional agent LLM access to Anthropic **and** OpenAI with bring-your-own-key.

- `pyproject.toml` — `pip install -e .` exposes console scripts `sysmldiag` and `sysmldiag-llm`
  (stdlib-only; no third-party deps for either diagrams or the LLM client).
- `scripts/install.sh` — idempotent installer: nomograph-sysml (cargo), the Python package, optional
  mermaid-cli, then verifies (tests + validate + index + diagrams). Flags: `--no-rust/--no-svg/--no-pip/--check-llm`.
- `INSTALL.md` — detailed manual + automated install, LLM/agent setup, verification, troubleshooting.
- `tools/sysmldiag/llm.py` — provider-agnostic client (Anthropic + OpenAI + OpenAI-compatible/local,
  e.g. Gemma). Keys come from env only; defaults are small/cheap (Haiku 4.5 / gpt-4o-mini). `--check`/`--show`.
- `ingest_eval/extractor.py` now builds on `llm.py`; the Layer B eval reports the resolved (redacted) config.
- Tests: added `tests/test_llm.py` (offline: config resolution, BYO key, missing-key/unknown-provider errors).
  CI now runs the whole `tools/sysmldiag/tests` suite by discovery (17 tests, green).

No model facts changed; the SysML `validate` gate is untouched.

## 2026-06-23 — Tooling: prefer uv for install + CI

**Verb:** Refactor (tooling). Adopt [uv](https://docs.astral.sh/uv/) as the preferred installer.

- `scripts/install.sh` auto-detects uv (`uv pip install`, venv-aware) and falls back to pip;
  `--uv`/`--pip` force either. Verified end-to-end in-sandbox (uv 0.8.17).
- CI `renderer-tests` now uses `astral-sh/setup-uv` + `uv run`, exercising the uv install path.
- `INSTALL.md` documents `uv run` / `uv venv` / `uv pip --system`, with pip as fallback.
- `uv.lock` committed (zero third-party deps; marks the repo as a uv project for reproducible runs).

## 2026-06-23 — Fix: install without root on a shared host

**Verb:** Fix (tooling). `uv pip install --system` failed with EACCES on a shared dev host
(non-root, no venv) trying to write `/usr/local/lib/python3.10/dist-packages`.

- `scripts/install.sh`: when no venv is active, uv now uses `uv tool install --editable .`
  (installs the CLIs into `~/.local/bin`, no root); pip fallback uses `--user`. `--system`
  is used only inside an active venv or as root. Verify step now runs via `PYTHONPATH`,
  so it's independent of where the console scripts landed / PATH propagation.
- `INSTALL.md`: lead with the user-space uv flow (`uv tool install`); added a troubleshooting
  entry for the EACCES/`command not found` cases.

## 2026-06-23 — Fix: no-sudo install (npm/cargo PATH, link mode)

**Verb:** Fix (tooling). Follow-up to the user-space install fix, for a host with no sudo and
modules (cargo + nodejs) on read-only paths.

- `scripts/install.sh`: `UV_LINK_MODE=copy` (cache/target on different filesystems);
  prepend `~/.local/bin` and the cargo bin dir to PATH so verify finds freshly-installed
  tools; install mermaid-cli with `npm install -g --prefix ~/.local` (no root); print a
  PATH hint when user-space bins aren't yet on PATH.

## 2026-06-23 — Feature: multi-doc ingestion + PDF/Word format support

**Verb:** Develop (tooling). The ingestion eval now accepts multiple documents and
non-Markdown formats via optional extras.

- `tools/sysmldiag/ingest_eval/doc_reader.py` — new module: reads `.md/.txt/.rst/.adoc`
  (stdlib, always), `.pdf` (via `pypdf`, optional), `.docx` (via `python-docx`, optional).
  Multi-doc: joins with `### Source: <filename>` per-file headers so the LLM and
  `@Provenance` can attribute facts to distinct sources.
- `eval.py`: `--doc` now accepts multiple files (`action="append"`); `run()` takes
  `list[Path]`; reports doc count and combined line count.
- `pyproject.toml`: added `[pdf]`, `[docx]`, `[ingest]` optional extras; core remains
  stdlib-only (zero deps).
- `tests/test_doc_reader.py`: offline tests (mock pypdf/python-docx); covers text formats,
  multi-doc join, missing-dep errors with actionable install hints, empty PDF, mock extraction.
  Total test count: 30 (was 17).

No model facts changed; the SysML `validate` gate is untouched.

## 2026-06-24 — Develop: ingestion safety net (patch queue + apply-authority)

**Verb:** Develop (tooling). Step 1 of the crystallized ingestion plan — the safety net that
must exist before any automated edits. Stdlib-only (no pydantic/filelock/ULID).

- `tools/sysmldiag/ingest/queue.py` — `Patch` dataclass + `Queue`. `Patch.validate()` enforces
  hard guardrails in code: add/modify fragments must carry `@Provenance`; `provenance.source`
  required; `maturity ∈ {concept,designed,implemented,verified}`; `target_file` must be a
  repo-relative path under `models/`/`lib/` (no escapes). Time-sortable stdlib id; atomic
  `os.replace` writes; FIFO `incoming/applied/rejected` dirs.
- `tools/sysmldiag/ingest/authority.py` — the single writer. `apply_one` snapshots → edits
  (best-effort text transform) → validates → commits (move to applied/, append `log.md`) or
  rolls back byte-for-byte (restore snapshot, move to rejected/ with validator output). The
  validator is injectable (offline tests); the default shells to `nomograph-sysml validate`
  + `index` (catches cross-file dangling refs). `drain()` runs under an `O_EXCL` single-writer
  lock with stale-lock detection. Console script `sysledge-apply [--once] [--dry-run]`.
- Tests: `tests/test_ingest_queue.py` + `tests/test_ingest_authority.py` (23 new, offline with a
  fake validator). Suite now 53 tests, green. End-to-end smoke against real nomograph (dry-run):
  a valid patch validates+reverts, a malformed one is rejected, model file unchanged.
- `.gitignore`: ignore transient `queue/` and `.snapshots/`. `pyproject.toml`: register
  `sysledge-apply`.

No model facts changed; the SysML `validate` gate is untouched.

## 2026-06-24 — Refactor: Patch schema on pydantic (lean + pydantic)

**Verb:** Refactor (tooling). Per the "lean + pydantic" decision, migrate the ingestion
`Patch` schema from stdlib dataclasses to `pydantic.BaseModel` so machine-generated
patches (LLM → JSON, Step 2) are validated at parse time.

- `ingest/queue.py`: `Patch`/`Provenance` are pydantic models; typed `op`/`maturity`
  via `Literal`; guardrails (`@Provenance` in add/modify fragments, path-safety) run as a
  `model_validator`. `Patch.parse(dict)` surfaces every failure as a single `PatchError`.
  Rest stays stdlib (atomic writes, sortable id, FIFO dirs).
- `ingest/authority.py`: provenance access via the typed model.
- `pyproject.toml`: `dependencies = ["pydantic>=2"]` (diagrams + llm client remain
  stdlib-only). `uv.lock` updated; CI `renderer-tests` (uv run) installs it automatically.
- Tests updated; suite stays green (53 tests).
