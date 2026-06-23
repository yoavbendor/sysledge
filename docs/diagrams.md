# Diagrams — graphical views of the models

Diagrams are a primary way humans browse, validate, and find gaps in the models.
They are generated **deterministically from the nomograph knowledge graph** by the
`sysmldiag` component (`tools/sysmldiag/`) — **no LLM is in the rendering path**, so a
diagram is a faithful picture of `index.json`, never a guess. Output renders inline on
GitHub/GitLab/VS Code with zero tooling.

## Generate

```
bash .nomograph/scripts/diagrams.sh           # uses .nomograph/index.json -> reports/diagrams/
# or directly:
PYTHONPATH=tools python3 -m sysmldiag --out reports/diagrams --views all --format both
```

Open **`reports/diagrams/diagrams.md`** — the fenced ```mermaid blocks draw themselves.
Each diagram is followed by a collapsible table mapping every node to its `file:line`
source, so you can jump from picture to model.

## The view catalogue (SysML aspect → Mermaid)

| View (`slug`) | SysML aspect | Source in index | Mermaid type |
|---|---|---|---|
| `requirements` | Requirements traceability | `requirement_definition` + `Satisfy`/`Verify` | flowchart (verified/partial/orphan colouring) |
| `bdd` | Block definitions | `part_definition`, `attribute`+`TypedBy`, `Specialize`, ports | classDiagram (inheritance + composition) |
| `ibd` | Internal connections | `part_usage`, `port_usage`, `Connect` | flowchart |
| `behavior` | Behavior / actions | `action_definition/usage`, `parameter_usage`, `Member` | flowchart |
| `package_map` | Model map / browser | `package_definition` + `Member` | flowchart (layer-coloured) |
| `allocation` | Allocation / RFLP overview | `layer` + cross-layer `Satisfy` | flowchart (R ↔ L/P) |

Mermaid's native types map onto SysML aspects well enough to cover most of the diagram
taxonomy without the official toolchain; the mapping above is the rule set.

## Diagrams surface gaps on purpose

Honest gaps are the point of this knowledge base, so views report what is **missing**,
not just what exists:

- `requirements` colours satisfied-but-unverified requirements amber and orphans grey,
  and notes the counts.
- `ibd` reports how few connections are modeled relative to declared ports.
- `behavior` flags that succession/flow ordering is not yet captured.

A thin, honest diagram is a to-do list for the next ingest pass.

## Testing

Two layers (see `tools/sysmldiag/README.md`):

- **Layer A (deterministic, the CI gate, no LLM, no network):** golden-file + structural
  lint tests. Run:
  `PYTHONPATH=tools python3 -m unittest sysmldiag.tests.test_sysmldiag`.
  Regenerate goldens after an intentional change with `--update-golden`.
- **Layer B (optional ingestion eval, LLM):** converts an architecture document to a
  SysML model and asserts the views scale (richness + lint), proving the
  doc→model→diagram pipeline. The model is small/cheap by policy —
  default `claude-haiku-4-5-20251001`, swappable to a local Gemma-style endpoint.
  Never part of the CI gate.

## Optional raster export

If [`@mermaid-js/mermaid-cli`](https://github.com/mermaid-js/mermaid-cli) (`mmdc`) is
installed, `--format both` also writes `reports/diagrams/svg/*.svg`. Without it the step
is skipped and the `.mmd`/markdown sources remain the deliverable.

## Future: authentic SysML notation (Tier A)

For officially-notated SysML diagrams (true BDD/IBD glyphs) the upgrade path is a
heavier renderer — e.g. PlantUML with a SysML v2 macro profile, or driving the official
SysML Jupyter kernel (windseeker-style) / SysOn. These need Java/Jupyter/Docker, so they
are deliberately **out of scope** for the zero-install, CI-gated workflow here and would
be added as a separate, optional renderer that consumes the same `index.json`.
