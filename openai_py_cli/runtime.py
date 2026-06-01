"""Process-wide CLI runtime options."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeOptions:
    debug: bool = False
    timeout: float | None = None
    plain: bool = False
    json_output: bool = False


options = RuntimeOptions()
