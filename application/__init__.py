"""Application layer - pure Python use-case orchestration.

Sits between ``presentation/`` (Qt widgets) and ``domain/`` (entities). A module
here answers "what has to happen, in what order" for one use case - route a
turn, run a conversation - without knowing whether a human, a scheduler or a
test triggered it.

Hard rule (ADR-001 I1/I3, enforced by ``scripts/check_imports.py``): no
PySide6/PyQt imports and no reach into ``presentation/``/``ui/``. Results travel
back up through plain-Python callbacks; turning those into Qt signals is the
presentation layer's job.
"""
