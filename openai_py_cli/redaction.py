"""Local sensitive-data redaction."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionResult:
    text: str
    findings: dict[str, int]

    @property
    def changed(self) -> bool:
        return self.text != ""


PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "private_key",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.S,
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
    ("openai_key", re.compile(r"(?<!\w)sk-[A-Za-z0-9_\-]*"), "[REDACTED_OPENAI_KEY]"),
    (
        "github_token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
        "[REDACTED_GITHUB_TOKEN]",
    ),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_\-]+?\.[A-Za-z0-9_\-]+?\.[A-Za-z0-9_\-]+\b"),
        "[REDACTED_JWT]",
    ),
    (
        "bearer",
        re.compile(r"\bBearer\s+[A-Za-z0-9._\-~+/=]{12,}\b", re.I),
        "Bearer [REDACTED_TOKEN]",
    ),
    (
        "cookie",
        re.compile(r"(?i)\b(cookie|set-cookie):\s*[^\n\r]+"),
        r"\1: [REDACTED_COOKIE]",
    ),
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    ("phone", re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{8,}\d)(?!\w)"), "[REDACTED_PHONE]"),
    (
        "url_query_token",
        re.compile(r"([?&](?:token|api_key|key|secret|access_token)=)[^&\s]+", re.I),
        r"\1[REDACTED]",
    ),
    (
        "generic_api_key",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,}['\"]?"
        ),
        r"\1=[REDACTED_SECRET]",
    ),
)


def redact_text(text: str) -> RedactionResult:
    findings: dict[str, int] = {}
    redacted = text
    for name, pattern, replacement in PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        if count:
            findings[name] = count
    return RedactionResult(text=redacted, findings=findings)


def contains_secrets(text: str) -> bool:
    return any(pattern.search(text) for _, pattern, _ in PATTERNS)
