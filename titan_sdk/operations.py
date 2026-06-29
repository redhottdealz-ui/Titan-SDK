from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Operation:
    id: str
    label: str
    description: str = ""
    type: str = "action"
    enabled: bool = False
    requires_confirmation: bool = True
    permission: str = "owner"
    reason: str = "Remote execution is locked until Titan OS permissions are complete."
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.id,
            "label": self.label,
            "name": self.label,
            "description": self.description,
            "type": self.type,
            "operation_type": self.type,
            "enabled": self.enabled,
            "requires_confirmation": self.requires_confirmation,
            "permission": self.permission,
            "reason": self.reason,
            "metadata": self.metadata,
        }


class OperationRegistry:
    def __init__(self):
        self._operations: Dict[str, Operation] = {}

    def add(
        self,
        operation_id: Optional[str] = None,
        label: Optional[str] = None,
        description: str = "",
        operation_type: str = "action",
        enabled: bool = False,
        requires_confirmation: bool = True,
        permission: str = "owner",
        reason: str = "Remote execution is locked until Titan OS permissions are complete.",
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        operation_id = operation_id or kwargs.get("id") or kwargs.get("key")
        if not operation_id:
            raise ValueError("operation_id is required")
        label = label or kwargs.get("name") or kwargs.get("label") or operation_id
        operation_type = operation_type or kwargs.get("type", "action")

        operation = Operation(
            id=operation_id,
            label=label,
            description=description or kwargs.get("description", ""),
            type=operation_type,
            enabled=enabled,
            requires_confirmation=requires_confirmation,
            permission=permission,
            reason=reason,
            metadata=metadata or kwargs.get("metadata", {}),
        )
        self._operations[operation.id] = operation
        return operation.to_dict()

    def operation(self, key=None, name=None, **kwargs):
        return self.add(operation_id=key, label=name, **kwargs)

    def remove(self, operation_id):
        self._operations.pop(operation_id, None)

    def clear(self):
        self._operations.clear()

    def get(self, operation_id):
        operation = self._operations.get(operation_id)
        return operation.to_dict() if operation else None

    def all(self) -> List[Dict[str, Any]]:
        return [operation.to_dict() for operation in self._operations.values()]

    def count(self) -> int:
        return len(self._operations)


def default_operations():
    return [
        {
            "id": "view_status",
            "label": "View Status",
            "description": "View current service status and health.",
            "type": "read",
            "enabled": True,
            "requires_confirmation": False,
            "permission": "viewer",
            "reason": "Read-only operation.",
            "metadata": {},
        },
        {
            "id": "view_metrics",
            "label": "View Metrics",
            "description": "View service metrics reported by the SDK.",
            "type": "read",
            "enabled": True,
            "requires_confirmation": False,
            "permission": "viewer",
            "reason": "Read-only operation.",
            "metadata": {},
        },
        {
            "id": "view_diagnostics",
            "label": "View Diagnostics",
            "description": "View runtime diagnostics for troubleshooting.",
            "type": "read",
            "enabled": True,
            "requires_confirmation": False,
            "permission": "viewer",
            "reason": "Read-only operation.",
            "metadata": {},
        },
    ]
