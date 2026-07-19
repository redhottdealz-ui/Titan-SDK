# Titan SDK v1.7.0 — Secure Probation Handoff

Adds canonical API routes and client helpers for approved service-to-service probation requests:

- `PROBATION_REQUESTS`
- `PROBATION_REQUESTS_PENDING`
- `probation_request_ack(request_id)`
- `TitanClient.probation_request(...)`
- `TitanClient.probation_pending(...)`
- `TitanClient.probation_ack(...)`

Requests continue to use the shared `X-Titan-API-Key` authentication model.
