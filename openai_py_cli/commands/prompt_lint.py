"""Local prompt quality checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from ..output import console, print_json
from ..pricing import estimate_tokens
from ..redaction import contains_secrets


@dataclass(frozen=True)
class PromptLintResult:
    score: int
    warnings: list[str]
    suggestions: list[str]
    improved_prompt: str

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "improved_prompt": self.improved_prompt,
        }


VAGUE_WORDS = (
    "нормально",
    "красиво",
    "быстро",
    "лучше",
    "good",
    "nice",
    "better",
    "fast",
    "simple",
)
TASK_HINTS = (
    "create",
    "write",
    "explain",
    "summarize",
    "compare",
    "extract",
    "classify",
    "fix",
    "review",
    "сделай",
    "создай",
    "напиши",
    "объясни",
    "исправь",
    "проверь",
)
FORMAT_HINTS = (
    "format",
    "json",
    "markdown",
    "table",
    "list",
    "schema",
    "формат",
    "таблица",
    "список",
)
CONSTRAINT_HINTS = (
    "do not",
    "don't",
    "avoid",
    "must",
    "limit",
    "only",
    "never",
    "не ",
    "нельзя",
    "только",
    "без ",
)


def prompt_lint(
    path: Annotated[
        Path | None,
        typer.Argument(help="Prompt file. Reads stdin when omitted."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    text = path.read_text(encoding="utf-8") if path else typer.get_text_stream("stdin").read()
    result = analyze_prompt(text)
    if json_output:
        print_json(result.to_dict())
        return
    table = Table(title=f"Prompt lint score: {result.score}/100")
    table.add_column("Type")
    table.add_column("Message")
    for warning in result.warnings:
        table.add_row("[yellow]Warning[/yellow]", warning)
    for suggestion in result.suggestions:
        table.add_row("[cyan]Suggestion[/cyan]", suggestion)
    console.print(table)
    console.print(Panel(result.improved_prompt, title="Improved prompt draft"))


def analyze_prompt(prompt: str) -> PromptLintResult:
    normalized = prompt.strip()
    lower = normalized.lower()
    warnings: list[str] = []
    suggestions: list[str] = []

    if not normalized:
        warnings.append("Prompt is empty.")
        suggestions.append("Add a concrete task, context, constraints, and expected output format.")
        return PromptLintResult(0, warnings, suggestions, _draft_prompt(normalized))

    if not _has_any(lower, TASK_HINTS):
        warnings.append("No clear task was detected.")
        suggestions.append(
            "Start with an explicit action: explain, extract, compare, write, or review."
        )

    if not _has_any(lower, FORMAT_HINTS):
        warnings.append("Expected answer format is not specified.")
        suggestions.append(
            "State the output format, for example Markdown bullets, a table, or JSON."
        )

    if not _has_any(lower, CONSTRAINT_HINTS):
        warnings.append("No constraints or boundaries were detected.")
        suggestions.append(
            "Add constraints such as length, audience, exclusions, or acceptance criteria."
        )

    vague = sorted({word for word in VAGUE_WORDS if re.search(rf"\b{re.escape(word)}\b", lower)})
    if vague:
        warnings.append(f"Vague words need measurable criteria: {', '.join(vague)}.")
        suggestions.append("Replace subjective words with observable criteria.")

    if contains_secrets(normalized):
        warnings.append("Prompt appears to contain secrets.")
        suggestions.append("Redact secrets before sending this prompt to an API.")

    if "json" in lower and not _mentions_schema(lower):
        warnings.append("Prompt asks for JSON but does not provide a schema.")
        suggestions.append("Add a JSON Schema or an exact example object with required fields.")

    if _has_conflicting_instructions(lower):
        warnings.append("Potentially conflicting instructions were detected.")
        suggestions.append("Resolve contradictions before sending the prompt.")

    if estimate_tokens(normalized) > 3000:
        warnings.append(
            "Prompt is long enough to hide requirements or exceed smaller context budgets."
        )
        suggestions.append(
            "Move reference material to a separate section and summarize requirements first."
        )

    hidden_requirement_count = len(
        re.findall(r"\b(must|should|required|never|always|должен|нужно|нельзя)\b", lower)
    )
    if hidden_requirement_count >= 10:
        warnings.append("Many requirements were detected; some may be easy to miss.")
        suggestions.append("Group requirements into numbered acceptance criteria.")

    score = max(0, 100 - len(warnings) * 12 - max(0, hidden_requirement_count - 6) * 2)
    return PromptLintResult(score, warnings, suggestions, _draft_prompt(normalized))


def _draft_prompt(prompt: str) -> str:
    base = prompt or "[Describe the task here]"
    return (
        "Task:\n"
        f"{base}\n\n"
        "Context:\n"
        "[Add relevant background and inputs.]\n\n"
        "Constraints:\n"
        "- [Add measurable limits, exclusions, and quality criteria.]\n\n"
        "Output format:\n"
        "- [Specify Markdown, table columns, JSON schema, or exact sections.]\n\n"
        "Success criteria:\n"
        "- [Describe how the answer will be judged.]"
    )


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _mentions_schema(text: str) -> bool:
    return "schema" in text or "required" in text or "properties" in text or "пример json" in text


def _has_conflicting_instructions(text: str) -> bool:
    pairs = (
        ("only json", "markdown"),
        ("только json", "markdown"),
        ("do not explain", "explain"),
        ("не объясняй", "объясни"),
        ("no code", "code"),
        ("без кода", "код"),
    )
    return any(left in text and right in text.replace(left, "") for left, right in pairs)
