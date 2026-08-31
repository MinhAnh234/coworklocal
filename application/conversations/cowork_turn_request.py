"""Turn the Cowork widget's captured state into a request (R04-T04).

``ui/cowork_tab.py::build_job`` reads a dozen values off the widget on the UI
thread and has to translate three of them before a turn can run: which message
is this turn's prompt, which messages are its history, and whether the workspace
wants commands confirmed. Those rules lived inline in the widget, where no test
could reach them — and each fails silently when wrong (a duplicated user message,
or a command that quietly stops asking for approval).

They live here instead, as the mapping step the migration map assigns to the
application layer. The widget keeps only what is genuinely widget-specific:
reading its own state and building the provider.

Layer rules (``docs/architecture/ADR-001-layered-architecture.md``): pure Python.
Everything arrives as a plain value, so this module never sees a widget.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from ...domain.agents.conversation_execution_request import ConversationExecutionRequest


def build_cowork_turn_request(
    *,
    turn_id: str,
    session_id: str,
    messages: Sequence[Dict[str, Any]],
    surface: str = "cowork",
    project_id: str = "",
    title: str = "",
    provider_id: str = "",
    model: str = "",
    instructions: str = "",
    output_dir: Optional[Any] = None,
    home_output_root: Optional[Any] = None,
    confirm_commands: bool = False,
    agent_role: str = "cowork",
) -> ConversationExecutionRequest:
    """Build one Cowork turn's immutable request.

    ``messages`` is the widget's working list, which ALREADY ends with this
    turn's user message (the chat panel composes it — prefix, attachments,
    session notes — before the job starts). So the prompt is that last message
    and the history is everything before it. The request records both; the
    service is handed the same working list and appends into it.

    Keyword-only on purpose: a dozen positional strings in a call site is exactly
    how a title ends up in the project-id slot.
    """
    history = list(messages or ())
    # ``pop`` rather than ``[-1]``/``[:-1]`` so the empty-list case needs no
    # special branch: a turn with nothing in it yields an empty prompt instead of
    # raising IndexError deep inside a worker thread.
    last = history.pop() if history else {}
    return ConversationExecutionRequest(
        turn_id=turn_id,
        session_id=session_id,
        surface=surface,
        project_id=project_id,
        title=title,
        prompt=str(last.get("content") or ""),
        messages=history,
        provider_id=provider_id,
        model=model,
        project_context=instructions,
        output_dir=output_dir,
        home_output_root=home_output_root,
        # The workspace's Auto-run override (or the global setting) decides
        # whether run_command/install_package must be approved first.
        gate_mode="confirm" if confirm_commands else "auto",
        agent_role=agent_role,
    )


__all__ = ["build_cowork_turn_request"]
