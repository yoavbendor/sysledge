"""Safe, automated ingestion pipeline for the sysledge knowledge base.

Layer B agents (agents.py) enqueue `Patch` objects (queue.py); the apply-authority
(authority.py) is the single writer to the model tree, validating every edit and
rolling back on failure. The `Patch` schema uses pydantic (parse-time validation of
machine output); everything else is stdlib — see docs and the plan.
"""

from .agents import (
    Chunk,
    Contradiction,
    ReconcileResult,
    ScanResult,
    chunk_markdown,
    connect,
    port_map,
    reconcile,
    scan,
    write_review,
)
from .authority import apply_one, drain
from .queue import Patch, PatchError, Provenance, Queue

__all__ = [
    "Patch",
    "PatchError",
    "Provenance",
    "Queue",
    "apply_one",
    "drain",
    "Chunk",
    "ScanResult",
    "Contradiction",
    "ReconcileResult",
    "chunk_markdown",
    "scan",
    "connect",
    "reconcile",
    "write_review",
    "port_map",
]
