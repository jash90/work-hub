"""work-hub — a localhost web front-end over the Jira/GitLab/git/Tempo work skills.

The hub never reimplements a skill: it runs the skill's own script, keeps the result in an
envelope under data/, and renders it. See workhub/sources.py for the registry.
"""
import os
import sys

# The skills keep their shared plumbing here; the hub reuses it rather than carrying its own
# copy of atomic-write and the token resolver.
LIB = os.path.expanduser("~/.claude/lib")

if LIB not in sys.path:
    sys.path.insert(0, LIB)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("WORK_HUB_DATA") or os.path.join(ROOT, "data")
