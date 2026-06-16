from dataclasses import dataclass
from typing import Literal

SmsSendMode = Literal["text", "pattern"]


@dataclass(frozen=True)
class SmsPayload:
    """Outbound SMS — plain text or provider pattern/template."""

    mode: SmsSendMode
    text: str | None = None
    pattern_id: str | None = None
    pattern_params: dict[str, str] | None = None
    pattern_slots: tuple[str, ...] | None = None
