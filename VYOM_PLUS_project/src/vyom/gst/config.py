"""Environment-driven configuration for the GST Intelligence Layer.

Nothing here hardcodes a secret. The Groq API key is held as a SecretStr so it
never appears in repr(), logs or API responses.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Mapping, Optional

from pydantic import SecretStr


# A current Groq production model with strict structured-output support
# (console.groq.com/docs/models and /docs/structured-outputs). Override with GROQ_MODEL;
# model availability and free-tier limits change, so check the Groq docs.
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
ROOT = Path(__file__).resolve().parents[3]


class ConfigError(ValueError):
    """Invalid configuration value (never includes secret values in the message)."""


def _load_dotenv() -> None:
    """Load VYOM_PLUS_project/.env if python-dotenv is installed; existing variables win."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env", override=False)


def _number(env: Mapping[str, str], name: str, default, cast, low, high):
    raw = env.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = cast(raw)
    except (TypeError, ValueError):
        raise ConfigError(f"{name} must be a number between {low} and {high}")
    if not low <= value <= high:
        raise ConfigError(f"{name} must be between {low} and {high}")
    return value


@dataclass(frozen=True)
class GroqSettings:
    api_key: Optional[SecretStr]
    model: str = DEFAULT_GROQ_MODEL
    temperature: float = 0.0
    max_tokens: int = 2048
    timeout: float = 30.0
    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 20.0
    structured_method: str = "json_schema"

    @property
    def configured(self) -> bool:
        return self.api_key is not None and bool(self.api_key.get_secret_value().strip())

    def public(self) -> dict:
        """Settings safe to log or return (no key)."""
        return {"model": self.model, "temperature": self.temperature, "max_tokens": self.max_tokens,
                "timeout": self.timeout, "max_retries": self.max_retries, "api_key_configured": self.configured,
                "structured_method": self.structured_method}


@dataclass(frozen=True)
class AnalysisLimits:
    max_upload_bytes: int = 10 * 1024 * 1024
    max_json_bytes: int = 5 * 1024 * 1024
    max_rows: int = 5000
    max_sheets: int = 20
    max_columns: int = 300
    max_cell_chars: int = 2000
    llm_max_discrepancy_groups: int = 40
    llm_max_context_chars: int = 30000
    analysis_deadline_seconds: float = 120.0


@dataclass(frozen=True)
class Settings:
    groq: GroqSettings
    limits: AnalysisLimits = field(default_factory=AnalysisLimits)
    rules_path: Optional[Path] = None


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    if env is None:
        _load_dotenv()
        env = os.environ
    key = (env.get("GROQ_API_KEY") or "").strip()
    method = (env.get("GROQ_STRUCTURED_METHOD") or "json_schema").strip()
    if method not in ("json_schema", "function_calling", "json_mode"):
        raise ConfigError("GROQ_STRUCTURED_METHOD must be json_schema, function_calling or json_mode")
    groq = GroqSettings(
        api_key=SecretStr(key) if key else None,
        model=(env.get("GROQ_MODEL") or DEFAULT_GROQ_MODEL).strip(),
        temperature=_number(env, "GROQ_TEMPERATURE", 0.0, float, 0.0, 1.0),
        max_tokens=_number(env, "GROQ_MAX_TOKENS", 2048, int, 256, 32768),
        timeout=_number(env, "GROQ_TIMEOUT", 30.0, float, 1.0, 300.0),
        max_retries=_number(env, "GROQ_MAX_RETRIES", 3, int, 0, 5),
        backoff_base=_number(env, "GROQ_BACKOFF_BASE", 1.0, float, 0.0, 30.0),
        backoff_max=_number(env, "GROQ_BACKOFF_MAX", 20.0, float, 0.0, 120.0),
        structured_method=method,
    )
    limits = AnalysisLimits(
        max_upload_bytes=_number(env, "GST_MAX_UPLOAD_BYTES", AnalysisLimits.max_upload_bytes, int, 1024, 50 * 1024 * 1024),
        max_json_bytes=_number(env, "GST_MAX_JSON_BYTES", AnalysisLimits.max_json_bytes, int, 1024, 50 * 1024 * 1024),
        max_rows=_number(env, "GST_MAX_ROWS", AnalysisLimits.max_rows, int, 1, 100000),
        max_sheets=_number(env, "GST_MAX_SHEETS", AnalysisLimits.max_sheets, int, 1, 200),
        analysis_deadline_seconds=_number(env, "GST_ANALYSIS_DEADLINE_SECONDS",
                                          AnalysisLimits.analysis_deadline_seconds, float, 5.0, 900.0),
    )
    rules = (env.get("GST_RULES_PATH") or "").strip()
    return Settings(groq=groq, limits=limits, rules_path=Path(rules) if rules else None)
