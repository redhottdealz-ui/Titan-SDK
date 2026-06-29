import socket
from datetime import datetime, timezone


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_hostname():
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def uptime_seconds(started_at):
    parsed = parse_iso(started_at)
    if not parsed:
        return 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0, round((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds(), 2))


def runtime_identity():
    return {
        "hostname": get_hostname(),
        "timestamp": utc_now_iso(),
    }
