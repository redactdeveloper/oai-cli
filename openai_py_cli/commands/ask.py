"""One-shot prompt command."""

from __future__ import annotations

import time
from typing import Annotated, Any, cast

import typer
from rich.live import Live
from rich.markdown import Markdown

from ..client import get_client, get_client_context
from ..config import load_config
from ..dry_run import build_dry_run
from ..errors import ApiError
from ..logging_store import LoggingStore
from ..output import console, print_json, print_warning
from ..pricing import estimate_cost, estimate_tokens
from ..redaction import contains_secrets, redact_text


def ask(
    prompt: Annotated[
        str | None,
        typer.Argument(help="Prompt text. Reads stdin when omitted."),
    ] = None,
    model: Annotated[str | None, typer.Option("--model", "-m")] = None,
    system: Annotated[str | None, typer.Option("--system")] = None,
    temperature: Annotated[float | None, typer.Option("--temperature")] = None,
    max_output_tokens: Annotated[int | None, typer.Option("--max-output-tokens")] = None,
    stream: Annotated[bool, typer.Option("--stream/--no-stream")] = True,
    json_mode: Annotated[bool, typer.Option("--json")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    cost_estimate: Annotated[bool, typer.Option("--cost-estimate")] = False,
    save: Annotated[bool, typer.Option("--save/--no-save")] = True,
    redact: Annotated[bool | None, typer.Option("--redact/--no-redact")] = None,
) -> None:
    cfg = load_config()
    context = get_client_context(cfg)
    active = context.profile
    selected_model = model or active.default_model
    input_text = prompt if prompt is not None else typer.get_text_stream("stdin").read()
    if not input_text.strip():
        raise typer.BadParameter("Prompt is empty.")

    redact_enabled = cfg.redact_enabled if redact is None else redact
    original_input = input_text
    if redact_enabled:
        result = redact_text(input_text)
        input_text = result.text
        if result.findings:
            print_warning(f"Redacted sensitive data: {', '.join(result.findings)}")
    elif contains_secrets(input_text):
        print_warning("Prompt appears to contain secrets and redaction is disabled.")

    payload = build_responses_payload(
        prompt=input_text,
        model=selected_model,
        system=system,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        json_mode=json_mode,
    )

    if cost_estimate:
        tokens = estimate_tokens(input_text + (system or ""))
        cost = estimate_cost(selected_model, input_tokens=tokens)
        console.print(
            f"Estimated input tokens: {tokens}; cost: "
            f"{'unknown' if cost is None else f'${cost:.6f}'}"
        )
        if dry_run:
            return

    if dry_run:
        print_json(
            build_dry_run(
                operation="responses.create",
                model=selected_model,
                payload=payload,
                redaction_enabled=redact_enabled,
                context=context,
            )
        )
        return

    client = get_client(cfg)
    started = time.perf_counter()
    output_text = ""
    response_json: dict[str, Any] | None = None
    try:
        if stream:
            output_text = _stream_response(client, payload)
        else:
            response = client.responses.create(**payload)
            output_text = getattr(response, "output_text", str(response))
            response_json = _model_dump(response)
            console.print(Markdown(output_text))
    except Exception as exc:  # noqa: BLE001 - SDK exception types vary by version
        _save_log(
            cfg,
            save,
            selected_model,
            original_input,
            "",
            "error",
            int((time.perf_counter() - started) * 1000),
            payload,
            None,
            str(exc),
        )
        raise ApiError(f"OpenAI API request failed: {exc}") from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(output_text)
    _save_log(
        cfg,
        save,
        selected_model,
        original_input,
        output_text,
        "success",
        latency_ms,
        payload,
        response_json,
        None,
        input_tokens,
        output_tokens,
    )


def build_responses_payload(
    *,
    prompt: str,
    model: str,
    system: str | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    json_mode: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model, "input": prompt}
    if system:
        payload["instructions"] = system
    if temperature is not None:
        payload["temperature"] = temperature
    if max_output_tokens is not None:
        payload["max_output_tokens"] = max_output_tokens
    if json_mode:
        payload["text"] = {"format": {"type": "json_object"}}
    return payload


def _stream_response(client: Any, payload: dict[str, Any]) -> str:
    output_parts: list[str] = []
    with (
        Live("", console=console, refresh_per_second=12) as live,
        client.responses.stream(**payload) as stream,
    ):
        for event in stream:
            if getattr(event, "type", "") == "response.output_text.delta":
                delta = getattr(event, "delta", "")
                output_parts.append(delta)
                live.update(Markdown("".join(output_parts)))
        stream.get_final_response()
    return "".join(output_parts)


def _save_log(
    cfg: Any,
    save: bool,
    model: str,
    input_text: str,
    output_text: str,
    status: str,
    latency_ms: int,
    request_json: dict[str, Any],
    response_json: dict[str, Any] | None,
    error: str | None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    if not save or not cfg.log_enabled or cfg.log_path is None:
        return
    total_tokens = (
        (input_tokens or 0) + (output_tokens or 0)
        if input_tokens or output_tokens
        else None
    )
    LoggingStore(cfg.log_path).insert(
        command="ask",
        model=model,
        input_text=input_text,
        output_text=output_text,
        status=status,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimate_cost(model, input_tokens or 0, output_tokens or 0),
        request_json=request_json,
        response_json=response_json,
        error=error,
    )


def _model_dump(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return cast(dict[str, Any], obj.model_dump())
    return {"value": str(obj)}
