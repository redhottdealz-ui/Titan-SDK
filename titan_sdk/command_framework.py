"""Discord slash command reliability helpers for Titan bots.

The decorator is intentionally optional and light-touch. Bots can adopt it
command-by-command without changing their Discord command registration model.
"""
from __future__ import annotations

import asyncio
import functools
import traceback
from typing import Any, Callable, Optional

from .telemetry import CommandTelemetry


async def _send_safe_interaction_message(interaction, message: str, ephemeral: bool = True):
    try:
        if getattr(interaction, "response", None) and not interaction.response.is_done():
            await interaction.response.send_message(message, ephemeral=ephemeral)
        elif getattr(interaction, "followup", None):
            await interaction.followup.send(message, ephemeral=ephemeral)
    except Exception:
        pass


def _interaction_ids(interaction):
    guild_id = str(getattr(getattr(interaction, "guild", None), "id", "") or "")
    user_id = str(getattr(getattr(interaction, "user", None), "id", "") or "")
    return guild_id, user_id


def safe_slash_command(
    client=None,
    name: Optional[str] = None,
    timeout_seconds: int = 25,
    ephemeral_errors: bool = True,
    failure_message: str = "⚠️ This Titan command hit an error instead of hanging. The issue has been reported.",
):
    """Wrap a Discord app command so it cannot hang silently.

    Usage:
        @safe_slash_command(client=titan, name="my_command")
        @app_commands.command(name="my_command")
        async def my_command(interaction, ...):
            ...
    """
    def decorator(func: Callable):
        command_name = name or getattr(func, "__name__", "slash_command")

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            interaction = args[0] if args else kwargs.get("interaction")
            if interaction is None and len(args) > 1:
                interaction = args[1]
            active_client = client
            if active_client is None:
                for candidate in args:
                    active_client = getattr(candidate, "titan", None) or getattr(candidate, "client", None)
                    if active_client:
                        break
            guild_id, user_id = _interaction_ids(interaction) if interaction is not None else ("", "")
            telemetry = CommandTelemetry(command_name=command_name, service_key=getattr(active_client, "service_key", ""), guild_id=guild_id, user_id=user_id)
            try:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
                telemetry.finish("success")
                if active_client and hasattr(active_client, "record_command_telemetry"):
                    active_client.record_command_telemetry(telemetry)
                return result
            except asyncio.TimeoutError as error:
                telemetry.finish("timeout", f"Command exceeded {timeout_seconds}s")
                if active_client and hasattr(active_client, "record_command_telemetry"):
                    active_client.record_command_telemetry(telemetry)
                if active_client and hasattr(active_client, "error"):
                    active_client.error(f"Command Timeout: {command_name}", f"Command exceeded {timeout_seconds}s", data=telemetry.to_dict())
                if interaction is not None:
                    await _send_safe_interaction_message(interaction, f"⚠️ This command took too long and was stopped after {timeout_seconds} seconds.", ephemeral=ephemeral_errors)
                return None
            except Exception as error:
                telemetry.finish("error", str(error))
                payload = telemetry.to_dict()
                payload["traceback"] = traceback.format_exc()
                if active_client and hasattr(active_client, "record_command_telemetry"):
                    active_client.record_command_telemetry(telemetry)
                if active_client and hasattr(active_client, "error"):
                    active_client.error(f"Command Failed: {command_name}", str(error), data=payload)
                if interaction is not None:
                    await _send_safe_interaction_message(interaction, failure_message, ephemeral=ephemeral_errors)
                return None

        return wrapper
    return decorator
