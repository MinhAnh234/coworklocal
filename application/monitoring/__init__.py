"""Read-only query services for monitoring/dashboard screens (EPIC R08).

⚠️ Ownership note (R08-T13): per ``docs/refactor/Feature_Architecture_
Proposal.md``'s file-split diagram, ``dashboard_query_service.py`` lives
under ``application/monitoring/`` alongside the Dashboard split — but the
SAME document's "Ranh giới phân hệ" table assigns ``application/monitoring/``
to Team Nam (R08-T07→T10, Monitoring's own 8-tab split). This directory did
not exist yet when Team Hoa reached R08-T13, so creating it here does not
collide with any file Team Nam has written — same situation R06-T02 flagged
for ``infrastructure/persistence/json/atomic_write.py`` vs. Team Nam's
planned ``atomic_json_file.py``. Team Nam should confirm when they start
R08-T07→T10 whether ``DashboardQueryService`` belongs here permanently or
should move once Monitoring's own query service exists.
"""

from .dashboard_query_service import DashboardQueryService
from .monitoring_query_service import MonitoringQueryService

__all__ = ["DashboardQueryService", "MonitoringQueryService"]
