"""Compare one prompt across multiple models."""

from __future__ import annotations

import difflib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.panel import Panel
from rich.table import Table

from ..client import get_client, get_client_context
from ..config import load_config
from ..dry_run import build_dry_run
from ..output import console, print_json, print_warning
from ..pricing import estimate_cost, estimate_tokens
from ..redaction import contains_secrets, redact_text
from .ask import build_responses_payload


@dataclass(frozen=True)
class CompareResult:
    model: str
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None
    status: str
    output_text: str
    error: str | None = None


def compare(
    prompt: Annotated[
        str | None,
        typer.Argument(help="Prompt text. Reads stdin when omitted."),
    ] = None,
    models: Annotated[list[str] | None, typer.Option("--model", "-m")] = None,
    system: Annotated[str | None, typer.Option("--system")] = None,
    diff: Annotated[bool, typer.Option("--diff")] = False,
    json_output: Annotated[
        Path | None,
        typer.Option("--json-output", help="Write comparison result to JSON file."),
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    redact: Annotated[bool | None, typer.Option("--redact/--no-redact")] = None,
) -> None:
    cfg = load_config()
    context = get_client_context(cfg)
    selected_models = models or [context.profile.default_model]
    if len(selected_models) < 2 and not dry_run:
        print_warning("Only one model was provided; comparison table will contain one result.")

    input_text = prompt if prompt is not None else typer.get_text_stream("stdin").read()
    if not input_text.strip():
        raise typer.BadParameter("Prompt is empty.")

    redact_enabled = cfg.redact_enabled if redact is None else redact
    if redact_enabled:
        redacted = redact_text(input_text)
        input_text = redacted.text
        if redacted.findings:
            print_warning(f"Redacted sensitive data: {', '.join(redacted.findings)}")
    elif contains_secrets(input_text):
        print_warning("Prompt appears to contain secrets and redaction is disabled.")

    payloads = [
        build_responses_payload(prompt=input_text, model=model, system=system)
        for model in selected_models
    ]
    if dry_run:
        print_json(
            [
                build_dry_run(
                    operation="responses.create",
                    model=model,
                    payload=payload,
                    redaction_enabled=redact_enabled,
                    context=context,
                )
                for model, payload in zip(selected_models, payloads, strict=True)
            ]
        )
        return

    client = get_client(cfg)
    results = [_run_model(client, payload) for payload in payloads]
    render_compare_results(results, show_diff=diff)

    if json_output:
        json_output.write_text(
            json.dumps([asdict(result) for result in results], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        console.print(f"Wrote {json_output}")


def render_compare_results(results: list[CompareResult], *, show_diff: bool = False) -> None:
    table = Table(title="Model comparison")
    for column in ["model", "latency", "input", "output", "total", "cost", "status"]:
        table.add_column(column)
    for result in results:
        cost = (
            "unknown"
            if result.estimated_cost_usd is None
            else f"${result.estimated_cost_usd:.6f}"
        )
        table.add_row(
            result.model,
            f"{result.latency_ms} ms",
            _num(result.input_tokens),
            _num(result.output_tokens),
            _num(result.total_tokens),
            cost,
            result.status,
        )
    console.print(table)

    for result in results:
        body = result.output_text if result.status == "success" else result.error or "No output."
        console.print(Panel(body, title=result.model))

    if show_diff and len(results) >= 2:
        base = results[0]
        for result in results[1:]:
            lines = difflib.unified_diff(
                base.output_text.splitlines(),
                result.output_text.splitlines(),
                fromfile=base.model,
                tofile=result.model,
                lineterm="",
            )
            console.print(
                Panel(
                    "\n".join(lines) or "No diff.",
                    title=f"Diff: {base.model} vs {result.model}",
                )
            )


def _run_model(client: Any, payload: dict[str, Any]) -> CompareResult:
    model = str(payload["model"])
    started = time.perf_counter()
    input_tokens = estimate_tokens(str(payload.get("input", "")))
    try:
        response = client.responses.create(**payload)
        output_text = getattr(response, "output_text", str(response))
        output_tokens = estimate_tokens(output_text)
        total_tokens = input_tokens + output_tokens
        return CompareResult(
            model=model,
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimate_cost(model, input_tokens, output_tokens),
            status="success",
            output_text=output_text,
        )
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, KeyboardInterrupt):
            raise
        return CompareResult(
            model=model,
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=input_tokens,
            output_tokens=None,
            total_tokens=None,
            estimated_cost_usd=None,
            status="error",
            output_text="",
            error=str(exc),
        )


def _num(value: int | None) -> str:
    return "unknown" if value is None else str(value)
