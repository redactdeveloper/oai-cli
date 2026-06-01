"""Run prompt evals across one or more models."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table

from ..client import get_client, get_client_context
from ..config import load_config
from ..dry_run import build_dry_run
from ..errors import ValidationError
from ..output import console, print_json
from ..pricing import estimate_cost, estimate_tokens
from .ask import build_responses_payload


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    model: str
    status: str
    latency_ms: int
    output_text: str
    estimated_cost_usd: float | None
    error: str | None = None


def eval_command(
    cases_path: Annotated[Path, typer.Argument(help="JSONL file with prompt cases.")],
    models: Annotated[list[str] | None, typer.Option("--model", "-m")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    cases = load_eval_cases(cases_path)
    cfg = load_config()
    context = get_client_context(cfg)
    selected_models = models or [context.profile.default_model]
    payloads = [
        (case["id"], model, build_responses_payload(prompt=case["prompt"], model=model))
        for case in cases
        for model in selected_models
    ]
    if dry_run:
        print_json(
            [
                build_dry_run(
                    operation="responses.create",
                    model=model,
                    payload=payload,
                    redaction_enabled=cfg.redact_enabled,
                    context=context,
                )
                for _, model, payload in payloads
            ]
        )
        return
    client = get_client(cfg)
    results = [
        _run_eval_case(client, case_id, model, payload)
        for case_id, model, payload in payloads
    ]
    if output:
        output.write_text(
            json.dumps([asdict(result) for result in results], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if json_output:
        print_json([asdict(result) for result in results])
    else:
        _render_results(results)


def load_eval_cases(path: Path) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(f"Could not read eval file {path}: {exc}") from exc
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid eval JSONL at line {index}: {exc}") from exc
        prompt = raw.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValidationError(f"Eval line {index} must contain a non-empty prompt string.")
        cases.append({"id": str(raw.get("id", index)), "prompt": prompt})
    if not cases:
        raise ValidationError("Eval file has no cases.")
    return cases


def _run_eval_case(
    client: Any,
    case_id: str,
    model: str,
    payload: dict[str, Any],
) -> EvalResult:
    started = time.perf_counter()
    try:
        response = client.responses.create(**payload)
        output_text = getattr(response, "output_text", str(response))
        input_tokens = estimate_tokens(str(payload.get("input", "")))
        output_tokens = estimate_tokens(output_text)
        return EvalResult(
            case_id=case_id,
            model=model,
            status="success",
            latency_ms=int((time.perf_counter() - started) * 1000),
            output_text=output_text,
            estimated_cost_usd=estimate_cost(model, input_tokens, output_tokens),
        )
    except Exception as exc:  # noqa: BLE001
        return EvalResult(
            case_id=case_id,
            model=model,
            status="error",
            latency_ms=int((time.perf_counter() - started) * 1000),
            output_text="",
            estimated_cost_usd=None,
            error=str(exc),
        )


def _render_results(results: list[EvalResult]) -> None:
    table = Table(title="Eval results")
    for column in ["case", "model", "status", "latency", "cost"]:
        table.add_column(column)
    for result in results:
        cost = (
            "unknown"
            if result.estimated_cost_usd is None
            else f"${result.estimated_cost_usd:.6f}"
        )
        table.add_row(result.case_id, result.model, result.status, f"{result.latency_ms} ms", cost)
    console.print(table)
