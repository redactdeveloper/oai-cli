"""Model listing and cache commands."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, cast

import typer
from rich.table import Table

from ..client import get_client
from ..config import dirs
from ..errors import ApiError
from ..output import console, print_json

app = typer.Typer(help="List and cache available models.")


@app.command("list")
def list_models(
    refresh: Annotated[bool, typer.Option("--refresh")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    data = fetch_models() if refresh or not cache_path().exists() else load_model_cache()
    if json_output:
        print_json(data)
        return
    table = Table(title="Models")
    table.add_column("id")
    table.add_column("owned_by")
    for item in data.get("models", []):
        table.add_row(str(item.get("id", "")), str(item.get("owned_by", "")))
    console.print(table)


@app.command("cache")
def cache_models(json_output: Annotated[bool, typer.Option("--json")] = False) -> None:
    data = fetch_models()
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    result = {"cache_path": str(path), "count": len(data["models"])}
    if json_output:
        print_json(result)
    else:
        console.print(f"Cached {result['count']} models at {path}")


def fetch_models() -> dict[str, Any]:
    try:
        response = get_client().models.list()
    except Exception as exc:  # noqa: BLE001
        raise ApiError(f"Could not list models: {exc}") from exc
    models = [
        item.model_dump() if hasattr(item, "model_dump") else {"id": str(item)}
        for item in getattr(response, "data", [])
    ]
    return {"cached_at": datetime.now(timezone.utc).isoformat(), "models": models}


def load_model_cache() -> dict[str, Any]:
    try:
        return cast(dict[str, Any], json.loads(cache_path().read_text(encoding="utf-8")))
    except OSError as exc:
        raise ApiError(f"Could not read model cache. Run `oai-cli models cache`: {exc}") from exc


def cache_path() -> Path:
    return Path(dirs().user_cache_dir) / "models.json"
