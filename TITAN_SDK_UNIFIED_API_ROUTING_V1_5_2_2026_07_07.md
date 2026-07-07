# Titan SDK v1.5.2 — Unified API Routing

## Summary
Adds canonical Titan API route definitions to the SDK so services and Titan Control Center use the same endpoint paths.

## New File
- `titan_sdk/api_routes.py`

## Key Routes
- `/api/register-service`
- `/api/status`
- `/api/heartbeat`
- `/api/event`
- `/api/metrics`
- `/api/titan-ai/personality-registry`
- `/api/titan-ai/personality-registry/version`
- `/api/titan-ai/personality-registry/push-sync`
- `/api/titan-ai/personality-registry/status`

## Compatibility
Backward compatible. Existing SDK client calls now reference route constants internally.

## Environment Variables
New required variables: none.
