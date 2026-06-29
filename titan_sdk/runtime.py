import socket
from datetime import datetime, timezone


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def uptime_seconds(started_at):
    try:
        started = datetime.fromisoformat(started_at)
        return int((datetime.now(timezone.utc) - started).total_seconds())
    except Exception:
        return 0


def get_hostname():
    return socket.gethostname()
