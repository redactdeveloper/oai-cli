"""AI-assisted code review from stdin diff."""

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

FOCUS_VALUES = {"security", "bugs", "performance", "style"}


def code_review(
    model: Annotated[str | None, typer.Option("--model", "-m")] = None,
    focus: Annotated[str | None, typer.Option("--focus")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[str, typer.Option("--output")] = "markdown",
) -> None:
    if focus and focus not in FOCUS_VALUES:
        raise typer.BadParameter("--focus must be security, bugs, performance, or style")
    if output not in {"markdown", "json"}:
        raise typer.BadParameter("--output must be markdown or json")
    diff = typer.get_text_stream("stdin").read()
    if not diff.strip():
        raise typer.BadParameter("Diff input is empty.")
    redacted = redact_text(diff)
    if redacted.findings:
        print_warning(f"Redacted sensitive data: {', '.join(redacted.findings)}")
    cfg = load_config()
    context = get_client_context(cfg)
    selected_model = model or context.profile.default_model
    prompt = build_code_review_prompt(redacted.text, focus=focus, output=output)
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
        raise ApiError(f"Code review request failed: {exc}") from exc
    console.print(getattr(response, "output_text", str(response)))


def build_code_review_prompt(diff: str, *, focus: str | None, output: str) -> str:
    focus_line = f"Prioritize {focus} findings." if focus else "Prioritize correctness and risk."
    return (
        "Review this git diff as a senior engineer. Return findings first, ordered by severity. "
        "Include summary, bugs, security issues, performance issues, style issues, and suggested "
        f"patch snippets. {focus_line} Output format: {output}.\n\nDiff:\n"
        f"{diff}"
    )
