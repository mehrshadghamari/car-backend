from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SmsProviderCredentials:
    driver: str
    slug: str
    config: dict[str, Any]

    def get(self, key: str, default: str = "") -> str:
        value = self.config.get(key, default)
        return str(value) if value is not None else default

    @property
    def api_key(self) -> str:
        return self.get("api_key")
