"""Configuration loading and profile management."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from platformdirs import PlatformDirs
from pydantic import BaseModel, Field

if sys.version_info >= (3, 11):  # pragma: no cover - depends on runtime Python
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

from .errors import ConfigError

APP_NAME = "oai-cli"


class Profile(BaseModel):
    api_key_env: str = "OPENAI_API_KEY"
    default_model: str = "gpt-4.1-mini"
    base_url: str | None = None
    organization: str | None = None
    project: str | None = None


class AppConfig(BaseModel):
    default_model: str = "gpt-4.1-mini"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str | None = None
    organization: str | None = None
    project: str | None = None
    log_enabled: bool = True
    log_path: Path | None = None
    redact_enabled: bool = True
    active_profile: str = "default"
    profiles: dict[str, Profile] = Field(default_factory=lambda: {"default": Profile()})

    def active(self) -> Profile:
        profile = self.profiles.get(self.active_profile)
        if profile is None:
            raise ConfigError(f"Active profile '{self.active_profile}' does not exist.")
        return Profile(
            api_key_env=profile.api_key_env or self.api_key_env,
            default_model=profile.default_model or self.default_model,
            base_url=profile.base_url if profile.base_url is not None else self.base_url,
            organization=profile.organization
            if profile.organization is not None
            else self.organization,
            project=profile.project if profile.project is not None else self.project,
        )


def dirs() -> PlatformDirs:
    return PlatformDirs(APP_NAME, appauthor=False)


def config_path() -> Path:
    override = os.environ.get("OAI_CLI_CONFIG") or os.environ.get("OPENAI_PY_CONFIG")
    return Path(override or Path(dirs().user_config_dir) / "config.toml")


def default_log_path() -> Path:
    override = os.environ.get("OAI_CLI_LOG_PATH") or os.environ.get("OPENAI_PY_LOG_PATH")
    return Path(override or Path(dirs().user_data_dir) / "logs.sqlite")


def load_config(path: Path | None = None) -> AppConfig:
    cfg_path = path or config_path()
    if not cfg_path.exists():
        config = AppConfig()
        config.log_path = default_log_path()
        return config
    try:
        raw_text = cfg_path.read_text(encoding="utf-8")
        raw = _restore_nulls(tomllib.loads(_toml_null_to_sentinel(raw_text)))
    except OSError as exc:
        raise ConfigError(f"Could not read config file {cfg_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {cfg_path}: {exc}") from exc
    config = AppConfig.model_validate(raw)
    if config.log_path is None:
        config.log_path = default_log_path()
    return config


def write_config(config: AppConfig, path: Path | None = None) -> Path:
    cfg_path = path or config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(to_toml(config), encoding="utf-8")
    return cfg_path


def to_toml(config: AppConfig) -> str:
    data = config.model_dump(mode="json")
    profiles = data.pop("profiles")
    lines: list[str] = []
    for key, value in data.items():
        lines.append(_toml_line(key, value))
    for name, profile in profiles.items():
        lines.append("")
        lines.append(f"[profiles.{name}]")
        for key, value in profile.items():
            lines.append(_toml_line(key, value))
    return "\n".join(lines) + "\n"


def _toml_line(key: str, value: Any) -> str:
    if value is None:
        return f"{key} = null"
    if isinstance(value, bool):
        return f"{key} = {str(value).lower()}"
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'{key} = "{escaped}"'


def _toml_null_to_sentinel(text: str) -> str:
    return re.sub(r"=\s*null(\s*(?:#.*)?$)", '= "__OPENAI_PY_NULL__"\\1', text, flags=re.M)


def _restore_nulls(value: Any) -> Any:
    if value == "__OPENAI_PY_NULL__":
        return None
    if isinstance(value, dict):
        return {key: _restore_nulls(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_nulls(item) for item in value]
    return value


def ensure_config_exists() -> Path:
    path = config_path()
    if not path.exists():
        write_config(load_config(path), path)
    return path
