import json

import pytest

from openai_py_cli.commands import models
from openai_py_cli.errors import ApiError


def test_load_model_cache(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "models.json"
    path.write_text(json.dumps({"models": [{"id": "gpt-test"}]}), encoding="utf-8")
    monkeypatch.setattr(models, "cache_path", lambda: path)
    assert models.load_model_cache()["models"][0]["id"] == "gpt-test"


def test_load_model_cache_missing(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "cache_path", lambda: tmp_path / "missing.json")
    with pytest.raises(ApiError):
        models.load_model_cache()
