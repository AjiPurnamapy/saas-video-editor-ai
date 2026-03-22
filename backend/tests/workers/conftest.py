"""
conftest for worker tests.

Adds the project root to sys.path so worker modules
(which live outside backend/) are importable.
"""

import os
import sys

# The project root is two levels up from backend/tests/workers/
_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
