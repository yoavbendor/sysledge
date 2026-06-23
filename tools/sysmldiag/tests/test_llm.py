"""Offline tests for the provider-agnostic LLM client (no network).

Covers config resolution, bring-your-own-key handling, and provider defaults —
the logic that decides *whether* and *how* to call a provider, without making a
call. The network path is exercised only by the optional Layer B eval.
"""

from __future__ import annotations

import unittest
from unittest import mock

from sysmldiag.llm import PROVIDERS, LLMConfig, LLMError


def _env(**kw):
    return mock.patch.dict("os.environ", kw, clear=True)


class LLMConfigTest(unittest.TestCase):
    def test_default_provider_is_anthropic_haiku(self):
        with _env(ANTHROPIC_API_KEY="sk-test-abcd"):
            cfg = LLMConfig.from_env()
        self.assertEqual(cfg.provider, "anthropic")
        self.assertEqual(cfg.model, PROVIDERS["anthropic"]["default_model"])
        self.assertIn("anthropic.com", cfg.base_url)

    def test_openai_provider_defaults(self):
        with _env(SYSMLDIAG_LLM_PROVIDER="openai", OPENAI_API_KEY="sk-oai"):
            cfg = LLMConfig.from_env()
        self.assertEqual(cfg.provider, "openai")
        self.assertEqual(cfg.model, PROVIDERS["openai"]["default_model"])
        self.assertIn("openai.com", cfg.base_url)

    def test_missing_key_raises(self):
        with _env(SYSMLDIAG_LLM_PROVIDER="openai"):
            with self.assertRaises(LLMError):
                LLMConfig.from_env()

    def test_unknown_provider_raises(self):
        with _env(SYSMLDIAG_LLM_PROVIDER="bogus", SYSMLDIAG_LLM_API_KEY="x"):
            with self.assertRaises(LLMError):
                LLMConfig.from_env()

    def test_byo_overrides_model_and_base_url(self):
        with _env(
            SYSMLDIAG_LLM_PROVIDER="openai",
            SYSMLDIAG_LLM_API_KEY="local-none",
            SYSMLDIAG_LLM_MODEL="gemma-2-9b",
            SYSMLDIAG_LLM_BASE_URL="http://localhost:8000/v1/",
        ):
            cfg = LLMConfig.from_env()
        self.assertEqual(cfg.model, "gemma-2-9b")
        self.assertEqual(cfg.base_url, "http://localhost:8000/v1")  # trailing / stripped
        self.assertEqual(cfg.api_key, "local-none")

    def test_redacted_hides_key(self):
        with _env(ANTHROPIC_API_KEY="sk-secret-tail1234"):
            red = LLMConfig.from_env().redacted()
        self.assertNotIn("secret", red)
        self.assertIn("1234", red)


if __name__ == "__main__":
    unittest.main()
