from pathlib import Path

import pytest

from openai_py_cli.client import get_client
from openai_py_cli.config import AppConfig, Profile, load_config, write_config
from openai_py_cli.errors import MissingApiKeyError


def test_load_default_config_when_missing(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.default_model == "gpt-4.1-mini"
    assert cfg.active().api_key_env == "OPENAI_API_KEY"


def test_profile_switching_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    cfg = AppConfig(
        active_profile="work",
        profiles={
            "default": Profile(),
            "work": Profile(api_key_env="OPENAI_WORK_API_KEY", default_model="gpt-4.1"),
        },
    )
    write_config(cfg, path)
    loaded = load_config(path)
    assert loaded.active_profile == "work"
    assert loaded.active().api_key_env == "OPENAI_WORK_API_KEY"


def test_missing_env_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError):
        get_client(AppConfig())
