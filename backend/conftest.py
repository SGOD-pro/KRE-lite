"""
conftest.py — pytest configuration and shared fixtures for backend tests.

Adds backend/ to sys.path so `from app.xxx import yyy` works from tests/.
"""
import sys
from pathlib import Path

# Ensure the backend/ directory is on sys.path regardless of where pytest runs from
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
