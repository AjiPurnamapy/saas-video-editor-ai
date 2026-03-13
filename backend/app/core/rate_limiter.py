"""
Rate limiter module.

Provides a shared slowapi Limiter instance used across route modules.
Extracted to its own module to avoid circular imports between
main.py and route files.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
import os

# Disable limiter entirely during tests by checking an env var we'll set in conftest
_is_testing = os.getenv("TESTING") == "1"

# Shared limiter instance — imported by route modules and main.py
limiter = Limiter(key_func=get_remote_address, enabled=not _is_testing)
