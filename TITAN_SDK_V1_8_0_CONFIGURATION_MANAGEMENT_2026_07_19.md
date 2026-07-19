# Titan SDK v1.8.0 — Configuration Management Foundation

## Added
- `ConfigurationClient` for configuration fetch and applied-version acknowledgement.
- `ConfigurationSnapshot` and `ConfigurationApplyResult` models.
- Shared schema normalization and supported field-type contract.
- Local snapshot validation for required and Discord resource fields.
- Hot-reload handler registry with safe `pending_restart` fallback.

## Compatibility
The release is backward compatible with existing Titan SDK lifecycle, telemetry, reliability, operations, and probation handoff APIs.
