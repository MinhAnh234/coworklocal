"""Backward-compatible re-export.

The Monitoring Dashboard's implementation moved to
``presentation/monitoring/`` (container + one file per sub-tab, plus shared
helpers/services) as part of the N2 refactor. ``app.py`` imports
``MonitoringTab`` from this exact path (``from .ui.monitoring_tab import
MonitoringTab``) and cannot be modified, so this module stays as the single
stable import site while the real code lives in the new package.
"""
from __future__ import annotations

from ..presentation.monitoring.monitoring_tab import MonitoringTab

__all__ = ["MonitoringTab"]
