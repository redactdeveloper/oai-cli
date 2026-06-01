"""Application exceptions and exit codes."""

from __future__ import annotations

from .redaction import redact_text

EXIT_GENERAL = 1
EXIT_CONFIG = 2
EXIT_API = 3
EXIT_VALIDATION = 4


class OpenAIPyCliError(Exception):
    """Base class for expected user-facing errors."""

    exit_code = EXIT_GENERAL


class ConfigError(OpenAIPyCliError):
    """Configuration is missing or invalid."""

    exit_code = EXIT_CONFIG


class MissingApiKeyError(ConfigError):
    """The configured API key environment variable is not set."""


class ApiError(OpenAIPyCliError):
    """OpenAI API request failed."""

    exit_code = EXIT_API

    def __init__(self, message: str) -> None:
        super().__init__(redact_text(message).text)


class ValidationError(OpenAIPyCliError):
    """Local input validation failed."""

    exit_code = EXIT_VALIDATION
