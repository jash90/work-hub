"""Point the hub at a throwaway data directory before importing anything from it.

The settings paths are redirected the same way, and for a stronger reason: a test that
saved a token would otherwise overwrite the real `.env` and the real files under
~/.claude/.secrets that the skills read.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SANDBOX = tempfile.mkdtemp(prefix="work-hub-test-")

os.environ.setdefault("WORK_HUB_DATA", SANDBOX)
os.environ.setdefault("WORK_HUB_ENV", os.path.join(SANDBOX, ".env"))
os.environ.setdefault("WORK_HUB_SECRETS_DIR", os.path.join(SANDBOX, "secrets"))
