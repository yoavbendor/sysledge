# Modeling conventions (the ontology)

The rules every agent and human follows when building/maintaining models in this repo, so models stay
**valid, uniform, and reusable**. These are tuned to the `nomograph-sysml` validator/indexer actually in
use (see `SKILL.md`); when a rule exists to satisfy the tool, that is noted.

## Repository layout

```
lib/        shared, stable vocabulary imported by every system
  scalar_values.sysml   minimal ScalarValues stub (String/Real/Integer/Boolean)*
  concepts.sysml        Provenance metadata + reusable interfaces/ports
models/
  index.sysml           top-level entry point; imports each system's packages
  <system>/
    requirements.sysml   requirement defs (the catalog of "shall" statements)
    structure.sysml      part defs, ports, interfaces, variation points
    behavior.sysml       action defs (control/data flow)
    verification.sysml    verification cases + verify links
    allocation.sysml     a system-context part with satisfy links (req -> part)
raw/<system>/           immutable source registry (manifest of what was ingested)
reports/                generated, not hand-edited (traceability matrix, etc.)
.nomograph/             validator harness + knowledge-graph index
```
\* `scalar_values.sysml` exists only because nomograph does not bundle the SysML standard library; without
it the primitive types show up as dangling references. Replace with the real stdlib import if nomograph
ships one.

## One model file per aspect

Keep requirements / structure / behavior / verification / allocation in separate files so diffs are small
and reviewable, and so an agent can pull just the slice it needs.

## Provenance is mandatory (the anti-guessing rule)

Every element that **asserts a fact about a real system** carries a `@Provenance` from `Concepts`:

```sysml
@Provenance { source = "<repo>@<commit>:<path>[#anchor]"; maturity = "implemented"; }
```

- `source` points at the exact raw material the fact was read from (registered in `raw/<system>/`).
- `maturity` is one of: `concept` → `designed` → `implemented` → `verified`.
- An element with **no provenance** is a hypothesis; it must use `maturity = "concept"` and is treated as
  a lint finding if it claims otherwise. This is what lets Domain-1 agents separate fact from guess.

## Aspect → SysML construct mapping

| System aspect                | Construct (validated dialect)                          |
|------------------------------|--------------------------------------------------------|
| Requirement / "shall"        | `requirement def <'R-n'> Name { attribute id/text; }`  |
| Component (HW or SW)         | `part def`                                              |
| Build/deploy variant         | `variation part` + `variant part` (see below)          |
| Interface / connection       | `port def`, `interface def` (`end port`), `connect`    |
| Behavior / algorithm         | `action def` with `in/out item`                         |
| Config / parameter           | typed `attribute` (`: String/Real/Integer/Boolean`)     |
| Test / acceptance            | `verification def` + `verification` usage with `verify` |
| Requirement → component      | `satisfy <RequirementDef> by <part>`                    |

## Traceability links target requirement **definitions**

nomograph's completeness checks are definition-centric. Therefore:

- `satisfy SeekableStream by factory.stream;`  — target the **def**, not a usage.
- `verify SeekableStream;`                      — target the **def**.

Mixing (satisfy a usage, verify a def) leaves both flagged as orphan/unverified. Keep both on the def.
`satisfy` links live in the system-context part in `allocation.sysml`; `verify` links live on the
verification usages in `verification.sysml`.

## Variants and reuse (the "common/near-equal parts" rule)

Search `lib/` before defining a new part/interface. Model genuine variants as variation points, not
copy-paste:

```sysml
part def Sha256Backend;
part def OpenSslSha256 :> Sha256Backend;   // ':>' = specializes
part def BundledSha256 :> Sha256Backend;

part def Reader {
    variation part crypto : Sha256Backend {
        variant part openssl : OpenSslSha256;
        variant part bundled : BundledSha256;
    }
}
```

Anything duplicated across ≥2 systems gets promoted into `lib/` by the librarian step.

## Showing models graphically (on request)

The models are graph data, so they can be drawn for humans on demand — this is a standard operation:

- **Diagrams (box-and-arrow).** `nomograph-sysml` itself renders tables and an SVG badge, **not** diagrams,
  so `.nomograph/scripts/diagrams.sh` derives **Mermaid** diagrams from the graph (satisfy / verify /
  specialize relationships) into `reports/diagrams/`:
  - `traceability.mmd` — requirements with their satisfying part and verifying test; requirement nodes are
    coloured **green = verified**, **amber = satisfied-but-unverified** (the honest gaps show up visually).
  - `structure-variants.mmd` — the variation points (crypto/TLS backends).
  - `diagrams.md` — the same diagrams in ` ```mermaid ` fences, which **GitHub / GitLab / VS Code render
    inline with no tooling**. This is the default way to show a model graphically.
- **Tables, styled.** `nomograph-sysml render --template traceability-matrix --render-format html` →
  `reports/traceability-matrix.html` (open in a browser).
- **Health badge.** `nomograph-sysml stat --badge > reports/health-badge.svg`.
- **Live / ad-hoc.** Pipe any `.mmd` to a Mermaid renderer (mermaid.live, the editor's Mermaid preview,
  or a Mermaid MCP tool) for an instant picture without committing anything.

Regenerate diagrams whenever the model changes (same trigger as `reports/`); they are generated artifacts,
never hand-edited.

## What "done" looks like for a change

1. `nomograph-sysml validate <files>` → `valid: true` for every file (hard gate).
2. `nomograph-sysml index lib models` rebuilds the graph with no **new** dangling references.
3. `nomograph-sysml check orphan-requirements missing-verification` → 0 findings.
4. `nomograph-sysml check unverified-requirements` findings are acceptable **only** when they reflect a
   real, documented absence of a test — never hidden. Record them in the change's `log.md` entry.
5. Regenerate `reports/` and append a `log.md` entry.
