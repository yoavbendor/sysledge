"""Safe, automated ingestion pipeline for the sysledge knowledge base.

Layer B agents enqueue `Patch` objects (queue.py); the apply-authority
(authority.py) is the single writer to the model tree, validating every edit and
rolling back on failure. Stdlib-only by design — see docs and the plan.
"""
