# Titan SDK v1.6.0 — Capability Registry

## Release Date
July 7, 2026

## Repository
Titan SDK

## Summary
Adds a shared Capability Registry to Titan SDK so every Titan service can advertise what it can do using one standardized schema.

## Files to replace
- `README.md`
- `pyproject.toml`
- `titan_sdk/__init__.py`
- `titan_sdk/client.py`
- `titan_sdk/pyproject.toml`
- `titan_sdk/version.py`

## New files
- `titan_sdk/capabilities.py`
- `TITAN_SDK_CAPABILITY_REGISTRY_V1_6_0_2026_07_07.md`

## New required environment variables
None.

## Database changes
None.

## Commit message
`Add Titan SDK Capability Registry v1.6.0`

## Notes
The SDK remains backward-compatible with existing string-based `capabilities=[...]` lists. Services now publish capability metadata during registration and unified heartbeat reporting.
