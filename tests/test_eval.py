from pathlib import Path

import pytest

from openai_py_cli.commands.eval_cmd import load_eval_cases
from openai_py_cli.errors import ValidationError


def test_load_eval_cases(tmp_path: Path) -> None:
    path = tmp_path / "eval.jsonl"
    path.write_text('{"id":"a","prompt":"Say hi"}\n{"prompt":"Say bye"}\n', encoding="utf-8")
    assert load_eval_cases(path) == [
        {"id": "a", "prompt": "Say hi"},
        {"id": "2", "prompt": "Say bye"},
    ]


def test_load_eval_cases_rejects_missing_prompt(tmp_path: Path) -> None:
    path = tmp_path / "eval.jsonl"
    path.write_text('{"id":"a"}\n', encoding="utf-8")
    with pytest.raises(ValidationError):
        load_eval_cases(path)
