"""write_json - crash-safe JSON writes (R06-T02).

``core/projects.py::save_project`` and ``core/history.py``'s
``save_conversation``/``rename_conversation``/``set_pinned`` all do a plain
``path.write_text(json.dumps(...))`` today. That is two syscalls with a gap in
between: a crash, a killed process, or a full disk between the truncate and
the write leaves a half-written, unparseable JSON file - the NEXT read of
that project/conversation then fails outright (``load_project`` /
``load_conversation`` already treat a parse error as "missing", so this isn't
even a loud failure - a project can silently vanish).

``write_json`` fixes this the standard way: write the full content to a
temporary file in the SAME directory (so the following replace is on one
filesystem, not crossing a mount point), then atomically rename it over the
target. Either the old file is still there, or the new one is fully there -
never a partial one.

Transitional note: EPIC R02 (Team Nam, ``docs/refactor/Refactoring_Checklist.md``
R02-T01) plans a shared ``infrastructure/persistence/json/atomic_json_file.py``
for the SAME purpose across the whole app (config, secrets, ...). This module
is deliberately named differently and scoped to R06's two repositories only,
so the two EPICs don't edit the same file in parallel; once R02-T01 lands,
``WorkspaceRepository``/``ConversationRepository`` should switch to it and
this module can go away.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Any) -> None:
    """Serialize ``data`` as indented UTF-8 JSON and write it to ``path``
    atomically. Creates parent directories if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


__all__ = ["write_json"]
