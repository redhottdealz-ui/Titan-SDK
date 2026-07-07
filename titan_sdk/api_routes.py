"""Canonical Titan API route definitions.

The SDK owns these path constants so Titan services and Titan Control Center
can stay aligned. Route strings should not be duplicated in bots/workers.
"""

API_PREFIX = "/api"

REGISTER_SERVICE = f"{API_PREFIX}/register-service"
STATUS = f"{API_PREFIX}/status"
HEARTBEAT = f"{API_PREFIX}/heartbeat"
EVENT = f"{API_PREFIX}/event"
EVENTS = f"{API_PREFIX}/events"
METRICS = f"{API_PREFIX}/metrics"
SERVICES = f"{API_PREFIX}/services"

# Titan AI personality registry routes.
# Canonical public API routes include /api. Control Center keeps non-/api
# compatibility aliases during migration.
PERSONALITY_REGISTRY = f"{API_PREFIX}/titan-ai/personality-registry"
PERSONALITY_REGISTRY_VERSION = f"{API_PREFIX}/titan-ai/personality-registry/version"
PERSONALITY_REGISTRY_PUSH_SYNC = f"{API_PREFIX}/titan-ai/personality-registry/push-sync"
PERSONALITY_REGISTRY_STATUS = f"{API_PREFIX}/titan-ai/personality-registry/status"


def join_url(base_url: str, route: str) -> str:
    """Join a Titan base URL and a canonical route."""
    base = str(base_url or "").rstrip("/")
    path = str(route or "")
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}" if base else ""


TITAN_API_ROUTES = {
    "register_service": REGISTER_SERVICE,
    "status": STATUS,
    "heartbeat": HEARTBEAT,
    "event": EVENT,
    "events": EVENTS,
    "metrics": METRICS,
    "services": SERVICES,
    "personality_registry": PERSONALITY_REGISTRY,
    "personality_registry_version": PERSONALITY_REGISTRY_VERSION,
    "personality_registry_push_sync": PERSONALITY_REGISTRY_PUSH_SYNC,
    "personality_registry_status": PERSONALITY_REGISTRY_STATUS,
}
