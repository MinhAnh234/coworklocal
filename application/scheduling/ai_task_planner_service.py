"""AiTaskPlannerService - AI-generate / import task lists, outside the widget
(R07-T05).

``ui/schedule_task_tab.py``'s ``_AiCreateDialog`` already delegates the
actual planning to two existing pure functions —
``core/ai_task_planner.py::plan_tasks`` (natural-language description ->
task dicts, via the active provider) and
``core/task_import.py::import_tasks`` (Excel/CSV/JSON -> task dicts) — so
this service does not reimplement either. What it DOES own is one small
piece of business logic that currently only exists inside the dialog's
``AgentWorker`` job closure (``_generate``'s ``job()``): every AI-generated
task must carry the SAME file/link attachments the user attached to the
request, so they're available again at run time, not just visible to the
planner while it drafts the task list. Leaving that step trapped in a Qt
worker closure means it can only be exercised by driving the real dialog;
here it's a plain, independently testable method.

Pure Python: no Qt import. The provider is a constructor-injected factory
(``() -> Provider``, no arguments — matches ``AppContext.build_active_
provider``), the same dependency-inversion shape
``application/conversations/conversation_application_service.py`` (R04-T03)
uses for ITS provider factory.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

ProviderFactory = Callable[[], Any]
CancelFn = Callable[[], bool]


class AiTaskPlannerService:
    """AI task generation + file/Excel/CSV/JSON import, for
    ``presentation/scheduling/ai_task_creator_dialog.py`` and
    ``ai_task_import_dialog.py`` (R08-T11) to call instead of importing
    ``core.ai_task_planner``/``core.task_import`` directly.

    Args:
        provider_factory: ``() -> Provider``. Production passes
            ``AppContext.build_active_provider``; tests pass a lambda
            returning a :class:`FakeProvider`.
    """

    def __init__(self, provider_factory: Optional[ProviderFactory] = None) -> None:
        """``provider_factory`` là hàm dựng provider, gọi lúc cần chứ không dựng sẵn —
        provider có thể bị đổi giữa hai lần lập kế hoạch.
        """
        self._provider_factory = provider_factory

    def plan(
        self,
        description: str,
        *,
        file_paths: Sequence[str] = (),
        links: Sequence[str] = (),
        provider: Any = None,
        cancel: Optional[CancelFn] = None,
    ) -> List[Dict[str, Any]]:
        """Turn ``description`` into a list of NOT-yet-saved task dicts.

        ``provider`` overrides the constructor's factory for this one call
        (useful for tests, or a caller that already resolved a provider);
        omit it to use the injected factory. Raises ``RuntimeError`` when
        no provider is available at all, or when the model's reply had no
        parseable task list (same error ``core.ai_task_planner.plan_tasks``
        already raises).
        """
        resolved = provider if provider is not None else self._resolve_provider()
        from cowork_local.core.ai_task_planner import plan_tasks

        planned = plan_tasks(resolved, description, cancel=cancel)
        # Attachments apply to EVERY generated task so they're still there
        # when the task actually runs, not just while the planner drafts it
        # (see module docstring — this used to only happen inside the
        # dialog's worker closure).
        for task in planned:
            task["input"]["file_paths"] = list(file_paths)
            task["input"]["links"] = list(links)
        return planned

    def import_file(self, path: Union[str, Path]) -> List[Dict[str, Any]]:
        """Excel/CSV/JSON -> NOT-yet-saved task dicts, auto-chained in file
        order. Raises ``ValueError`` with a human-readable message on an
        unusable/unsupported file (same contract
        ``core.task_import.import_tasks`` already has)."""
        from cowork_local.core.task_import import import_tasks

        return import_tasks(path)

    def _resolve_provider(self) -> Any:
        """Provider dùng để lập kế hoạch; chưa cấu hình thì báo lỗi rõ ràng ngay tại
        đây thay vì để lỗi nổ ra ở tận tầng HTTP.
        """
        if self._provider_factory is None:
            raise RuntimeError("No provider available to plan tasks.")
        return self._provider_factory()


__all__ = ["AiTaskPlannerService"]
