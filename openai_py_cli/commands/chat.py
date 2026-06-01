"""Interactive chat REPL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel

from ..client import get_client_context
from ..config import dirs, load_config
from ..errors import ApiError
from ..output import console, print_warning
from .ask import _stream_response, build_responses_payload


def chat(
    model: Annotated[str | None, typer.Option("--model", "-m")] = None,
    system: Annotated[str | None, typer.Option("--system")] = None,
) -> None:
    cfg = load_config()
    context = get_client_context(cfg)
    selected_model = model or context.profile.default_model
    messages: list[dict[str, str]] = []
    console.print(Panel("Type /help for commands. Ctrl+D exits.", title="oai-cli chat"))
    while True:
        try:
            user_input = _read_repl_input()
        except EOFError:
            console.print()
            return
        except KeyboardInterrupt:
            console.print("\nInterrupted. Type /exit to quit.")
            continue
        if not user_input.strip():
            continue
        if user_input.startswith("/"):
            selected_model, system, messages = _handle_command(
                user_input,
                selected_model,
                system,
                messages,
            )
            if user_input.strip() == "/exit":
                return
            continue
        messages.append({"role": "user", "content": user_input})
        prompt = _conversation_prompt(messages)
        payload = build_responses_payload(prompt=prompt, model=selected_model, system=system)
        try:
            from ..client import get_client

            output = _stream_response(get_client(cfg), payload)
        except Exception as exc:  # noqa: BLE001
            raise ApiError(f"Chat request failed: {exc}") from exc
        messages.append({"role": "assistant", "content": output})


def _read_repl_input() -> str:
    first = input("oai-cli> ")
    if first.strip() != '"""':
        return first
    lines: list[str] = []
    while True:
        line = input("... ")
        if line.strip() == '"""':
            return "\n".join(lines)
        lines.append(line)


def _handle_command(
    command: str,
    model: str,
    system: str | None,
    messages: list[dict[str, str]],
) -> tuple[str, str | None, list[dict[str, str]]]:
    parts = command.strip().split(maxsplit=1)
    name = parts[0]
    value = parts[1] if len(parts) > 1 else ""
    if name == "/help":
        console.print(
            "/exit /clear /model <name> /system <text> /save <name> /load <name> /history"
        )
    elif name == "/exit":
        return model, system, messages
    elif name == "/clear":
        messages = []
        console.print("History cleared.")
    elif name == "/model" and value:
        model = value
        console.print(f"Model: {model}")
    elif name == "/system":
        system = value or None
        console.print("System prompt updated.")
    elif name == "/save" and value:
        _session_path(value).write_text(json.dumps(messages, indent=2), encoding="utf-8")
        console.print(f"Saved session: {value}")
    elif name == "/load" and value:
        messages = json.loads(_session_path(value).read_text(encoding="utf-8"))
        console.print(f"Loaded session: {value}")
    elif name == "/history":
        for item in messages:
            console.print(Panel(item["content"], title=item["role"]))
    else:
        print_warning("Unknown command. Type /help.")
    return model, system, messages


def _conversation_prompt(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(f"{item['role'].upper()}:\n{item['content']}" for item in messages)


def _session_path(name: str) -> Path:
    safe_name = "".join(ch for ch in name if ch.isalnum() or ch in {"-", "_"}).strip()
    if not safe_name:
        raise typer.BadParameter("Session name is empty.")
    path = Path(dirs().user_data_dir) / "chat_sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{safe_name}.json"
