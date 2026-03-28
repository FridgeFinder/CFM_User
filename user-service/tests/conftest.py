"""
Root conftest.py – adds Lambda layer paths to sys.path and sets required
environment variables before any test module is imported.

Note: boto3.client() creates a client object but makes no network calls until
a method is invoked on it, so no patching is needed here. Individual tests
mock the client methods they care about via patch.object.
"""
import os
import sys

# ── resolve absolute paths ─────────────────────────────────────────────────
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SERVICE_DIR = os.path.dirname(_TESTS_DIR)  # user-service/

# Add all function directories and layer python/ directories automatically.
# New Lambdas and layers are picked up without any changes here.
_paths = []

for _entry in os.scandir(os.path.join(_SERVICE_DIR, "functions")):
    if _entry.is_dir():
        _paths.append(_entry.path)

for _entry in os.scandir(os.path.join(_SERVICE_DIR, "layers")):
    if _entry.is_dir():
        _python_dir = os.path.join(_entry.path, "python")
        if os.path.isdir(_python_dir):
            _paths.append(_python_dir)

for _p in _paths:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── environment variables ──────────────────────────────────────────────────
# USERS_TABLE is read at module import time by the Lambda handlers.
os.environ.setdefault("USERS_TABLE", "test-users-table")
os.environ.setdefault("DEPLOYMENT_TARGET", "test")
