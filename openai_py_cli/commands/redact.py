"""Redact sensitive data locally."""

from __future__ import annotations

from typing import Annotated

import typer

from ..output import console, print_json
from ..redaction import redact_text


def redact(
    text: Annotated[
        str | None,
        typer.Argument(help="Text to redact. Reads stdin when omitted."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print findings as JSON.")] = False,
) -> None:
    input_text = text if text is not None else typer.get_text_stream("stdin").read()
    result = redact_text(input_text)
    if json_output:
        print_json({"text": result.text, "findings": result.findings})
    else:
        console.print(result.text)
