"""Wires :class:`ConversationApplicationService` to the existing runtime (R04-T03).

The service is written against the narrow seams in :mod:`turn_runtime` so it can
be tested with plain fakes. This module supplies the real implementations — the
provider call with its recovery pass, the tool/sandbox runtime, the security
guards, context compaction — and is therefore the ONLY file in
``application/conversations/`` that knows ``core/*`` exists. Same shape (and
same reason) as ``application/model_routing/core_routing_adapter.py`` in R03.

Every ``core`` import is deferred into a method body: importing the tool runtime
pulls in ``requests``, ``psutil`` and the sandbox stack, and code that merely
*builds* a service must not pay for that.

Faithfulness notes — two places where this reproduces a quirk of the current
runtime rather than the behaviour one would design fresh. Both are marked
inline: the MS365 system-prompt paragraph keys off the CONFIGURED extra tools
(not the advertised subset), and the ``tool_result`` path falls back to the
call's own ``path`` argument resolved against the workdir.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ...domain.agents.agent_event import PlanStep, ToolPreview
from .conversation_application_service import ConversationApplicationService
from .turn_runtime import PLAN_TOOL, EventSink

# Legacy emit: the dict-based callback every current caller already owns.
LegacyEmit = Callable[[Dict[str, Any]], None]


def legacy_event_sink(emit: LegacyEmit) -> EventSink:
    """Adapt a typed :class:`EventSink` onto the legacy dict ``emit``.

    This is what lets R04 land without touching the presentation layer: the
    service thinks in typed events, ``ui/chat_panel.py::_on_event`` keeps
    receiving exactly the dicts it already dispatches on. Deleted in R08 once
    the widget consumes events directly.
    """
    return lambda event: emit(event.to_legacy_dict())


class CoreModelCall:
    """:class:`ModelCallPort` over ``code_agent._call_provider_with_recovery``.

    Not ``provider.chat`` directly: the recovery wrapper adds the one bounded
    retry that hides a dropped connection or a momentarily unreachable gateway,
    and losing it would be a visible regression on flaky corporate networks.
    """

    def __init__(self, provider: Any) -> None:
        """Bọc một provider của ``core/`` vào cổng ``ModelCallPort``."""
        self._provider = provider

    def call(self, messages, tools, on_text=None, on_reasoning=None, cancel=None):
        """Gọi model một lượt, có tự phục hồi khi tràn context hoặc bị giới hạn tốc độ."""
        from ...core.code_agent import _call_provider_with_recovery

        return _call_provider_with_recovery(self._provider, messages, tools, on_text,
                                            cancel, on_reasoning)


class CoreToolRuntime:
    """:class:`ToolRuntimePort` over ``core/tools.py`` + Cowork's file tools."""

    def __init__(self, output_dir: Path, *, title: str = "",
                 extra_tools: Optional[Sequence[Any]] = None, extra_executor=None,
                 security_config: Any = None, agent_role: str = "") -> None:
        """Bọc bộ tool của ``core/`` vào cổng ``ToolRuntimePort``.

        Tên các tool phụ được gom sẵn vào một ``set`` ngay tại đây: mỗi lượt gọi tool
        đều phải tra tên, tra trên danh sách sẽ chậm dần theo số tool.
        """
        self._output_dir = Path(output_dir)
        self._title = title
        self._extra_tools = list(extra_tools or ())
        self._extra_names = {getattr(t, "name", "") for t in self._extra_tools}
        # The connector executor MCP/REST tools are routed to; None when the
        # turn has no connectors enabled.
        self._extra_executor = extra_executor
        self._security_config = security_config
        self._agent_role = agent_role
        self._ctx: Any = None          # built on first use (see _tool_context)

    # -- the configured extra tools, for the system-prompt hints ---------- #
    @property
    def extra_names(self) -> frozenset:
        """Tên các tool bổ sung (MCP, connector) ngoài bộ dựng sẵn."""
        return frozenset(self._extra_names)

    def _tool_context(self):
        """The sandboxed ``ToolContext`` every built-in tool call runs inside.

        Built once per turn and cached: it carries the resource limits and the
        network policy, so re-deriving it mid-turn could let a Settings change
        take effect halfway through work already in flight.
        """
        if self._ctx is None:
            from ...core import agent_security
            from ...core.tools import ToolContext

            limits, block_network = agent_security.sandbox_settings(self._security_config)
            self._ctx = ToolContext(
                self._output_dir, flatten_writes=True,   # keep every file in the Output root
                resource_limits=limits, block_network=block_network,
                allow_url_fetch=agent_security.url_fetch_allowed(self._security_config),
                jira=(self._security_config.data.get("jira") if self._security_config else None),
            )
        return self._ctx

    # -- ToolRuntimePort -------------------------------------------------- #
    def specs(self, allowed_tools: Optional[Sequence[str]] = None) -> List[Any]:
        """Advertised tools: Cowork's own two, the enabled built-ins, then MCP.

        ``allowed_tools`` restricts the list so a read-only step literally cannot
        write. ``update_plan`` and the connector tools always survive the filter:
        the plan tool has no side effects, and connectors are opted into
        explicitly rather than governed by the built-in capability scope.
        """
        from ...core.chat_agent import SAVE_FILE_SPEC
        from ...core.plan import UPDATE_PLAN_SPEC
        from ...core.tools import enabled_tool_specs

        specs = ([SAVE_FILE_SPEC, UPDATE_PLAN_SPEC]
                 + list(enabled_tool_specs(self._security_config))
                 + self._extra_tools)
        if allowed_tools is None:
            return specs
        allow = set(allowed_tools) | {PLAN_TOOL} | self._extra_names
        return [t for t in specs if getattr(t, "name", "") in allow]

    def preview(self, name: str, args: Dict[str, Any]) -> Optional[ToolPreview]:
        """What the user sees before the call runs."""
        # A connector call has no local diff to show, so it renders as the plain
        # argument dump the runtime already used.
        if name in self._extra_names:
            return ToolPreview(kind="info", title=name, text=str(args))
        if name == "save_file":
            return self._save_file_preview(args)
        from ...core.tools import describe_action

        raw = describe_action(self._tool_context(), name, args)
        return ToolPreview.from_dict(raw)

    def _save_file_preview(self, args: Dict[str, Any]) -> ToolPreview:
        """A before/after diff for the file the agent is about to write.

        A brand-new file renders all-green (before is empty); an overwrite shows
        the real change, so saving a file reads like editing one.
        """
        import difflib

        from ...core.chat_agent import _structure_summary, _titled_filename

        fname = _titled_filename(self._title, args.get("filename", "output.txt"))
        content = str(args.get("content", ""))
        summary = _structure_summary(fname, content)
        old = ""
        existing = self._output_dir / fname
        if existing.exists():
            try:
                old = existing.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass   # unreadable existing file: show it as a fresh write
        diff = "".join(difflib.unified_diff(
            old.splitlines(keepends=True), content.splitlines(keepends=True),
            fromfile=f"a/{fname}", tofile=f"b/{fname}",
        )) or content[:4000]
        return ToolPreview(kind="diff", title=f"Save {fname}",
                           text=f"{summary}\n\n{diff[:4000]}")

    def execute(self, name: str, args: Dict[str, Any], on_output=None,
                cancel=None) -> Dict[str, Any]:
        """Run one tool call and return the runtime's result mapping."""
        if name == PLAN_TOOL:
            return self._execute_plan(args)
        if name in self._extra_names and self._extra_executor is not None:
            # Connector results carry no local file, so no path/produced keys —
            # matching what the runtime reports for an MCP call today.
            result = self._extra_executor(name, args) or {}
            return {"ok": bool(result.get("ok", False)), "output": result.get("output", "")}
        if name == "save_file":
            from ...core.chat_agent import _do_save_file

            return dict(_do_save_file(self._output_dir, self._title, args))

        from ...core.tools import execute_tool

        ctx = self._tool_context()
        result = dict(execute_tool(ctx, name, args, cancel=cancel, on_output=on_output,
                                   agent_role=self._agent_role))
        # Quirk preserved: a tool that wrote the file named in its OWN arguments
        # (write_file/edit_file) does not report a path, so the runtime derives
        # one from the argument. Dropping this would empty the Output list.
        if not result.get("path") and isinstance(args, dict) and args.get("path"):
            result["path"] = str(ctx.workdir / str(args["path"]))
        return result

    def _execute_plan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Apply an ``update_plan`` call: validate the steps and audit them.

        Produces no file and no chat bubble; the service turns the returned
        steps into a single plan event.
        """
        from ...core import agent_roles, audit_log
        from ...core.plan import normalize_plan_steps

        steps = normalize_plan_steps(args.get("steps"))
        audit_log.record("tool_call", PLAN_TOOL, True, f"{len(steps)} step(s)",
                         agent_role=agent_roles.PLANNER)
        return {"ok": True, "output": "Plan updated.",
                "plan_steps": [PlanStep(title=s["title"], status=s["status"]) for s in steps]}

    def snapshot(self) -> Any:
        """Ảnh chụp thư mục kết quả trước lượt chạy — dùng để biết tệp nào mới sinh ra."""
        from ...core.tools import _snapshot

        return _snapshot(self._output_dir)

    def finalize(self, before: Any, cancelled: bool = False
                 ) -> Tuple[List[str], List[str]]:
        """Drop the scratch sandbox and flatten deliverables into the root.

        Returns ``(gone, arrived)``: a file that MOVED counts as both, because
        the Output list keys entries by path and must drop the old one.
        """
        from ...core.chat_agent import _cleanup_cowork_intermediates

        removed, moved = _cleanup_cowork_intermediates(self._output_dir, before,
                                                       cancelled=cancelled)
        gone = list(removed) + [old for old, _new in moved]
        arrived = [new for _old, new in moved]
        return gone, arrived


def build_cowork_conversation_service(
    provider: Any,
    output_dir: Path,
    emit: LegacyEmit,
    *,
    title: str = "",
    project_context: str = "",
    extra_tools: Optional[Sequence[Any]] = None,
    extra_executor=None,
    security_config: Any = None,
    gate: Any = None,
    agent_role: str = "",
) -> ConversationApplicationService:
    """A service wired to the real runtime, ready to execute a Cowork turn.

    ``emit`` is the legacy dict callback: the guards and the compactor publish
    their own notices through it directly (exactly as they do now), while the
    service's typed events reach it via :func:`legacy_event_sink`.

    ``gate`` present means the workspace asked to confirm commands; pass the
    request with ``gate_mode="confirm"`` so the two agree. A gate of ``None``
    keeps the pre-existing auto-run behaviour.
    """
    from ...core import agent_roles

    tools = CoreToolRuntime(
        output_dir, title=title, extra_tools=extra_tools, extra_executor=extra_executor,
        security_config=security_config, agent_role=agent_role or agent_roles.COWORK,
    )

    def prepare_prompt(messages: List[Dict[str, Any]], advertised: Tuple[str, ...]) -> None:
        """Insert the system prompt, then fold in skills, rules and project text.

        ``advertised`` is unused on purpose: the runtime decides the MS365
        paragraph from the CONFIGURED connector tools, not from the subset a
        capability scope left advertised. Changing that changes the prompt the
        model sees, so it stays as-is here and belongs to R05's tool-policy work.
        """
        from ...core.chat_agent import (
            COWORK_TOOL_PROMPT,
            OPENDATALOADER_PDF_PROMPT,
            _apply_project_context,
            _apply_security_rules,
            _apply_skills,
        )
        from ...core.deps import _can_pip
        from ...core.java_runtime import find_java
        from ...core.security_rules import load_rules
        from ...core.skills import active_skills_text

        if not messages or messages[0].get("role") != "system":
            system = COWORK_TOOL_PROMPT
            if any(n.startswith("ms365_") for n in tools.extra_names):
                system += ("\nThe user has signed in to Microsoft 365 and enabled some ms365__* "
                           "tools (Outlook / Teams / OneDrive / SharePoint / meeting transcripts, "
                           "via the built-in MS365 MCP server). Use them whenever the request "
                           "involves that data — don't say you can't access it.")
            if find_java() is not None and _can_pip():
                # Only advertise the Java-backed PDF extractor when BOTH the JVM
                # and pip are available, so the agent is never steered into a
                # command that cannot work on this machine.
                system += "\n\n" + OPENDATALOADER_PDF_PROMPT
            messages.insert(0, {"role": "system", "content": system})
        _apply_skills(messages, active_skills_text())
        _apply_security_rules(messages, load_rules())
        _apply_project_context(messages, project_context)

    def prompt_guard(messages: List[Dict[str, Any]]) -> None:
        """Chốt an toàn cho prompt trước khi gửi: quét dấu hiệu tiêm lệnh."""
        from ...core import agent_security

        agent_security.enforce_prompt(provider, messages, security_config, emit)

    def command_guard(name: str, args: Dict[str, Any]) -> None:
        """Chốt an toàn cho lệnh shell trước khi chạy: phân loại rủi ro và chặn/hỏi."""
        from ...core import agent_security

        agent_security.enforce_command(provider, name, args, security_config, emit)

    def compact(messages: List[Dict[str, Any]], cancel) -> None:
        """Nén lịch sử hội thoại khi gần đầy cửa sổ ngữ cảnh."""
        from ...core import context_budget

        context_budget.maybe_compact(provider, messages, security_config,
                                     emit=emit, cancel=cancel)

    return ConversationApplicationService(
        CoreModelCall(provider), tools,
        prepare_prompt=prepare_prompt,
        prompt_guard=prompt_guard,
        command_guard=command_guard,
        compact=compact,
        permission_request=(gate.request if gate is not None else None),
    )


__all__ = [
    "LegacyEmit", "legacy_event_sink", "CoreModelCall", "CoreToolRuntime",
    "build_cowork_conversation_service",
]
