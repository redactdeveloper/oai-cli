"""Rich output helpers."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel

from .runtime import options

console = Console()
err_console = Console(stderr=True)


def print_json(data: Any) -> None:
    console.print_json(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def print_error(message: str) -> None:
    if options.plain:
        err_console.print(f"Error: {message}")
        return
    if options.json_output:
        err_console.print_json(json.dumps({"error": message}, ensure_ascii=False))
        return
    err_console.print(Panel(message, title="[red]Error[/red]", border_style="red"))


def print_warning(message: str) -> None:
    if options.plain:
        err_console.print(f"Warning: {message}")
        return
    err_console.print(f"[yellow]Warning:[/yellow] {message}")
