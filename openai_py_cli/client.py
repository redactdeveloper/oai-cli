"""OpenAI SDK client creation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from .config import AppConfig, Profile, load_config
from .errors import MissingApiKeyError
from .runtime import options


@dataclass(frozen=True)
class ClientContext:
    config: AppConfig
    profile_name: str
    profile: Profile
    api_key_env: str
    api_key_present: bool


def get_client(config: AppConfig | None = None) -> Any:
    context = get_client_context(config)
    api_key = os.environ.get(context.api_key_env)
    if not api_key:
        raise MissingApiKeyError(
            f"{context.api_key_env} is not set. Run: export {context.api_key_env}=..."
        )
    from openai import OpenAI

    return OpenAI(
        api_key=api_key,
        base_url=context.profile.base_url,
        organization=context.profile.organization,
        project=context.profile.project,
        timeout=options.timeout,
    )


def get_client_context(config: AppConfig | None = None) -> ClientContext:
    cfg = config or load_config()
    profile = cfg.active()
    return ClientContext(
        config=cfg,
        profile_name=cfg.active_profile,
        profile=profile,
        api_key_env=profile.api_key_env,
        api_key_present=bool(os.environ.get(profile.api_key_env)),
    )
