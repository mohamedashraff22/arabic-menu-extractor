"""
Shared utility functions.
"""

from __future__ import annotations

import uuid


def generate_id() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())
