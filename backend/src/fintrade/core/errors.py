"""Typed error hierarchy (ENGINEERING.md section 8). Never raise bare Exception."""


class FintradeError(Exception):
    """Base class for every error raised by our code."""


class InvalidInputError(FintradeError):
    """Input failed validation at a boundary."""


class ConfigError(FintradeError):
    """Configuration is missing or invalid."""


class DataError(FintradeError):
    """Market or reference data is missing, malformed or inconsistent."""


class StaleDataError(DataError):
    """Data is older than allowed. Callers must fail closed (AGENTS.md section 2)."""


class BrokerError(FintradeError):
    """A broker call failed or returned something unexpected."""


class RuleViolation(FintradeError):  # noqa: N818 - a violation is the domain term
    """An action would break a rule or guardrail. Carries a stable code for logs and tests."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
