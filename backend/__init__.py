"""Backend package init.

This file makes the `backend` directory a proper Python package so
absolute imports like `from backend.geoip import ...` work when running
submodules directly.
"""

__all__ = ["geoip", "ws", "events", "risk"]
