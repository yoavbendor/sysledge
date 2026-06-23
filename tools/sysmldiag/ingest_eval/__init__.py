"""Layer B — optional documentation -> SysML ingestion eval.

This is the ONLY place in the toolchain that uses an LLM, and it never runs in
the deterministic test path or CI gate. It exercises the doc->model->diagram
pipeline on richer input so we can confirm the views scale beyond the pilot.

The model is small/cheap by policy: default `claude-haiku-4-5-20251001`, with a
pluggable backend so a local OpenAI-compatible endpoint (e.g. a Gemma server)
can be swapped in via environment variables. See `extractor.py`.
"""
