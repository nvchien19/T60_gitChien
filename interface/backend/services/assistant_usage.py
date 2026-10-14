"""Per-request API usage only: never store questions, evidence or credentials."""
from contextvars import ContextVar
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict


class AssistantUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_calls: int = 0
    measured: bool = True
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd_min: float | None = 0.0
    cost_usd_max: float | None = 0.0
    pricing_date: str = "2026-10-11"


@dataclass
class UsageMeter:
    attempts: int = 0
    receipts: list[tuple[str, dict]] = field(default_factory=list)

    def summary(self) -> AssistantUsage:
        result = AssistantUsage(api_calls=self.attempts, measured=len(self.receipts) == self.attempts)
        lower = 0.0
        known_price = result.measured
        for model, usage in self.receipts:
            count = lambda key: usage[key] if type(usage.get(key)) is int and usage[key] >= 0 else 0  # noqa: E731
            prompt, cached, output = count("prompt_tokens"), count("prompt_cache_hit_tokens"), count("completion_tokens")
            result.input_tokens += prompt
            result.cached_input_tokens += cached
            result.output_tokens += output
            result.total_tokens += prompt + output
            # Official prices per million tokens on pricing_date, off-peak/peak range.
            rates = (0.003, 0.15, 0.6) if model.startswith("deepseek-flash") else (
                (0.022, 0.66, 1.98) if model.startswith("deepseek-v4-pro") else None)
            if rates is None or "prompt_cache_hit_tokens" not in usage or cached > prompt:
                known_price = False
            else:
                lower += (cached * rates[0] + (prompt - cached) * rates[1] + output * rates[2]) / 1_000_000
        result.cost_usd_min = round(lower, 9) if known_price else None
        result.cost_usd_max = round(lower * 2, 9) if known_price else None
        return result


active_usage: ContextVar[UsageMeter | None] = ContextVar("assistant_usage", default=None)


def record_attempt() -> None:
    meter = active_usage.get()
    if meter is not None:
        meter.attempts += 1


def record_receipt(data: dict) -> None:
    meter = active_usage.get()
    usage = data.get("usage")
    if meter is not None and isinstance(usage, dict) and all(
        type(usage.get(key)) is int and usage[key] >= 0 for key in ("prompt_tokens", "completion_tokens")
    ):
        meter.receipts.append((str(data.get("model", "")), usage))
