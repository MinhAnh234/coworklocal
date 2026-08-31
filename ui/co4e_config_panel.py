"""Co4E right-hand config panels — edit a selected step node's persona.

StepConfigPanel has moved to ``presentation/co4e/node_property_panel.py``
(split further into ``presentation/co4e/step_config_section.py`` and
``presentation/co4e/node_property_actions_mixin.py`` to stay under the
400-line-per-file cap). Re-exported here, unchanged in name and behaviour, so
every existing ``from .co4e_config_panel import StepConfigPanel`` (e.g.
``ui/co4e_tab.py``) keeps working without edits.
"""
from __future__ import annotations

from ..presentation.co4e.node_property_panel import StepConfigPanel

__all__ = ["StepConfigPanel"]
