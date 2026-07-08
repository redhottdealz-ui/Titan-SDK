"""Fault-tolerant file and JSON helpers for Titan services.

These helpers are intentionally conservative: they return structured results
instead of raising, so diagnostics, logging, heartbeat loops, and background
workers can degrade gracefully when persistent storage has permissions issues.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class SafeIOResult:
    ok: bool
    path: str
    value: Any = None
    error: str = ""

    def to_dict(self):
        return {"ok": self.ok, "path": self.path, "value": self.value, "error": self.error}


def _path(path: Any) -> Path:
    return path if isinstance(path, Path) else Path(str(path))


def safe_exists(path: Any) -> SafeIOResult:
    p = _path(path)
    try:
        return SafeIOResult(True, str(p), p.exists(), "")
    except Exception as error:
        return SafeIOResult(False, str(p), None, str(error))


def safe_stat(path: Any) -> SafeIOResult:
    p = _path(path)
    try:
        st = p.stat()
        return SafeIOResult(True, str(p), {"size": st.st_size, "mtime": st.st_mtime}, "")
    except Exception as error:
        return SafeIOResult(False, str(p), None, str(error))


def safe_mkdir(path: Any, parents: bool = True, exist_ok: bool = True) -> SafeIOResult:
    p = _path(path)
    try:
        p.mkdir(parents=parents, exist_ok=exist_ok)
        return SafeIOResult(True, str(p), True, "")
    except Exception as error:
        return SafeIOResult(False, str(p), False, str(error))


def safe_read_text(path: Any, default: Optional[str] = None, encoding: str = "utf-8") -> SafeIOResult:
    p = _path(path)
    try:
        return SafeIOResult(True, str(p), p.read_text(encoding=encoding), "")
    except Exception as error:
        return SafeIOResult(False, str(p), default, str(error))


def safe_write_text(path: Any, text: str, encoding: str = "utf-8", create_parent: bool = True) -> SafeIOResult:
    p = _path(path)
    try:
        if create_parent and p.parent:
            p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(str(text), encoding=encoding)
        return SafeIOResult(True, str(p), True, "")
    except Exception as error:
        return SafeIOResult(False, str(p), False, str(error))


def safe_read_json(path: Any, default: Any = None, encoding: str = "utf-8") -> SafeIOResult:
    p = _path(path)
    try:
        return SafeIOResult(True, str(p), json.loads(p.read_text(encoding=encoding)), "")
    except Exception as error:
        return SafeIOResult(False, str(p), default, str(error))


def safe_write_json(path: Any, data: Any, encoding: str = "utf-8", create_parent: bool = True, indent: int = 2) -> SafeIOResult:
    p = _path(path)
    try:
        if create_parent and p.parent:
            p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=indent, sort_keys=True), encoding=encoding)
        return SafeIOResult(True, str(p), True, "")
    except Exception as error:
        return SafeIOResult(False, str(p), False, str(error))


def safe_touch(path: Any, create_parent: bool = True) -> SafeIOResult:
    p = _path(path)
    try:
        if create_parent and p.parent:
            p.parent.mkdir(parents=True, exist_ok=True)
        p.touch(exist_ok=True)
        return SafeIOResult(True, str(p), True, "")
    except Exception as error:
        return SafeIOResult(False, str(p), False, str(error))
