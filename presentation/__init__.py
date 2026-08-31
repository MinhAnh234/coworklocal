"""Presentation layer: Qt widgets, one screen/concern per file, assembled
into thin shell containers (EPIC R08).

Nothing under here is imported by ``domain/`` or ``application/``
(``scripts/check_imports.py`` rule I3) — data flows the other way, through
application services these widgets call.
"""
