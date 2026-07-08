# Titan SDK v1.6.1 — Reliability Framework & Fault-Tolerant Services

Release date: July 8, 2026

## Overview

Titan SDK v1.6.1 adds a reliability layer for Titan services so heartbeat, diagnostics, logging-adjacent telemetry, background tasks, scheduler jobs, and Discord slash commands can fail safely instead of hanging or terminating service threads.

This release is additive and backward compatible with Titan SDK v1.6.0.

## Added

- Fault-tolerant heartbeat loop protection.
- Safe diagnostics collection.
- Reliability event tracking.
- Command execution telemetry.
- Discord slash command safety decorator.
- Safe filesystem helpers for diagnostics and persistent storage checks.
- Reliability scoring helpers.
- Runtime reliability snapshots in diagnostics and heartbeat payloads.

## New SDK modules

- `titan_sdk/reliability.py`
- `titan_sdk/command_framework.py`
- `titan_sdk/safe_io.py`
- `titan_sdk/telemetry.py`
- `titan_sdk/health.py`

## New exports

- `safe_slash_command`
- `safe_task`
- `safe_background_task`
- `safe_scheduler`
- `safe_heartbeat`
- `ReliabilityMonitor`
- `ReliabilityEvent`
- `safe_exists`
- `safe_read_json`
- `safe_write_json`
- `safe_mkdir`
- `safe_touch`

## Reliability behavior

Heartbeat loops now catch and report exceptions instead of allowing heartbeat threads to die.

Diagnostics now degrade gracefully. If a diagnostics provider fails, the error is included in the diagnostics payload instead of crashing the heartbeat or status call.

Command telemetry can now track command starts, successes, failures, timeouts, duration, guild, and user metadata.

## Environment variables

New required variables: none.

Existing variables remain unchanged:

- `TITAN_OS_URL`
- `TITAN_OS_API_KEY`

## Deployment notes

1. Publish Titan SDK v1.6.1.
2. Services can safely update their requirements to:
   `git+https://github.com/redhottdealz-ui/Titan-SDK.git@v1.6.1`
3. Bot command wrappers can be adopted incrementally.

## Commit message

`Add Titan SDK Reliability Framework v1.6.1`
