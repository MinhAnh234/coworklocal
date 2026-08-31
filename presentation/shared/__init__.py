"""Small pieces shared across more than one presentation screen (EPIC R08).

Kept intentionally minimal — this is NOT a dumping ground for every reusable
widget (``ui/icons.py``, ``ui/widgets.py``, ``ui/routing_toggle.py`` stay
where they are; migrating those is a separate concern from R08-T12/T14).
Only ``HAS_WEB_ENGINE`` lives here so far — it was one module-level flag
duplicated between two God files being split by two different R08 tasks
(``ui/folder_tab.py`` and ``ui/structure_graph_view.py``), and a shared
constant beats one screen importing another screen's module.
"""

from .web_engine_support import HAS_WEB_ENGINE

__all__ = ["HAS_WEB_ENGINE"]
