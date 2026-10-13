"""Exception hierarchy. Every error raised on purpose derives from RagStudioError."""
from __future__ import annotations


class RagStudioError(Exception):
    """Base class: the CLI turns it into `{"ok": false, "error": ...}`."""


class ConfigError(RagStudioError):
    pass


class ValidationError(RagStudioError):
    pass


class NotFoundError(RagStudioError):
    pass


class LeakageError(ValidationError):
    """A runbook would mix documents or questions from different corpus splits."""


class BudgetExceeded(RagStudioError):
    pass


class ProviderError(RagStudioError):
    def __init__(self, message: str, status_code: int | None = None, retry_after: float | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after

    @property
    def retryable(self) -> bool:
        return self.status_code in (408, 409, 429) or (self.status_code is not None and self.status_code >= 500)
