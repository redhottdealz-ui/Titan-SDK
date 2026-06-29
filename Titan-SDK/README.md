# Titan SDK

Titan SDK is the shared Python client used by Titan applications to report service registration, heartbeat, status, metrics, and events to Titan Control Center.

## Install from GitHub

Add this to an application's `requirements.txt`:

```text
git+https://github.com/redhottdealz/Titan-SDK.git@main
```

After the first stable release tag is created, prefer:

```text
git+https://github.com/redhottdealz/Titan-SDK.git@v1.0.0
```

## Environment Variables

Each Titan application should set:

```text
TITAN_OS_BASE_URL=https://your-titan-control-center-url
TITAN_OS_API_KEY=your-api-key
```

## Basic Usage

```python
from titan_sdk import TitanClient


titan = TitanClient(
    service_key="example_service",
    name="Example Service",
    version="1.0.0",
    category="Testing",
    icon="🧪",
    capabilities=["heartbeat", "status", "metrics", "events"],
)

titan.start()
titan.status(status="healthy", current_state="Running")
titan.event("Example event", "The service reported successfully.", level="info")
titan.metric("example_count", 1)
```

## Features

- Service self-registration
- Heartbeat reporting
- Status reporting
- Metrics reporting
- Event reporting
- Runtime metadata reporting
- Retry queue for failed status/event/metric requests
