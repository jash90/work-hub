"""Point the hub at a throwaway data directory before importing anything from it."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("WORK_HUB_DATA", tempfile.mkdtemp(prefix="work-hub-test-"))
