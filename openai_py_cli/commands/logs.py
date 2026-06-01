"""Request log commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from ..config import default_log_path, load_config
from ..logging_store import LoggingStore
from ..output import console, print_json
from ..redaction import redact_text

app = typer.Typer(help="Inspect local SQLite request logs.")


def _store() -> LoggingStore:
    cfg = load_config()
    return LoggingStore(cfg.log_path or default_log_path())


@app.command("list")
def list_logs(limit: Annotated[int, typer.Option("--limit", "-n")] = 50) -> None:
    table = Table(title="Request logs")
    for col in ["id", "date", "command", "model", "status", "tokens", "cost", "prompt preview"]:
        table.add_column(col)
    for row in _store().list(limit):
        preview = row.input_text.replace("\n", " ")[:80]
        tokens = "" if row.total_tokens is None else str(row.total_tokens)
        cost = "" if row.estimated_cost_usd is None else f"${row.estimated_cost_usd:.6f}"
        table.add_row(
            row.id,
            row.created_at[:19],
            row.command,
            row.model,
            row.status,
            tokens,
            cost,
            preview,
        )
    console.print(table)


@app.command("show")
def show_log(log_id: str, json_output: Annotated[bool, typer.Option("--json")] = False) -> None:
    row = _store().show(log_id)
    if row is None:
        raise typer.BadParameter(f"Log id not found: {log_id}")
    if json_output:
        print_json(row.__dict__)
    else:
        print_json(row.__dict__)


@app.command("delete")
def delete_log(log_id: str) -> None:
    deleted = _store().delete(log_id)
    if not deleted:
        raise typer.BadParameter(f"Log id not found: {log_id}")
    console.print(f"Deleted log {log_id}")


@app.command("clear")
def clear_logs(force: Annotated[bool, typer.Option("--yes", "-y")] = False) -> None:
    if not force and not typer.confirm("Delete all request logs?"):
        raise typer.Abort()
    count = _store().clear()
    console.print(f"Deleted {count} logs")


@app.command("export")
def export_logs(fmt: Annotated[str, typer.Option("--format")] = "json") -> None:
    if fmt not in {"json", "jsonl", "csv"}:
        raise typer.BadParameter("--format must be json, jsonl, or csv")
    console.print(_store().export(fmt))


@app.command("scan-secrets")
def scan_secrets(json_output: Annotated[bool, typer.Option("--json")] = False) -> None:
    findings: list[dict[str, object]] = []
    for row in _store().list(limit=10_000):
        combined = "\n".join(
            part
            for part in [
                row.input_text,
                row.output_text,
                row.request_json or "",
                row.response_json or "",
                row.error or "",
            ]
            if part
        )
        result = redact_text(combined)
        if result.findings:
            findings.append(
                {
                    "id": row.id,
                    "created_at": row.created_at,
                    "findings": result.findings,
                }
            )
    if json_output:
        print_json(findings)
        return
    table = Table(title="Secret scan")
    table.add_column("id")
    table.add_column("date")
    table.add_column("findings")
    for item in findings:
        table.add_row(
            str(item["id"]),
            str(item["created_at"])[:19],
            ", ".join(
                f"{key}:{value}"
                for key, value in _findings_dict(item["findings"]).items()
            ),
        )
    console.print(table)


def _findings_dict(value: object) -> dict[str, int]:
    return value if isinstance(value, dict) else {}
