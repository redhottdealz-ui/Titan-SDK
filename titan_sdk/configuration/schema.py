from __future__ import annotations

from typing import Any, Dict, Iterable, List

SUPPORTED_FIELD_TYPES = {
    "text", "textarea", "boolean", "integer", "number", "select", "multi_select",
    "time", "timezone", "discord_channel", "discord_role", "discord_user", "notification_toggle",
}


def normalize_schema(product_key: str, version: str, sections: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    normalized: List[Dict[str, Any]] = []
    field_keys = set()
    for section in sections:
        section_copy = dict(section)
        fields = []
        for raw in section.get("fields") or []:
            field = dict(raw)
            key = str(field.get("key") or "").strip()
            field_type = str(field.get("field_type") or field.get("type") or "").strip().lower()
            if not key:
                raise ValueError("Configuration field key is required.")
            if key in field_keys:
                raise ValueError(f"Duplicate configuration field key: {key}")
            if field_type not in SUPPORTED_FIELD_TYPES:
                raise ValueError(f"Unsupported configuration field type: {field_type}")
            field_keys.add(key)
            field["key"] = key
            field["field_type"] = field_type
            field.pop("type", None)
            fields.append(field)
        section_copy["fields"] = fields
        normalized.append(section_copy)
    return {"product_key": str(product_key), "version": str(version), "sections": normalized}
