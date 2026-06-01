"""Replay requests saved in the local log store."""

from __future__ import annotations

import json
import time
from typing import Annotated, Any

import typer
from rich.markdown import Markdown
from rich.panel import Panel

from ..client import get_client, get_client_context
from ..config import default_log_path, load_config
from ..dry_run import build_dry_run
from ..errors import ApiError
from ..logging_store import LoggingStore, RequestLog
from ..output import console, print_json
from ..pricing import estimate_cost, estimate_tokens
from .ask import _model_dump, _stream_response


def replay(
    log_id: Annotated[str, typer.Argument(help="Request log id to replay.")],
    model: Annotated[str | None, typer.Option("--model", "-m")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    stream: Annotated[bool, typer.Option("--stream/--no-stream")] = False,
    save: Annotated[bool, typer.Option("--save/--no-save")] = True,
    yes: Annotated[bool, typer.Option("--yes", "-y")] = False,
) -> None:
    cfg = load_config()
    store = LoggingStore(cfg.log_path or default_log_path())
    row = store.show(log_id)
    if row is None:
        raise typer.BadParameter(f"Log id not found: {log_id}")

    payload = build_replay_payload(row, model)
    context = get_client_context(cfg)
    console.print(Panel(json.dumps(payload, indent=2, ensure_ascii=False), title="Replay payload"))

    if dry_run:
        print_json(
            build_dry_run(
                operation="responses.create",
                model=str(payload.get("model", row.model)),
                payload=payload,
                redaction_enabled=cfg.redact_enabled,
                context=context,
            )
        )
        return

    if not yes and not typer.confirm("Repeat this request?"):
        raise typer.Abort()

    client = get_client(cfg)
    started = time.perf_counter()
    response_json: dict[str, Any] | None = None
    try:
        if stream:
            output_text = _stream_response(client, payload)
        else:
            response = client.responses.create(**payload)
            output_text = getattr(response, "output_text", str(response))
            response_json = _model_dump(response)
            console.print(Markdown(output_text))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"OpenAI API replay failed: {exc}") from exc

    if save and cfg.log_enabled and cfg.log_path is not None:
        input_tokens = estimate_tokens(str(payload.get("input", row.input_text)))
        output_tokens = estimate_tokens(output_text)
        LoggingStore(cfg.log_path).insert(
            command="replay",
            model=str(payload.get("model", row.model)),
            input_text=str(payload.get("input", row.input_text)),
            output_text=output_text,
            status="success",
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost_usd=estimate_cost(
                str(payload.get("model", row.model)), input_tokens, output_tokens
            ),
            request_json=payload,
            response_json=response_json,
        )


def build_replay_payload(row: RequestLog, model: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any]
    if row.request_json:
        loaded = json.loads(row.request_json)
        payload = loaded if isinstance(loaded, dict) else {}
    else:
        payload = {"model": row.model, "input": row.input_text}
    if model:
        payload["model"] = model
    return payload
