from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class ConfigurationSnapshot:
    product_key: str
    guild_id: str
    profile: str
    version: int
    configuration: Dict[str, Any]
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConfigurationApplyResult:
    status: str
    applied_version: int
    message: str = ""
    runtime_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
