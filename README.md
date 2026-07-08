# Titan SDK v1.4.0 — Lifecycle Intelligence Framework

Titan SDK is the shared operational framework for Titan Platform applications. It provides service registration, heartbeats, status reporting, events, metrics, diagnostics, operations metadata, retry handling, and lifecycle helpers for long-running services, workers, bots, and scheduled jobs.

## Install from GitHub release

```txt
git+https://github.com/redhottdealz-ui/Titan-SDK.git@v1.4.0
```

## Basic service

```python
from titan_sdk import TitanClient


titan = TitanClient(
    service_key="marketing_worker",
    name="Titan Marketing Video Worker",
    version="2.0.0",
    service_type="worker",
    capabilities=["video", "discord", "facebook"],
)

titan.operation(
    key="featured_product_video_job",
    name="Featured Product Video Job",
    description="Generate and upload a featured Titan Legends product video.",
)

titan.start(current_state="Waiting for scheduled job")
```

## Lifecycle job API

Use `titan.job()` for bounded jobs such as GitHub Actions, cron jobs, scheduled workers, and automation runs.

```python
with titan.job("Featured Product Video") as job:
    job.progress("Collecting products")
    products = collect_products()

    job.progress("Rendering video", metrics={"products_loaded": len(products)})
    video = render_video(products[0])

    job.progress("Uploading video")
    upload(video)
```

The SDK automatically sends:

- job started event
- running status
- progress events
- job completed or failed event
- success or error status
- metrics
- runtime diagnostics

## Manual metrics

```python
titan.increment("videos_generated_today")
titan.increment("facebook_posts_today")
titan.metric("last_render_seconds", 42.5)
titan.timer("featured_product_video", 42.5)
```

## Diagnostics providers

```python
def media_diagnostics(client):
    return {
        "music_files": 8,
        "logo_files": 3,
        "generated_videos": 4,
    }


titan.add_diagnostics_provider(media_diagnostics)
```

## Operations helpers

```python
titan.operation(
    key="health_check",
    name="Health Check",
    description="Report storage, media, webhook, Facebook, and runtime readiness.",
    operation_type="read",
    enabled=True,
    requires_confirmation=False,
)
```

## Telemetry separation

Titan SDK v1.4.0 keeps telemetry clean:

- `heartbeat()` is lightweight liveness.
- `status()` is for state transitions.
- `event()` is for human-readable timeline entries.
- `metrics()` is for counters, gauges, timers, and display values.

This prevents noisy status updates and keeps Mission Control readable.

## Environment variables

```txt
TITAN_OS_URL=https://your-control-center-url
TITAN_OS_API_KEY=your-api-key
TITAN_SERVICE_KEY=optional-service-key
TITAN_SERVICE_NAME=optional-service-name
TITAN_SERVICE_TYPE=worker|bot|scheduled_job|service
TITAN_REPOSITORY=optional-repository-name
TITAN_ENVIRONMENT=production
TITAN_DEPLOYMENT=Miget
```

## Version

Current release: `v1.4.0 — Lifecycle Intelligence Framework`


## Titan SDK v1.5.0 Platform Events

Titan SDK v1.5.0 keeps the existing `titan.event(...)` API backward-compatible and adds typed platform event metadata for cross-service coordination.

```python
titan.platform_event(
    event_type="member.hiatus.started",
    title="Hiatus Started",
    message="Member entered hiatus.",
    level="info",
    subject_id=member_id,
    subject_type="discord_member",
    correlation_id="HIA-000123",
    tags=["member", "hiatus"],
    data={"hiatus_id": 123},
)
```

Existing calls like `titan.event(title="Job Completed", message="...")` continue to work unchanged.


## Titan SDK v1.5.2 — Unified API Routing

The SDK includes canonical API route constants in `titan_sdk.api_routes` so services do not hardcode Titan Control Center endpoints. Use `join_url(TITAN_OS_URL, PERSONALITY_REGISTRY_STATUS)` for registry status reporting and the exported constants for service registration, heartbeat, status, events, and metrics.


## Titan SDK v1.6.0 — Capability Registry

Titan SDK v1.6.0 adds the Unified Capability Registry. Services can continue passing simple capability keys to `TitanClient(capabilities=[...])`; the SDK now enriches those keys into a shared metadata payload used by Titan Control Center.

Example:

```python
titan = TitanClient(
    service_key="battle_bot",
    name="Titan Battle Bot",
    version="1.4.0",
    capabilities=[
        "discord",
        "battle_scheduler",
        "draws",
        "voice_automation",
        "heartbeats",
    ],
)
```

The SDK publishes:
- capability keys
- display labels
- categories
- schema version
- capability counts
- heartbeat component metadata

No additional environment variables are required.
