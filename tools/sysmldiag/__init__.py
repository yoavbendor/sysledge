"""sysmldiag — deterministic SysML v2 -> Mermaid diagram generator.

Reads the nomograph knowledge graph (`.nomograph/index.json`) and emits one
Mermaid diagram per SysML aspect (requirements, BDD, IBD, behavior, model map,
allocation). No LLM is used anywhere in the rendering path; output is fully
determined by the index, so it is golden-testable.
"""

__version__ = "0.1.0"
