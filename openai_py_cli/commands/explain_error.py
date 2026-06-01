"""Explain traceback or log output from stdin."""

from __future__ import annotations

from typing import Annotated

import typer

from ..client import get_client, get_client_context
from ..config import load_config
from ..dry_run import build_dry_run
from ..errors import ApiError
from ..output import console, print_json, print_warning
from ..redaction import redact_text
from .ask import build_responses_payload


def explain_error(
    model: Annotated[str | None, typer.Option("--model", "-m")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    log = typer.get_text_stream("stdin").read()
    if not log.strip():
        raise typer.BadParameter("Error log input is empty.")
    redacted = redact_text(log)
    if redacted.findings:
        print_warning(f"Redacted sensitive data: {', '.join(redacted.findings)}")
    cfg = load_config()
    context = get_client_context(cfg)
    selected_model = model or context.profile.default_model
    prompt = build_explain_error_prompt(redacted.text)
    payload = build_responses_payload(prompt=prompt, model=selected_model)
    if dry_run:
        print_json(
            build_dry_run(
                operation="responses.create",
                model=selected_model,
                payload=payload,
                redaction_enabled=True,
                context=context,
            )
        )
        return
    try:
        response = get_client(cfg).responses.create(**payload)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Explain-error request failed: {exc}") from exc
    console.print(getattr(response, "output_text", str(response)))


def build_explain_error_prompt(log: str) -> str:
    return (
        "Explain this traceback or test log. Infer the language/framework if possible. "
        "Return: short cause, likely file/line, how to reproduce, fix options, and patch "
        f"suggestion.\n\nLog:\n{log}"
    )
