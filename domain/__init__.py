"""Domain layer - pure Python entities, value objects and events.

The innermost layer of the 4-tier architecture (see
``docs/architecture/ADR-001-layered-architecture.md``). Modules here describe
WHAT the application is about - a turn of conversation, a model candidate, an
agent event - and depend on nothing but the standard library.

Hard rule (ADR-001 I1/I2, enforced by ``scripts/check_imports.py``): no imports
of PySide6/PyQt, and no imports from ``application/``, ``infrastructure/``,
``presentation/`` or the legacy ``core/``/``ui/`` packages.
"""
