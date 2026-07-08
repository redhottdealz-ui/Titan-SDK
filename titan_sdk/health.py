"""Titan SDK health scoring helpers."""
from __future__ import annotations


def score_from_failures(failures: int, total: int) -> int:
    total = max(0, int(total or 0))
    failures = max(0, int(failures or 0))
    if total <= 0:
        return 100
    return max(0, min(100, round(((total - failures) / total) * 100)))


def reliability_score(*, heartbeats_sent=0, failed_posts=0, successful_posts=0, command_failures=0, command_total=0, reliability_failures=0, reliability_successes=0):
    post_score = score_from_failures(failed_posts, int(successful_posts or 0) + int(failed_posts or 0))
    command_score = score_from_failures(command_failures, command_total)
    reliability = score_from_failures(reliability_failures, int(reliability_successes or 0) + int(reliability_failures or 0))
    heartbeat_score = 100 if int(heartbeats_sent or 0) >= 0 else 0
    return {
        "overall": round((post_score + command_score + reliability + heartbeat_score) / 4),
        "posts": post_score,
        "commands": command_score,
        "reliability": reliability,
        "heartbeats": heartbeat_score,
    }
