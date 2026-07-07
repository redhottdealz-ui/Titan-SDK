# Titan SDK v1.5.1 — Unified Heartbeat Framework

## Repository
Titan SDK

## Purpose
Adds a standardized heartbeat payload that every Titan service can use to report subsystem health consistently.

## New module
- `titan_sdk/heartbeat.py`

## Updated files
- `titan_sdk/client.py`
- `titan_sdk/__init__.py`
- `titan_sdk/version.py`
- `pyproject.toml`

## New SDK capabilities
- `TitanClient.set_heartbeat_component(name, status, message, **fields)`
- `TitanClient.clear_heartbeat_component(name)`
- `TitanClient.set_heartbeat_compatibility(**fields)`
- `TitanClient.unified_heartbeat_payload(...)`
- `TitanClient.unified_heartbeat(...)`

## Protocol
`titan_sdk_unified_heartbeat_v1`

## Environment variables
New required variables: **none**.

Uses existing:
- `TITAN_OS_URL` or `TITAN_OS_BASE_URL`
- `TITAN_OS_API_KEY`

## Commit message
`Add Titan SDK Unified Heartbeat Framework v1.5.1`

## Notes
The unified heartbeat uses the existing `/api/heartbeat` endpoint, so services do not need new network configuration.
