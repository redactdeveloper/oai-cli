"""Environment diagnostics."""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table

from ..client import get_client, get_client_context
from ..config import config_path, default_log_path, load_config
from ..output import console, print_json


def doctor(
    check_api: Annotated[bool, typer.Option("--check-api")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    cfg = load_config()
    context = get_client_context(cfg)
    checks: list[dict[str, Any]] = []
    _add(checks, "Python", sys.version.split()[0], sys.version_info >= (3, 10))
    _add(checks, "oai-cli", _version("oai-cli"), True)
    _add(checks, "openai SDK", _version("openai"), True)
    _add(checks, "Active profile", context.profile_name, True)
    _add(
        checks,
        f"API key env {context.api_key_env}",
        "set" if context.api_key_present else "missing",
        context.api_key_present,
    )
    _add(checks, "Base URL", context.profile.base_url or "default", True)
    _add_path(checks, "Config directory", config_path().parent)
    _add_path(checks, "Log directory", (cfg.log_path or default_log_path()).parent)

    if check_api:
        try:
            client = get_client(cfg)
            response = client.responses.create(
                model=context.profile.default_model,
                input="Reply with OK.",
                max_output_tokens=16,
            )
            _add(checks, "API probe", getattr(response, "output_text", "ok"), True)
        except Exception as exc:  # noqa: BLE001
            _add(checks, "API probe", str(exc), False)

    if json_output:
        print_json(checks)
        return
    table = Table(title="oai-cli doctor")
    table.add_column("Status")
    table.add_column("Check")
    table.add_column("Details")
    for item in checks:
        if item["ok"]:
            icon = "[green]OK[/green]"
        elif item["warning"]:
            icon = "[yellow]Warning[/yellow]"
        else:
            icon = "[red]Error[/red]"
        details = item["details"]
        table.add_row(icon, item["name"], details)
    console.print(table)


def _add(
    checks: list[dict[str, Any]],
    name: str,
    details: str,
    ok: bool,
    warning: bool = False,
) -> None:
    checks.append({"name": name, "details": details, "ok": ok, "warning": warning})


def _add_path(checks: list[dict[str, Any]], name: str, path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        writable = path.exists() and path.is_dir()
        _add(checks, name, str(path), writable)
    except OSError as exc:
        _add(checks, name, f"{path}: {exc}", False)


def _version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"
