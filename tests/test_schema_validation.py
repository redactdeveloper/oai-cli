import json
from pathlib import Path

import pytest

from openai_py_cli.errors import ValidationError
from openai_py_cli.schema_validation import (
    parse_json_output,
    validate_json_value,
    validate_jsonl,
)


def test_validate_jsonl_returns_count_and_first_row(tmp_path: Path) -> None:
    path = tmp_path / "batch.jsonl"
    path.write_text('{"custom_id":"1"}\n{"custom_id":"2"}\n', encoding="utf-8")
    count, first = validate_jsonl(path)
    assert count == 2
    assert first == {"custom_id": "1"}


def test_validate_jsonl_rejects_invalid_line(tmp_path: Path) -> None:
    path = tmp_path / "batch.jsonl"
    path.write_text('{"ok": true}\nnot-json\n', encoding="utf-8")
    with pytest.raises(ValidationError):
        validate_jsonl(path)


def test_json_schema_validation() -> None:
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
    }
    validate_json_value({"name": "Ada"}, schema)
    with pytest.raises(ValidationError):
        validate_json_value({"name": 1}, schema)


def test_parse_json_output() -> None:
    assert parse_json_output(json.dumps({"ok": True})) == {"ok": True}
    with pytest.raises(ValidationError):
        parse_json_output("not-json")
