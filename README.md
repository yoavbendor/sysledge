# sysledge

A **second brain for engineered systems**: the knowledge base your AI agents reason
over, built from **SysML v2 models in git** instead of wikis.

Heterogeneous source material (word/pdf/html/excel/xml/json/text/markdown) is
ingested into human-readable, diffable, machine-validated **SysML v2** models, so
agents give advice grounded in **facts and plans, not guesses**.

Approach: [Karpathy's LLM-wiki method](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
with the markdown wiki replaced by SysML v2, validated/queried/rendered via
[nomograph/sysml](https://gitlab.com/nomograph/sysml) (a Rust CLI + MCP server).

Two domains:
1. **Using** the models — agents consume them to advise (separate plan).
2. **Building & maintaining** the models — see **[`docs/domain-2-plan.md`](docs/domain-2-plan.md)**.
