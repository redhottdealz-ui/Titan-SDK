"""Titan SDK Capability Registry.

The Capability Registry gives every Titan service a shared language for
advertising what it can do. Services may continue passing simple string
capability keys, while the SDK enriches those keys into metadata that Titan
Control Center can render consistently.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping


CAPABILITY_SCHEMA_VERSION = "1.0"

CAPABILITY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "registration": {"label": "Registration", "category": "platform", "icon": "🧾", "description": "Registers with Titan Control Center."},
    "heartbeat": {"label": "Heartbeat", "category": "platform", "icon": "💓", "description": "Reports recurring service heartbeat status."},
    "heartbeats": {"label": "Heartbeats", "category": "platform", "icon": "💓", "description": "Reports recurring service heartbeat status."},
    "status": {"label": "Status", "category": "platform", "icon": "📡", "description": "Publishes service status updates."},
    "metrics": {"label": "Metrics", "category": "observability", "icon": "📊", "description": "Publishes service metrics."},
    "events": {"label": "Events", "category": "observability", "icon": "🧭", "description": "Publishes platform events."},
    "platform_events": {"label": "Platform Events", "category": "observability", "icon": "🧭", "description": "Publishes typed Titan platform events."},
    "diagnostics": {"label": "Diagnostics", "category": "observability", "icon": "🩺", "description": "Supports diagnostics reporting."},
    "operations": {"label": "Operations", "category": "platform", "icon": "🛠️", "description": "Exposes Titan operations metadata."},
    "lifecycle": {"label": "Lifecycle", "category": "platform", "icon": "🔁", "description": "Reports start/stop lifecycle events."},
    "jobs": {"label": "Jobs", "category": "automation", "icon": "📦", "description": "Tracks job execution status."},

    "discord": {"label": "Discord", "category": "integration", "icon": "💬", "description": "Connects to Discord."},
    "reviews": {"label": "Reviews", "category": "community", "icon": "📋", "description": "Runs member review workflows."},
    "hiatus": {"label": "Hiatus", "category": "community", "icon": "🏝️", "description": "Manages member hiatus workflows."},
    "contests": {"label": "Contests", "category": "community", "icon": "🏆", "description": "Supports contests or draws."},
    "scheduler": {"label": "Scheduler", "category": "automation", "icon": "⏱️", "description": "Runs scheduled automation."},
    "battle_scheduler": {"label": "Battle Scheduler", "category": "battle", "icon": "⚔️", "description": "Schedules and manages battle events."},
    "draws": {"label": "Draws", "category": "battle", "icon": "🎲", "description": "Runs random draws and winner pools."},
    "voice_automation": {"label": "Voice Automation", "category": "battle", "icon": "🔊", "description": "Supports Discord voice automation."},
    "flyers": {"label": "Flyers", "category": "battle", "icon": "🖼️", "description": "Supports flyer workflows."},

    "applications": {"label": "Applications", "category": "family", "icon": "📝", "description": "Manages intake applications."},
    "intake": {"label": "Intake", "category": "family", "icon": "👥", "description": "Supports review and intake workflows."},
    "voting": {"label": "Voting", "category": "family", "icon": "🗳️", "description": "Supports supervisor/final voting workflows."},
    "reposts": {"label": "Reposts", "category": "family", "icon": "🔁", "description": "Supports reminder or repost workflows."},

    "tiktok_live": {"label": "TikTok LIVE", "category": "creator", "icon": "🎥", "description": "Tracks TikTok LIVE status."},
    "tiktok_tracking": {"label": "TikTok Tracking", "category": "creator", "icon": "📈", "description": "Tracks TikTok accounts and reports."},
    "marketing": {"label": "Marketing", "category": "marketing", "icon": "📣", "description": "Supports marketing workflows."},
    "product_posting": {"label": "Product Posting", "category": "marketing", "icon": "🛍️", "description": "Posts products to channels or social platforms."},
    "video_generation": {"label": "Video Generation", "category": "marketing", "icon": "🎬", "description": "Generates marketing videos."},

    "ai": {"label": "AI", "category": "titan_ai", "icon": "🤖", "description": "Uses Titan AI capabilities."},
    "titan_ai": {"label": "Titan AI", "category": "titan_ai", "icon": "🤖", "description": "Integrates with Titan AI service."},
    "personality_registry": {"label": "Personality Registry", "category": "titan_ai", "icon": "🧬", "description": "Syncs Titan AI personality registry."},
    "memory": {"label": "Memory", "category": "titan_ai", "icon": "🧠", "description": "Supports AI memory."},
    "prompt_library": {"label": "Prompt Library", "category": "titan_ai", "icon": "📚", "description": "Supports saved prompts."},
}


DEFAULT_CAPABILITIES = [
    "registration",
    "heartbeat",
    "status",
    "metrics",
    "events",
    "diagnostics",
    "operations",
    "lifecycle",
    "jobs",
]


def capability_key(value: Any) -> str:
    if isinstance(value, Mapping):
        raw = value.get("key") or value.get("id") or value.get("name") or value.get("label")
    else:
        raw = value
    key = str(raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    return key


def _title_from_key(key: str) -> str:
    return str(key or "").replace("_", " ").title()


def capability_definition(key: str, override: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    base = dict(CAPABILITY_REGISTRY.get(key, {}))
    if not base:
        base = {
            "label": _title_from_key(key),
            "category": "custom",
            "icon": "🔹",
            "description": f"Custom capability: {_title_from_key(key)}.",
        }
    if override:
        base.update({k: v for k, v in dict(override).items() if v is not None})
    base["key"] = key
    return base


def normalize_capabilities(capabilities: Iterable[Any] | None, include_defaults: bool = True) -> List[str]:
    keys: List[str] = []
    source = list(capabilities or [])
    if include_defaults:
        source = DEFAULT_CAPABILITIES + source
    for item in source:
        key = capability_key(item)
        if key and key not in keys:
            keys.append(key)
    return keys


def build_capability_payload(capabilities: Iterable[Any] | None, include_defaults: bool = True) -> Dict[str, Any]:
    keys = normalize_capabilities(capabilities, include_defaults=include_defaults)
    items = []
    by_category: Dict[str, List[str]] = {}
    for original in keys:
        items.append(capability_definition(original))
        category = items[-1].get("category", "custom")
        by_category.setdefault(category, []).append(original)
    return {
        "schema": "titan_capability_registry",
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "count": len(keys),
        "keys": keys,
        "items": items,
        "categories": by_category,
    }


def capability_summary(capabilities: Iterable[Any] | None, include_defaults: bool = True) -> Dict[str, Any]:
    payload = build_capability_payload(capabilities, include_defaults=include_defaults)
    return {
        "schema_version": payload["schema_version"],
        "count": payload["count"],
        "keys": payload["keys"],
        "categories": {key: len(value) for key, value in payload["categories"].items()},
    }
