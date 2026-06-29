VALID_OPERATION_TYPES = {
    "action",
    "diagnostic",
    "report",
    "maintenance",
    "control",
}


class OperationRegistry:
    def __init__(self):
        self._operations = []

    def add(
        self,
        operation_id,
        label,
        description="",
        operation_type="action",
        enabled=False,
        requires_confirmation=True,
        permission="owner",
        reason="Remote execution is locked until Titan OS permissions are complete.",
        metadata=None,
    ):
        operation_type = operation_type if operation_type in VALID_OPERATION_TYPES else "action"

        operation = {
            "id": str(operation_id),
            "label": str(label),
            "description": str(description or ""),
            "type": operation_type,
            "enabled": bool(enabled),
            "requires_confirmation": bool(requires_confirmation),
            "permission": str(permission or "owner"),
            "reason": str(reason or ""),
            "metadata": metadata or {},
        }

        self.remove(operation["id"])
        self._operations.append(operation)

        return operation

    def remove(self, operation_id):
        operation_id = str(operation_id)
        self._operations = [
            operation
            for operation in self._operations
            if operation.get("id") != operation_id
        ]

    def clear(self):
        self._operations = []

    def all(self):
        return list(self._operations)


def default_operations():
    registry = OperationRegistry()

    registry.add(
        operation_id="diagnostics",
        label="Run Diagnostics",
        description="Collect SDK diagnostics and service runtime information.",
        operation_type="diagnostic",
        enabled=False,
        requires_confirmation=False,
        permission="owner",
        reason="Read-only diagnostics execution from Titan OS is not enabled yet.",
    )

    registry.add(
        operation_id="refresh_status",
        label="Refresh Status",
        description="Ask the service to send a fresh status update.",
        operation_type="report",
        enabled=False,
        requires_confirmation=False,
        permission="owner",
        reason="Remote status refresh is not enabled yet.",
    )

    registry.add(
        operation_id="restart_service",
        label="Restart Service",
        description="Safely restart the service.",
        operation_type="control",
        enabled=False,
        requires_confirmation=True,
        permission="owner",
        reason="Remote restart is locked until Titan OS command permissions are complete.",
    )

    return registry.all()
