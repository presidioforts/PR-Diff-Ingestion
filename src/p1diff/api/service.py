"""Backward compatibility shim for legacy imports."""

from .services.diff import DiffService, collect_notes

__all__ = ['DiffService', 'collect_notes']
