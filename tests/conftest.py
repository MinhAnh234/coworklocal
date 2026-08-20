"""Make the repository package importable when pytest runs from the repo root."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_PARENT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_PARENT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_PARENT))
