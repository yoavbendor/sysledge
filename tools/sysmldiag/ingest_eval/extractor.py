"""Pluggable, dependency-light LLM backend for doc -> SysML extraction.

Policy: the extractor uses a *small, cheap* model. Defaults:
  provider = anthropic
  model    = claude-haiku-4-5-20251001

To run against a local open model (e.g. a Gemma server exposing an
OpenAI-compatible API), set:
  SYSMLDIAG_LLM_PROVIDER=openai
  SYSMLDIAG_LLM_BASE_URL=http://localhost:8000/v1
  SYSMLDIAG_LLM_MODEL=<your-local-model>
  OPENAI_API_KEY=<token-or-"none">

Only stdlib `urllib` is used so the eval has no third-party install footprint.
"""

from __future__ import annotations

import json
import os
import urllib.request

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM = """You convert architecture documentation into a SysML v2 textual model.
Rules:
- Emit ONLY SysML v2 source, no prose, no markdown fences.
- Wrap everything in a single `package` named after the system.
- Use part def / part / requirement def / action def / port / connect as appropriate.
- Every fact MUST carry an `@Provenance { source = "<ref>"; maturity = "concept"; }`
  because this is extracted, unverified information.
- Prefer reusing primitive types String/Integer/Boolean/Real.
- Keep names PascalCase for definitions, camelCase for usages."""


class LLMError(RuntimeError):
    pass


def _prompt(doc_text: str, system_name: str) -> str:
    return (
        f"System name: {system_name}\n\n"
        f"Documentation:\n'''\n{doc_text}\n'''\n\n"
        "Produce the SysML v2 model now."
    )


def _anthropic(model: str, user: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise LLMError("ANTHROPIC_API_KEY not set")
    base = os.environ.get("SYSMLDIAG_LLM_BASE_URL", "https://api.anthropic.com")
    body = json.dumps(
        {
            "model": model,
            "max_tokens": 4096,
            "system": _SYSTEM,
            "messages": [{"role": "user", "content": user}],
        }
    ).encode()
    req = urllib.request.Request(
        f"{base}/v1/messages",
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    return "".join(b.get("text", "") for b in data.get("content", []))


def _openai_compatible(model: str, user: str) -> str:
    base = os.environ.get("SYSMLDIAG_LLM_BASE_URL")
    if not base:
        raise LLMError("SYSMLDIAG_LLM_BASE_URL required for openai provider")
    key = os.environ.get("OPENAI_API_KEY", "none")
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        }
    ).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={"authorization": f"Bearer {key}", "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"]


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip() + "\n"


def extract_sysml(doc_text: str, system_name: str, model: str | None = None) -> str:
    """Return SysML v2 source extracted from `doc_text`. Raises LLMError on
    misconfiguration so the eval can skip cleanly."""
    provider = os.environ.get("SYSMLDIAG_LLM_PROVIDER", "anthropic").lower()
    model = model or os.environ.get("SYSMLDIAG_LLM_MODEL", DEFAULT_MODEL)
    user = _prompt(doc_text, system_name)
    if provider == "anthropic":
        return _strip_fences(_anthropic(model, user))
    if provider == "openai":
        return _strip_fences(_openai_compatible(model, user))
    raise LLMError(f"unknown provider: {provider}")
