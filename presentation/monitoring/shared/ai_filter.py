"""AI-assisted search-keyword filter — shared by the Security Events / MCP
Call History / Action Logs tabs' search box. Extracted verbatim from
``ui/monitoring_tab.py``'s ``MonitoringTab._ai_filter``.

Each caller owns its own ``state`` dict (just ``{}`` at construction) so a
repeat click is a no-op while a request is already in flight — mirrors the
original single ``self._ai_filter_worker`` attribute, without needing a
shared base class.
"""
from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QPushButton


def start_ai_filter(ctx, search: QLineEdit, ai_btn: QPushButton, state: dict) -> None:
    """Nhờ AI dịch câu tìm kiếm tự nhiên thành từ khoá lọc bảng sự kiện.

    Ô tìm rỗng hoặc đang chạy dở thì bỏ qua.
    """
    query = search.text().strip()
    if not query or state.get("worker") is not None:
        return
    ai_btn.setEnabled(False)

    def job(worker):
        """Chạy nền: hỏi model từ khoá lọc tương ứng câu người dùng gõ."""
        provider = ctx.build_active_provider()
        reply = provider.chat([
            {"role": "system", "content":
                "Turn the user's natural-language question about an audit/security event "
                "log into ONE short search keyword. Reply with ONLY the keyword."},
            {"role": "user", "content": query},
        ], cancel=worker.is_cancelled)
        return {"keyword": (reply.get("content") or "").strip().splitlines()[0][:60]}

    def done(result: dict) -> None:
        """Đổ từ khoá model trả về vào ô tìm và áp bộ lọc."""
        state["worker"] = None
        ai_btn.setEnabled(True)
        search.setText(result.get("keyword") or query)

    def failed(_err: str) -> None:
        """Lọc bằng AI lỗi: chỉ mở khoá lại nút, giữ nguyên bộ lọc đang có — đây là
        tiện ích phụ, hỏng thì không được làm phiền người dùng.
        """
        state["worker"] = None
        ai_btn.setEnabled(True)

    from ....core.worker import AgentWorker
    w = AgentWorker(job)
    w.finished_ok.connect(done)
    w.failed.connect(failed)
    state["worker"] = w
    w.start()
