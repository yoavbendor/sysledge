"""Doc -> SysML extraction, built on the provider-agnostic LLM client.

Works with Anthropic or OpenAI (or any OpenAI-compatible endpoint) and
bring-your-own-key — see `sysmldiag.llm` for configuration. By policy the
default model is small/cheap (Anthropic Haiku 4.5; OpenAI gpt-4o-mini).
"""

from __future__ import annotations

from ..llm import LLMConfig, LLMError, complete

__all__ = ["extract_sysml", "LLMError"]

_SYSTEM = """You convert architecture documentation into a SysML v2 textual model.
Rules:
- Emit ONLY SysML v2 source, no prose, no markdown fences.
- Wrap everything in a single `package` named after the system.
- Use part def / part / requirement def / action def / port / connect as appropriate.
- Every fact MUST carry an `@Provenance { source = "<ref>"; maturity = "concept"; }`
  because this is extracted, unverified information.
- Prefer reusing primitive types String/Integer/Boolean/Real.
- Keep names PascalCase for definitions, camelCase for usages."""


def _prompt(doc_text: str, system_name: str) -> str:
    return (
        f"System name: {system_name}\n\n"
        f"Documentation:\n'''\n{doc_text}\n'''\n\n"
        "Produce the SysML v2 model now."
    )


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip() + "\n"


def extract_sysml(
    doc_text: str, system_name: str, cfg: LLMConfig | None = None
) -> str:
    """Return SysML v2 source extracted from `doc_text`. Raises LLMError if the
    LLM is not configured (missing key / unknown provider), so callers can skip."""
    cfg = cfg or LLMConfig.from_env()
    raw = complete(_SYSTEM, _prompt(doc_text, system_name), cfg)
    return _strip_fences(raw)
