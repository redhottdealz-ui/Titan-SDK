from __future__ import annotations

import re
from typing import Any, Dict, List

DISCORD_ID = re.compile(r"^\d{15,22}$")


def validate_snapshot(schema: Dict[str, Any], configuration: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, str]] = []
    for section in schema.get("sections") or []:
        for field in section.get("fields") or []:
            key = field.get("key")
            value = configuration.get(key, field.get("default"))
            empty = value is None or value == "" or value == []
            if field.get("required") and empty:
                issues.append({"field": key, "code": "required", "message": f"{field.get('label') or key} is required."})
                continue
            if empty:
                continue
            if field.get("field_type") in {"discord_channel", "discord_role", "discord_user"} and not DISCORD_ID.match(str(value)):
                issues.append({"field": key, "code": "discord_id", "message": f"{field.get('label') or key} must be a valid Discord ID."})
    return {"valid": not issues, "issues": issues}
