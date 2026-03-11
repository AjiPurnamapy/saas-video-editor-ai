"""
Rate limiter module.

Provides a shared slowapi Limiter instance used across route modules.
Extracted to its own module to avoid circular imports between
main.py and route files.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance — imported by route modules and main.py
limiter = Limiter(key_func=get_remote_address)
