"""Provider-agnostic LLM client for the (optional) agent features.

Supports **Anthropic** and **OpenAI** (and any OpenAI-compatible endpoint, e.g.
Azure OpenAI or a local Gemma/vLLM server) with **bring-your-own-key**: nothing
is hard-coded; keys come from the environment. Only stdlib `urllib` is used, so
there is no third-party install footprint.

Configuration (all optional except a key for the chosen provider):

    SYSMLDIAG_LLM_PROVIDER   anthropic | openai           (default: anthropic)
    SYSMLDIAG_LLM_MODEL      model id                     (default: per provider)
    SYSMLDIAG_LLM_BASE_URL   override API base URL         (default: per provider)
    SYSMLDIAG_LLM_API_KEY    override the key              (else provider's env var)
    ANTHROPIC_API_KEY        key when provider=anthropic
    OPENAI_API_KEY           key when provider=openai

By policy the defaults are small/cheap models. Quick check:

    PYTHONPATH=tools python3 -m sysmldiag.llm --check
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

PROVIDERS = {
    "anthropic": {
        "default_model": "claude-haiku-4-5-20251001",
        "base_url": "https://api.anthropic.com",
        "key_env": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "default_model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "key_env": "OPENAI_API_KEY",
    },
}


class LLMError(RuntimeError):
    pass


@dataclass
class LLMConfig:
    provider: str
    model: str
    base_url: str
    api_key: str
    max_tokens: int = 4096
    temperature: float = 0.0

    @classmethod
    def from_env(cls, max_tokens: int = 4096) -> "LLMConfig":
        provider = os.environ.get("SYSMLDIAG_LLM_PROVIDER", "anthropic").lower()
        if provider not in PROVIDERS:
            raise LLMError(
                f"unknown provider {provider!r}; choose one of {list(PROVIDERS)}"
            )
        spec = PROVIDERS[provider]
        key = os.environ.get("SYSMLDIAG_LLM_API_KEY") or os.environ.get(spec["key_env"])
        if not key:
            raise LLMError(
                f"no API key: set {spec['key_env']} (or SYSMLDIAG_LLM_API_KEY) "
                f"for provider {provider!r}."
            )
        return cls(
            provider=provider,
            model=os.environ.get("SYSMLDIAG_LLM_MODEL", spec["default_model"]),
            base_url=os.environ.get("SYSMLDIAG_LLM_BASE_URL", spec["base_url"]).rstrip("/"),
            api_key=key,
            max_tokens=max_tokens,
        )

    def redacted(self) -> str:
        tail = self.api_key[-4:] if len(self.api_key) >= 4 else "?"
        return (
            f"provider={self.provider} model={self.model} base_url={self.base_url} "
            f"key=…{tail}"
        )


def _post(url: str, headers: dict, payload: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise LLMError(f"HTTP {e.code} from {url}: {detail}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"cannot reach {url}: {e.reason}") from e


def complete(system: str, user: str, cfg: LLMConfig | None = None) -> str:
    """Return the model's text completion for (system, user)."""
    cfg = cfg or LLMConfig.from_env()
    if cfg.provider == "anthropic":
        data = _post(
            f"{cfg.base_url}/v1/messages",
            {
                "x-api-key": cfg.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            {
                "model": cfg.model,
                "max_tokens": cfg.max_tokens,
                "temperature": cfg.temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        return "".join(b.get("text", "") for b in data.get("content", []))
    if cfg.provider == "openai":
        data = _post(
            f"{cfg.base_url}/chat/completions",
            {
                "authorization": f"Bearer {cfg.api_key}",
                "content-type": "application/json",
            },
            {
                "model": cfg.model,
                "max_tokens": cfg.max_tokens,
                "temperature": cfg.temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        return data["choices"][0]["message"]["content"]
    raise LLMError(f"unsupported provider: {cfg.provider}")


def health_check(cfg: LLMConfig | None = None) -> tuple[bool, str]:
    """Send a tiny request to confirm the key/endpoint work. Returns (ok, detail)."""
    try:
        cfg = cfg or LLMConfig.from_env(max_tokens=8)
        cfg.max_tokens = 8
        reply = complete("You are a health check. Reply with: ok", "ping", cfg)
        return True, f"{cfg.redacted()} -> {reply.strip()[:40]!r}"
    except LLMError as e:
        return False, str(e)


def _main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="sysmldiag.llm", description=__doc__)
    ap.add_argument("--check", action="store_true", help="ping the configured provider")
    ap.add_argument("--show", action="store_true", help="print resolved config (redacted)")
    args = ap.parse_args(argv)
    if args.show:
        try:
            print(LLMConfig.from_env().redacted())
        except LLMError as e:
            print(f"not configured: {e}")
            return 3
        return 0
    if args.check:
        ok, detail = health_check()
        print(("OK: " if ok else "FAIL: ") + detail)
        return 0 if ok else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
