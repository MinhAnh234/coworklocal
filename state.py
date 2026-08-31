"""Shared application context passed to the UI widgets."""
from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Optional, Tuple

from .config import AppConfig
from .infrastructure.mcp import McpToolSourceManager


def resolve_agent_default(
    active_provider: str,
    setting_model: str,
    current_model: str,
    model_provider: Optional[str],
    user_override: bool,
) -> Tuple[str, bool]:
    """Decide which model a tab's **Agent** selector should default to.

    Rule: the default always follows Settings (the active provider's configured
    model). A per-tab model the user picked by hand survives only while the active
    provider is unchanged — so a fresh launch, or switching the active provider in
    Settings, snaps every tab back to the Settings model, while a deliberate
    runtime override keeps working until then.

    Returns ``(model, keep_override)`` — ``model`` is the model to select
    (``''`` means "use the provider's own default") and ``keep_override`` says
    whether the user's manual override is still in effect.
    """
    if user_override and model_provider == active_provider and current_model:
        return current_model, True
    return setting_model, False


class AppContext:
    """Holds the live config and small convenience factories."""

    def __init__(self, config: AppConfig):
        """Dựng ngữ cảnh dùng chung cho cả ứng dụng: cấu hình, mốc khởi động và các
        nguồn tool.

        Vòng đời kết nối MCP nằm ở ``McpToolSourceManager`` chứ không ở đây — xem
        docstring của nó về việc vì sao kiểm-rồi-tạo phải có khoá.
        """
        self.config = config
        self.started_at = time.time()   # for Monitoring's Sandbox Details "Created"/"Uptime"
        # Admin-configured MCP servers + the built-in MS365 server (R05-T05):
        # connection caching/lifecycle (check-then-create, restart, shutdown)
        # now lives in McpToolSourceManager, extracted so it is testable
        # without an AppContext/Qt. See its docstring for why the check-then-
        # create race matters — several turns (multiple Cowork tabs, parallel
        # Co4E flows, scheduled tasks) can call build_mcp_tools() at once.
        self._mcp_manager = McpToolSourceManager()
        self._ext_connections: dict = {}  # connector id -> McpServerConnection (mcp_stdio mode only)
        # Guards ``_ext_connections`` only now — unified Connectors (CAD/CAE/
        # MS365/Other) aren't covered by McpToolSourceManager (R05-T05 scoped
        # to MCP servers), so this cache still needs its own check-then-create
        # lock, the same race McpToolSourceManager guards against internally.
        self._conn_lock = threading.Lock()
        self._routing_service = None       # lazy RoutingService (Auto Model Routing)
        # Lazy RoutingApplicationService (R03-T03) — the Qt-free decision layer
        # every chat surface now routes through. Wraps _routing_service, which
        # stays the scoring/ranking engine underneath.
        self._routing_application = None
        self._routing_lock = threading.Lock()
        # A SEPARATE lock for the application service: building it calls
        # routing(), which takes _routing_lock. threading.Lock is not
        # reentrant, so sharing one lock across both accessors deadlocks the
        # first caller instead of just serialising them.
        self._routing_app_lock = threading.Lock()
        # The workspace (project) currently selected in the Workspace screen.
        # Per-workspace modes (routing + auto-run) resolve against THIS project
        # so each workspace keeps its own modes. Updated by WorkspaceTab on
        # project switch; "default" is the auto-seeded starter workspace.
        self.active_project_id = "default"

    @property
    def role(self) -> str:
        """Vai trò người dùng. Bản này không có lớp xác thực nên luôn là 'admin'."""
        return "admin"  # no authentication layer, always full access

    # ---- Per-workspace modes (Auto Model Routing + Auto-run) ----------------
    def _current_project(self):
        """The workspace currently selected in the Workspace screen, or None."""
        pid = getattr(self, "active_project_id", "") or ""
        if not pid:
            return None
        from .core.projects import load_project
        return load_project(pid)

    def project_routing_mode(self, surface: str) -> str:
        """Effective Off/Auto/Manual/Fallback routing mode for a chat ``surface``
        in the ACTIVE workspace: the workspace's own override wins; otherwise the
        global default (``config.routing_mode_for``). This is what makes each
        workspace keep its own routing mode.

        The accepted set is taken from ``AppConfig.ROUTING_MODES`` rather than
        repeated here, so adding a mode (as R03-T03 did with "fallback") stays a
        one-line change instead of a hunt through every validation site."""
        project = self._current_project()
        if project is not None:
            mode = (project.routing_modes or {}).get(surface, "")
            if mode in self.config.ROUTING_MODES:
                return mode
        return self.config.routing_mode_for(surface)

    def set_project_routing_mode(self, surface: str, mode: str) -> None:
        """Persist a surface's routing mode for the ACTIVE workspace. With no
        workspace selected, falls back to the global setting so behaviour
        outside a project stays global."""
        mode = mode if mode in self.config.ROUTING_MODES else "off"
        project = self._current_project()
        if project is None:
            self.config.set_routing_mode_for(surface, mode)
            return
        from .core.projects import save_project
        modes = dict(project.routing_modes or {})
        modes[surface] = mode
        project.routing_modes = modes
        save_project(project)

    def project_confirm_commands(self) -> bool:
        """Whether to CONFIRM before running a command in the ACTIVE workspace
        (True → show the Approve/Reject dialog; False → auto-run). The
        workspace's own ``auto_run`` override wins; otherwise the global
        ``agent_security.cowork_confirm_commands``."""
        project = self._current_project()
        if project is not None and project.auto_run is not None:
            return not bool(project.auto_run)   # auto_run True → no confirm (auto-approve)
        return bool(self.config.agent_security.get("cowork_confirm_commands"))

    def project_auto_run(self) -> bool:
        """Convenience inverse of :meth:`project_confirm_commands` — True means
        commands auto-approve (no confirm dialog) in the active workspace."""
        return not self.project_confirm_commands()

    def set_project_auto_run(self, auto_run: Optional[bool]) -> None:
        """Persist the ACTIVE workspace's auto-run override. ``None`` → follow
        the global setting. With no workspace selected, writes the global
        confirm flag instead (``auto_run True`` ⇒ no confirm)."""
        project = self._current_project()
        if project is None:
            if auto_run is not None:
                self.config.agent_security["cowork_confirm_commands"] = (not auto_run)
                self.save()
            return
        from .core.projects import save_project
        project.auto_run = auto_run
        save_project(project)

    def routing(self):
        """The shared :class:`~cowork_local.core.routing.service.RoutingService`
        for Auto Model Assessment & Routing — created on first use so importing
        state.py never pulls in the routing stack (and its deps) at startup.

        One instance per app: it owns the assessment store + the in-memory
        pending-switch registry, both of which must be shared across every chat
        surface (Cowork / Co4E / AI-Edit) so a switch confirmed on one screen
        and the scores probed by the scheduler are visible everywhere."""
        if self._routing_service is None:
            with self._routing_lock:
                if self._routing_service is None:
                    from .core.routing.service import RoutingService
                    self._routing_service = RoutingService(self)
        return self._routing_service

    def routing_application(self):
        """The shared :class:`RoutingApplicationService` (R03-T03).

        This is what UI code should call: it owns the Off/Auto/Manual/Fallback
        policy, the confirm handshake and the never-raise guarantee, while
        :meth:`routing` remains the scoring engine underneath. Chat, Co4E and
        AI-Edit all go through this one object, so a change to routing policy is
        made once instead of three times.

        Built lazily and memoised for the same reason as :meth:`routing`: the
        pending-switch registry and assessment store must be shared app-wide."""
        if self._routing_application is None:
            # Resolve the engine BEFORE taking this lock: routing() takes
            # _routing_lock, and nesting the two acquisitions is what makes the
            # ordering fragile in the first place.
            engine = self.routing()
            with self._routing_app_lock:
                if self._routing_application is None:
                    from .application.model_routing import RoutingApplicationService

                    self._routing_application = RoutingApplicationService(
                        engine,
                        # Per-workspace mode lookup, so each workspace keeps its
                        # own routing behaviour (see project_routing_mode).
                        mode_reader=self.project_routing_mode,
                    )
        return self._routing_application

    def build_active_provider(self):
        """Construct the currently selected provider (called inside workers)."""
        return self.build_provider_for(self.config.active_provider)

    def build_provider_for(self, name: str, model: str | None = None):
        """Construct a provider by key, optionally overriding the model (per-tab
        agent/model selection)."""
        from .providers import build_provider

        name = name or self.config.active_provider
        conf = dict(self.config.provider_conf(name))
        if model:
            conf["model"] = model
        # A self-signed/internal-CA gateway is handled automatically by each
        # provider (see providers.base.Provider._request / core.tls_trust) —
        # this is only an explicit override for advanced/IT-managed setups
        # (COWORK_CA_BUNDLE env var), no longer exposed in Settings.
        conf["ca_bundle"] = self.config.ca_bundle
        return build_provider(name, conf)

    def teams_notifier(self):
        """Bộ gửi thông báo Teams, dựng theo webhook trong cấu hình."""
        from .core.teams import TeamsNotifier

        return TeamsNotifier(self.config.teams.get("webhook_url", ""), ca_bundle=self.config.ca_bundle)

    def save(self) -> None:
        """Ghi cấu hình xuống đĩa."""
        self.config.save()

    # ---- 🔌 MCP Layer — external MCP servers this app connects to as a client
    def build_mcp_tools(self):
        """``(tools, executor)`` for every enabled, successfully-connected MCP
        server in Settings, PLUS the built-in MS365 server when Microsoft 365
        is signed in with a connector enabled (``_ms365_builtin_connection``),
        PLUS every enabled unified Connector (CAD/CAE/MS365/Other — Settings →
        "Connectors (MCP)", see ``core/ext_connectors.py``). Reuses
        connections across calls/turns (spawning a subprocess per turn would
        be slow and wasteful). A server/connector that fails to connect is
        skipped, not a hard failure for the turn."""
        # Master switch (Monitoring → Tools → Connector): when the admin turns
        # "Connect to external" off, the agent connects to NO external
        # connectors/MCP at all — no subprocesses spawned, no REST calls.
        if not self.config.connect_external:
            return [], None
        from .core.ext_connectors import build_ext_connector_tools
        from .core.mcp_client import build_mcp_tools as _merge_mcp_tools
        from .core.tools import combine_tool_sources

        # R05-T05: connection caching/check-then-create for admin-configured
        # servers + the MS365 builtin now lives in McpToolSourceManager (its
        # own lock guards the race — see its docstring).
        active = []
        for entry in self.config.mcp_servers:
            if not entry.get("enabled", True):
                continue
            name = entry.get("name", "")
            command = entry.get("command", "")
            if not name or not command:
                continue
            conn = self._mcp_manager.ensure(name, command, entry.get("args") or [],
                                            entry.get("env") or None)
            if conn is not None:
                active.append(conn)
        builtin = self._ms365_builtin_connection(skip={c.name for c in active})
        if builtin is not None:
            active.append(builtin)
        mcp_tools, mcp_executor = _merge_mcp_tools(active)

        # ``_ext_connections`` isn't covered by McpToolSourceManager (T05
        # scoped to MCP servers) — still serialized under ``_conn_lock``.
        with self._conn_lock:
            ext = self.config.ext_connectors
            all_connectors = [*ext.get("cad", []), *ext.get("cae", []),
                              *ext.get("ms365", []), *ext.get("other", [])]
            ext_tools, ext_executor = build_ext_connector_tools(all_connectors, self._ext_connections)

        # Locally-synced OneDrive/SharePoint (no sign-in) — reads/writes the
        # OneDrive-desktop-synced folders directly, gated on ms365.connectors.
        from .core.ms365_local import build_ms365_local_tools
        local_tools, local_executor = build_ms365_local_tools(self.config)

        return combine_tool_sources((mcp_tools, mcp_executor), (ext_tools, ext_executor),
                                    (local_tools, local_executor))

    # ---- built-in MS365 MCP server (mcp_servers/ms365_server.py) ---------
    _MS365_BUILTIN = "ms365"

    def _ms365_available(self) -> bool:
        """Should the built-in MS365 MCP server exist right now? Mirrors the
        gate ``ms365_tools.build_ms365_tools`` enforces internally: external
        internet allowed + at least one connector on + signed in."""
        ms365 = self.config.ms365
        if not ms365.get("allow_external_internet"):
            return False
        if not any((ms365.get("connectors") or {}).values()):
            return False
        from .core.ms365_auth import signed_in_account

        return signed_in_account(ms365.get("tenant_id", ""),
                                 ms365.get("client_id", "")) is not None

    def _ms365_builtin_connection(self, skip=frozenset()):
        """Connection to the built-in MS365 MCP server — spawned on demand,
        stopped again when the user signs out / disables every connector.
        ``skip`` lets a user-configured server named 'ms365' take precedence."""
        import os
        import sys
        from pathlib import Path

        name = self._MS365_BUILTIN
        if name in skip:
            return None
        if not self._ms365_available():
            self._mcp_manager.stop(name)
            return None
        # The subprocess must import cowork_local even in a from-source run
        # (PYTHONPATH=src) — prepend this package's parent dir explicitly.
        env = dict(os.environ)
        src_root = str(Path(__file__).resolve().parent.parent)
        env["PYTHONPATH"] = (src_root + os.pathsep + env["PYTHONPATH"]
                             if env.get("PYTHONPATH") else src_root)
        return self._mcp_manager.ensure(
            name, sys.executable, ["-m", "cowork_local.mcp_servers.ms365_server"], env)

    def stop_mcp_connections(self) -> None:
        """Terminate every connected MCP server's subprocess (incl. External
        Connectors in mcp_stdio mode) — called on app shutdown so none of
        them linger as orphan processes."""
        from .core.ext_connectors import stop_ext_connections

        self._mcp_manager.stop_all()
        with self._conn_lock:
            stop_ext_connections(self._ext_connections)
