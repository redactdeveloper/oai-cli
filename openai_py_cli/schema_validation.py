"""JSON and JSONL validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema import ValidationError as JsonSchemaError

from .errors import ValidationError


def load_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValidationError(f"Could not read JSON file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc


def validate_json_schema(schema: Any) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except JsonSchemaError as exc:
        raise ValidationError(f"Invalid JSON schema: {exc.message}") from exc


def validate_json_value(value: Any, schema: Any) -> None:
    validate_json_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: item.path)
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ValidationError(f"JSON response does not match schema at {location}: {first.message}")


def parse_json_output(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Model output is not valid JSON: {exc}") from exc


def validate_jsonl(path: Path) -> tuple[int, dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(f"Could not read JSONL file {path}: {exc}") from exc
    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        raise ValidationError("JSONL file is empty.")
    first_obj: dict[str, Any] | None = None
    for index, line in enumerate(non_empty, start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSONL at line {index}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValidationError(f"Invalid JSONL at line {index}: expected an object.")
        if first_obj is None:
            first_obj = value
    return len(non_empty), first_obj or {}
