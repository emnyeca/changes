"""Legacy compatibility shim for experimental Elektron realtime recorder."""

from __future__ import annotations

from .legacy.elektron_recorder import record_to_elektron

__all__ = ["record_to_elektron"]
