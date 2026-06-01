"""Shared dry-run payload rendering."""

from __future__ import annotations

from typing import Any

from .client import ClientContext


def build_dry_run(
    *,
    operation: str,
    model: str,
    payload: dict[str, Any],
    redaction_enabled: bool,
    context: ClientContext,
) -> dict[str, Any]:
    return {
        "operation": operation,
        "model": model,
        "request_payload": payload,
        "redaction_enabled": redaction_enabled,
        "profile": context.profile_name,
        "base_url": context.profile.base_url,
        "api_key_env": context.api_key_env,
        "api_key_present": context.api_key_present,
    }
