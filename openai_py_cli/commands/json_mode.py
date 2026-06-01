"""Strict JSON output command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from ..client import get_client, get_client_context
from ..config import load_config
from ..dry_run import build_dry_run
from ..errors import ApiError, ValidationError
from ..output import console, print_json
from ..schema_validation import (
    load_json_file,
    parse_json_output,
    validate_json_schema,
    validate_json_value,
)


def json_command(
    prompt: Annotated[
        str | None,
        typer.Argument(help="Prompt text. Reads stdin when omitted."),
    ] = None,
    schema_path: Annotated[Path, typer.Option("--schema", help="JSON Schema file.")] = Path(
        "schema.json"
    ),
    model: Annotated[str | None, typer.Option("--model", "-m")] = None,
    input_file: Annotated[Path | None, typer.Option("--input-file")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    retry: Annotated[int, typer.Option("--retry", min=0, max=5)] = 0,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    cfg = load_config()
    context = get_client_context(cfg)
    selected_model = model or context.profile.default_model
    schema = load_json_file(schema_path)
    validate_json_schema(schema)
    input_text = _read_prompt(prompt, input_file)
    payload = build_json_payload(input_text, schema, selected_model)

    if dry_run:
        print_json(
            build_dry_run(
                operation="responses.create",
                model=selected_model,
                payload=payload,
                redaction_enabled=cfg.redact_enabled,
                context=context,
            )
        )
        return

    client = get_client(cfg)
    last_raw = ""
    for attempt in range(retry + 1):
        try:
            response = client.responses.create(**payload)
            last_raw = getattr(response, "output_text", str(response))
            parsed = parse_json_output(last_raw)
            validate_json_value(parsed, schema)
            rendered = json.dumps(parsed, indent=2, ensure_ascii=False)
            if output:
                output.write_text(rendered + "\n", encoding="utf-8")
                console.print(f"Wrote {output}")
            else:
                print_json(parsed)
            return
        except ValidationError:
            if attempt >= retry:
                console.print(last_raw)
                raise
            payload["input"] = (
                f"{input_text}\n\nPrevious output was invalid JSON or failed schema validation. "
                "Return corrected JSON only."
            )
        except Exception as exc:  # noqa: BLE001
            raise ApiError(f"OpenAI JSON request failed: {exc}") from exc


def build_json_payload(prompt: str, schema: Any, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "input": (
            f"{prompt}\n\nReturn JSON only. It must validate against this JSON Schema:\n"
            f"{json.dumps(schema, ensure_ascii=False)}"
        ),
        "text": {"format": {"type": "json_object"}},
    }


def _read_prompt(prompt: str | None, input_file: Path | None) -> str:
    parts: list[str] = []
    if prompt:
        parts.append(prompt)
    if input_file:
        parts.append(input_file.read_text(encoding="utf-8"))
    if not parts:
        parts.append(typer.get_text_stream("stdin").read())
    text = "\n\n".join(parts).strip()
    if not text:
        raise typer.BadParameter("Prompt is empty.")
    return text
