"""OpenAI Files API commands."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from rich.progress import Progress
from rich.table import Table

from ..client import get_client
from ..errors import ApiError
from ..output import console, print_json

app = typer.Typer(help="Manage OpenAI files.")

FilePurpose = Literal["assistants", "batch", "fine-tune", "vision", "user_data", "evals"]


@app.command("list")
def list_files(limit: Annotated[int, typer.Option("--limit")] = 100) -> None:
    try:
        files = get_client().files.list()
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Could not list files: {exc}") from exc
    table = Table(title="Files")
    for column in ["id", "filename", "purpose", "bytes", "created_at"]:
        table.add_column(column)
    for item in getattr(files, "data", [])[:limit]:
        table.add_row(
            str(getattr(item, "id", "")),
            str(getattr(item, "filename", "")),
            str(getattr(item, "purpose", "")),
            str(getattr(item, "bytes", "")),
            str(getattr(item, "created_at", "")),
        )
    console.print(table)


@app.command("upload")
def upload_file(
    path: Path,
    purpose: Annotated[FilePurpose, typer.Option("--purpose")] = "assistants",
) -> None:
    if not path.exists():
        raise typer.BadParameter(f"File does not exist: {path}")
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    try:
        with Progress() as progress:
            task = progress.add_task(
                f"Uploading {path.name} ({mime_type})",
                total=path.stat().st_size,
            )
            with path.open("rb") as handle:
                result = get_client().files.create(file=handle, purpose=purpose)
            progress.update(task, completed=path.stat().st_size)
        print_json(_dump(result))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Could not upload file: {exc}") from exc


@app.command("retrieve")
def retrieve_file(file_id: str) -> None:
    try:
        print_json(_dump(get_client().files.retrieve(file_id)))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Could not retrieve file: {exc}") from exc


@app.command("delete")
def delete_file(file_id: str) -> None:
    try:
        print_json(_dump(get_client().files.delete(file_id)))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Could not delete file: {exc}") from exc


@app.command("download")
def download_file(file_id: str, output: Annotated[Path, typer.Option("--output")]) -> None:
    try:
        content = get_client().files.content(file_id)
        data = content.read()
        with Progress() as progress:
            task = progress.add_task(f"Writing {output}", total=len(data))
            output.write_bytes(data)
            progress.update(task, completed=len(data))
        console.print(f"Wrote {output}")
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Could not download file: {exc}") from exc


def _dump(obj: Any) -> dict[str, Any]:
    return obj.model_dump() if hasattr(obj, "model_dump") else {"value": str(obj)}
