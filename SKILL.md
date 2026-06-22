# nomograph-sysml (v0.1.0)

SysML v2 knowledge graph toolkit. Parse, index, search, analyze, and render SysML v2 models.
Also available as MCP server via `nomograph-sysml --mcp`.

## Available Commands

| Command | Purpose | Example |
|---------|---------|---------|
| parse | Parse SysML files to AST | `nomograph-sysml parse *.sysml --level l1` |
| validate | Check files for errors | `nomograph-sysml validate model.sysml` |
| index | Build knowledge graph | `nomograph-sysml index ./model/` |
| search | Search by name/kind/text | `nomograph-sysml search "requirement" --kind requirement_definition` |
| trace | Follow relationships | `nomograph-sysml trace ShieldModule --hops 3 --direction both` |
| check | Structural + metamodel checks | `nomograph-sysml check all` or `check metamodel-conformance` |
| query | Predicate relationship search | `nomograph-sysml query --rel satisfy --source-name "shield"` |
| render | Template-based reports | `nomograph-sysml render --template traceability-matrix` |
| stat | Model health dashboard | `nomograph-sysml stat` |
| plan | Decompose question into commands | `nomograph-sysml plan "Does X satisfy Y?"` |
| skill | Agent skill file | `nomograph-sysml skill` |

## Typical Workflow

1. `nomograph-sysml index ./model/` — build knowledge graph
2. `nomograph-sysml search "<what you need>"` — find relevant elements
3. `nomograph-sysml trace <element> --hops 3` — follow impact chains
4. `nomograph-sysml check all` — find structural + metamodel gaps
5. `nomograph-sysml render --template completeness-report` — generate report

## Key Options

- `check --detail` — full findings instead of summary counts
- `trace --max-results N` — limit output for token efficiency
- `query --compact` — one-line per relationship
- `render --render-format html|csv` — alternate output formats
- `render --custom path.hbs` — custom Handlebars template
- `search --layer R|F|L|P` — filter by RFLP architecture layer
- `query --source-layer R --target-layer P` — cross-layer relationship queries
- `plan --execute` — run decomposed plan and aggregate results

## Output

All commands output JSON by default. `render` outputs markdown/html/csv.
Pipe between commands: `nomograph-sysml search "port" | jq '.[].qualified_name'`

## Help

Run `nomograph-sysml <command> --help` for detailed options.
