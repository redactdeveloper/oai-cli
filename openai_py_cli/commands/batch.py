"""Batch API commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from rich.panel import Panel
from rich.table import Table

from ..client import get_client
from ..errors import ApiError
from ..output import console, print_json, print_warning
from ..schema_validation import validate_jsonl

app = typer.Typer(help="Create and inspect OpenAI Batch jobs.")

BatchEndpoint = Literal[
    "/v1/responses",
    "/v1/chat/completions",
    "/v1/embeddings",
    "/v1/completions",
    "/v1/moderations",
    "/v1/images/generations",
    "/v1/images/edits",
    "/v1/videos",
]


@app.command("create")
def create_batch(
    jsonl_path: Path,
    endpoint: Annotated[BatchEndpoint, typer.Option("--endpoint")] = "/v1/responses",
    completion_window: Annotated[Literal["24h"], typer.Option("--completion-window")] = "24h",
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    line_count, first = validate_jsonl(jsonl_path)
    console.print(f"Validated {line_count} JSONL rows")
    console.print(Panel(str(first), title="First row"))
    if jsonl_path.stat().st_size > 100 * 1024 * 1024:
        print_warning("File is larger than 100 MB; upload and processing may take a while.")
    if dry_run:
        print_json(
            {
                "operation": "batches.create",
                "jsonl_path": str(jsonl_path),
                "endpoint": endpoint,
                "completion_window": completion_window,
                "line_count": line_count,
            }
        )
        return
    client = get_client()
    try:
        uploaded = client.files.create(file=jsonl_path.open("rb"), purpose="batch")
        batch = client.batches.create(
            input_file_id=uploaded.id,
            endpoint=endpoint,
            completion_window=completion_window,
        )
        print_json(_dump(batch))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Batch creation failed: {exc}") from exc


@app.command("status")
def batch_status(batch_id: str) -> None:
    try:
        print_json(_dump(get_client().batches.retrieve(batch_id)))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Could not retrieve batch: {exc}") from exc


@app.command("list")
def list_batches(limit: Annotated[int, typer.Option("--limit")] = 20) -> None:
    try:
        batches = get_client().batches.list(limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Could not list batches: {exc}") from exc
    table = Table(title="Batches")
    for column in ["id", "status", "endpoint", "created_at"]:
        table.add_column(column)
    for batch in getattr(batches, "data", []):
        table.add_row(
            str(getattr(batch, "id", "")),
            str(getattr(batch, "status", "")),
            str(getattr(batch, "endpoint", "")),
            str(getattr(batch, "created_at", "")),
        )
    console.print(table)


@app.command("cancel")
def cancel_batch(batch_id: str) -> None:
    try:
        print_json(_dump(get_client().batches.cancel(batch_id)))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Could not cancel batch: {exc}") from exc


@app.command("download")
def download_batch(batch_id: str, output: Annotated[Path, typer.Option("--output")]) -> None:
    client = get_client()
    try:
        batch = client.batches.retrieve(batch_id)
        output_file_id = getattr(batch, "output_file_id", None)
        if not output_file_id:
            raise ApiError("Batch does not have an output_file_id yet.")
        content = client.files.content(output_file_id)
        output.write_bytes(content.read())
        console.print(f"Wrote {output}")
    except ApiError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Could not download batch output: {exc}") from exc


def _dump(obj: Any) -> dict[str, Any]:
    return obj.model_dump() if hasattr(obj, "model_dump") else {"value": str(obj)}
