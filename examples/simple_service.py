import time

from titan_sdk import TitanClient


titan = TitanClient(
    service_key="simple_service",
    name="Simple Service",
    version="1.0.0",
    category="Examples",
    icon="🧪",
    capabilities=[
        "registration",
        "heartbeat",
        "status",
        "events",
        "metrics",
    ],
)


def main():
    titan.start()
    titan.event("Simple service started", "The example service is running.")
    titan.metric("example_runs", 1)

    try:
        while True:
            titan.status("healthy", "Example service running")
            time.sleep(60)
    except KeyboardInterrupt:
        titan.stop()


if __name__ == "__main__":
    main()
