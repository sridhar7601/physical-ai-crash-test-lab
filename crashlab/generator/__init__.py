"""Isaac Sim / Replicator frame generation.

Only `scene` and `generate` import `omni.*`; they run under Isaac Sim's Python.
`plan_frame` and the physical mapping are pure arithmetic and testable off-GPU.
"""

from __future__ import annotations

__all__ = ["scene", "generate"]
