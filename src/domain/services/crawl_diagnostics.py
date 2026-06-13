from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CrawlDiagnostics:
    """Per-run event log explaining what the crawler did and why listings were skipped."""

    events: list[dict] = field(default_factory=list)
    max_events: int = 250

    def add(self, level: str, message: str, **extra) -> None:
        if len(self.events) >= self.max_events:
            return
        self.events.append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "message": message,
                **{k: v for k, v in extra.items() if v is not None},
            }
        )

    def to_list(self) -> list[dict]:
        return list(self.events)
