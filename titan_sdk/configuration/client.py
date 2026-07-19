from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class ConfigurationClient:
    def __init__(self, base_url: str, service_token: str, timeout: int = 15, session: Optional[requests.Session] = None) -> None:
        self.base_url = str(base_url).rstrip("/")
        self.service_token = str(service_token)
        self.timeout = max(1, int(timeout))
        self.session = session or requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.service_token}", "Content-Type": "application/json", "User-Agent": "Titan-SDK-Configuration/1.8.0"}

    def fetch(self, product_key: str, guild_id: str, profile: str = "production") -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/api/configuration/{guild_id}/{product_key}", params={"profile": profile}, headers=self._headers(), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def acknowledge(self, product_key: str, guild_id: str, version: int, status: str = "applied", profile: str = "production", runtime_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self.session.post(f"{self.base_url}/api/configuration-sync/report/{guild_id}/{product_key}", json={"profile": profile, "configuration_version": int(version), "status": status, "runtime_metadata": runtime_metadata or {}}, headers=self._headers(), timeout=self.timeout)
        response.raise_for_status()
        return response.json()
