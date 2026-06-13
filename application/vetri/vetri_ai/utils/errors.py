from __future__ import annotations


class VetriError(Exception):
    """Base exception for Vetri AI foundation code."""


class PolicyBlockedError(VetriError):
    """Raised when policy blocks an action."""
