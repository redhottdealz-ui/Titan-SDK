# Titan SDK

Titan SDK is the shared Python client used by Titan applications to report service registration, heartbeats, status, metrics, events, diagnostics, runtime telemetry, and operations metadata to Titan Control Center.

## Current Release

**v1.3.1 — Operations Intelligence Framework**

This release extends the existing TitanClient runtime with richer diagnostics, built-in counters, job timers, lifecycle hooks, capability registration, and safer shutdown behavior while remaining backward compatible with v1.2.0 applications.

## Install from GitHub Release

Applications should install from a release tag, not from the main branch:

```text
git+https://github.com/redhottdealz/Titan-SDK.git@v1.3.1
```

## Environment Variables

Each Titan application should set:

```text
TITAN_OS_BASE_URL=https://your-titan-control-center-url
TITAN_OS_API_KEY=your-api-key
```

`TITAN_OS_URL` is also supported as a fallback for older services.

## Basic Usage

```python
from titan_sdk import TitanClient


titan = TitanClient(
    service_key="example_service",
    name="Example Service",
    version="1.0.0",
    category="Testing",
    icon="🧪",
    capabilities=["scheduler", "discord", "facebook"],
)

titan.start()
titan.status(status="healthy", current_state="Running")
titan.event("Example event", "The service reported successfully.", level="info")
titan.metric("example_count", 1)
```

## Built-in Metrics

The SDK automatically tracks:

- jobs started
- jobs completed
- jobs failed
- warnings
- errors
- events sent
- metrics sent
- heartbeats sent
- successful posts
- failed posts
- queue flushes
- queue retries
- queue drops
- starts
- stops

Use helpers for application metrics:

```python
titan.increment("videos_generated")
titan.set_gauge("queue_depth", 3)
titan.record_timer("render_video", 42.7)
titan.metrics()
```

## Job Timer API

```python
job = titan.begin_job("featured_video")

try:
    # do work
    job.success("Featured video generated.")
except Exception as error:
    job.fail(error)
    raise
```

Context manager form:

```python
with titan.job("weekly_report"):
    build_weekly_report()
```

## Lifecycle Hooks

Optional callbacks can be attached without changing SDK internals:

```python
def on_start(client):
    print("service starting", client.service_key)


titan = TitanClient(
    service_key="example_service",
    name="Example Service",
    on_start=on_start,
)
```

Supported hooks:

- `on_start(client)`
- `on_stop(client)`
- `on_heartbeat(client)`
- `on_error(client, error)`

## Runtime Intelligence

Runtime payloads now include:

- hostname
- process ID
- Python version
- Python executable
- operating system
- platform
- machine architecture
- CPU count
- active thread count
- application version
- SDK version
- uptime
- queue size
- last successful post
- last failed post
- last successful job
- last failed job
- capabilities
- operations
- counters, gauges, and timers

## Graceful Shutdown

Use:

```python
titan.stop()
```

The SDK will publish stopping/offline status, send final metrics, emit shutdown events, and attempt to flush queued requests.

## Backward Compatibility

Existing v1.2.0 applications using `TitanClient.start()`, `status()`, `event()`, `metric()`, `metrics()`, and `stop()` should continue working without code changes.


## Scheduled Job Helpers

Titan SDK v1.3.1 adds helper methods for GitHub Actions, cron jobs, and short-lived workers. These helpers let a job report its lifecycle without pretending to be a continuously running service.

```python
from titan_sdk import TitanClient

titan = TitanClient(
    service_key="product_poster",
    name="GitHub Product Poster",
    version="1.0.0",
    category="Marketing",
    icon="📦",
    capabilities=["scheduled_job", "product_scraping", "discord", "facebook"],
)

titan.start()
job = titan.job_started("Daily Product Poster", "Workflow started.")

try:
    titan.job_progress("Daily Product Poster", "Loading products")
    # run work here
    job.success("Daily Product Poster completed successfully.")
except Exception as error:
    job.fail(error, "Daily Product Poster failed.")
    raise
finally:
    titan.stop()
```

Available job helpers:

- `job_started(name, message=None, metadata=None, metrics=None)`
- `job_progress(name, current_state, message=None, metrics=None, level="info")`
- `job_completed(name, message=None, metrics=None, elapsed_seconds=None)`
- `job_failed(name, error, message=None, metrics=None, elapsed_seconds=None)`
- `begin_job(name, metadata=None)`
- `job(name, metadata=None)` context manager

These helpers are backward compatible with existing Titan SDK v1.3.0 integrations.
