"""Bốn màn chính và cách chuyển giữa chúng — R08-T10.

Dashboard và Lịch chỉ được dựng ở lần mở đầu tiên (dựng lười) — mở app không
phải trả giá cho hai màn có thể cả phiên không ai vào. ``_ensure_page`` là chỗ
duy nhất biết điều đó, nên mọi đường tới một trang đều phải đi qua ``_goto``.

Cùng kiểu mixin, xem ghi chú ở đầu ``nav_rail.py``.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from ...i18n import tr
from ..dashboard.dashboard_tab import DashboardTab
from ...ui.monitoring_tab import MonitoringTab
from ..scheduling.schedule_task_tab import ScheduleTaskTab



class PageRegistryMixin:
    """Bốn màn chính của cửa sổ và cách chuyển giữa chúng.

    Dashboard và Lịch dựng lười ở lần mở đầu tiên, nên MỌI đường tới một trang
    phải đi qua :meth:`_goto` — đó là chỗ duy nhất gọi :meth:`_ensure_page`.
    """

    # Lớp này từng khai ``_page_index`` HAI lần: bản đầu chỉ gọi
    # ``self.pages.indexOf(widget)`` và bị bản phía dưới che hoàn toàn (Python
    # giữ định nghĩa sau cùng), tức là mã chết. Đã gỡ bản đầu; bản còn lại nằm
    # ngay dưới ``_ensure_page`` và nó BẮT BUỘC phải so sánh danh tính trước,
    # vì trang dựng lười vẫn còn là widget giữ chỗ cho tới lần mở đầu tiên.
    def _build_dashboard(self):
        """Dựng màn Bảng điều khiển và nối dòng trạng thái của nó vào thanh dưới."""
        d = DashboardTab(self.ctx)
        d.status_message.connect(self.statusBar().showMessage)
        self.dashboard = d
        return d
    def _build_schedule(self):
        """Dựng màn Lịch trình và nối dòng trạng thái của nó vào thanh dưới."""
        s = ScheduleTaskTab(self.ctx, self.task_scheduler)
        s.status_message.connect(self.statusBar().showMessage)
        self.schedule = s
        return s
    def _build_monitoring(self):
        """Dựng màn Giám sát và nối dòng trạng thái của nó vào thanh dưới."""
        m = MonitoringTab(self.ctx, cowork=self.cowork, structure=self.structure,
                          task_scheduler=self.task_scheduler)
        m.status_message.connect(self.statusBar().showMessage)
        self.monitoring = m
        return m
    def current_screen_label(self) -> str:
        """Tên màn hình người dùng đang mở, dạng "Workspace ▸ Project".

        Trợ lý Hỗ trợ không nhìn được màn hình, nên "tôi đang ở đâu" là câu nó
        không thể tự trả lời — chuỗi này được ghép vào prompt của nó
        (``core/help_knowledge.py``).
        """
        row = self.pages.currentIndex()
        if not (0 <= row < len(self._nav_defs)):
            return ""
        page = tr(self._nav_defs[row][0])
        if row != self._ROW_WORKSPACE:
            return page
        sub = self.workspace.current_subtab()
        keys = {self.workspace._project_tab_idx: "workspace.tab_project",
                self.workspace._cowork_tab_idx: "workspace.tab_cowork",
                self.workspace._co4e_tab_idx: "workspace.tab_co4e",
                getattr(self.workspace, "_folder_tab_idx", -1): "workspace.tab_folder",
                self.workspace._graphrag_tab_idx: "workspace.tab_graphrag"}
        key = keys.get(sub)
        return f"{page} ▸ {tr(key)}" if key else page

    def help_context(self) -> str:
        """Ngữ cảnh sống cho Trợ lý Hỗ trợ: đang ở màn nào, và trên đó bấm được gì.

        Vì sao đọc từ WIDGET ĐANG CHẠY chứ không từ ``docs/screens/controls.json``:
        file đó được trích tự động nhưng đã cũ — 5/41 file trong đó không còn tồn
        tại, và nó không có file nào trong ``presentation/`` (chưa sinh lại sau
        refactor R08). Nạp nó vào prompt là dạy trợ lý về nút của những file đã
        bị xoá. Cây widget thật thì không bao giờ cũ được.
        """
        from PySide6.QtWidgets import QPushButton, QTabWidget

        from ...core.help_knowledge import screen_context

        page = self.pages.currentWidget()
        nhan = []
        if page is not None:
            for tabs in page.findChildren(QTabWidget):
                for i in range(tabs.count()):
                    if tabs.isTabVisible(i):
                        nhan.append(f"[tab] {tabs.tabText(i)}")
            for btn in page.findChildren(QPushButton):
                text = (btn.text() or "").replace("&", "").strip()
                if text and btn.isVisible() and btn.isEnabled():
                    nhan.append(text)
        # Bo trung, giu nguyen thu tu xuat hien tren man hinh.
        thay, gon = set(), []
        for n in nhan:
            if n not in thay:
                thay.add(n)
                gon.append(n)
        return screen_context(self.current_screen_label(), gon)

    def _ensure_page(self, row: int) -> None:
        """Build a lazy nav page on first visit and swap it in for its placeholder."""
        if not (0 <= row < len(self._built)) or self._built[row]:
            return
        builder = self._nav_defs[row][2]
        if builder is None:
            return
        real = builder()
        placeholder = self._page_widgets[row]
        self.pages.insertWidget(row, real)     # placeholder shifts to row+1
        self.pages.removeWidget(placeholder)
        placeholder.deleteLater()
        self._page_widgets[row] = real
        self._built[row] = True
    def _page_index(self, widget) -> int:
        """Chỉ số trang của một widget.

        So sánh theo danh tính trước khi hỏi ``QStackedWidget``: trang dựng lười
        vẫn còn là widget giữ chỗ cho tới lần mở đầu tiên, nên ``indexOf`` một
        mình sẽ trả về sai chỗ.
        """
        if widget is self.workspace:
            return self._ROW_WORKSPACE
        if self.dashboard is not None and widget is self.dashboard:
            return self._ROW_DASHBOARD
        if self.schedule is not None and widget is self.schedule:
            return self._ROW_SCHEDULE
        if self.monitoring is not None and widget is self.monitoring:
            return self._ROW_MONITORING
        return self.pages.indexOf(widget)
    def _goto(self, page: int, sub) -> None:
        """Chuyển sang một trang (và một sub-tab nếu có).

        Gác cổng project được đặt ở đây chứ không ở từng nơi gọi: dòng trên thanh
        menu bị làm mờ thì không bấm được, nhưng ``_goto`` còn được gọi từ RECENTS
        và từ lúc khôi phục phiên — trước đây nó mở thẳng sub-tab mà cổng đang
        đóng, thành ra trang hiện lên nhưng dải tab vẫn giấu nó đi.

        Vệt sáng trên thanh menu cũng cập nhật ở đây, để nó đi theo NỘI DUNG chứ
        không theo thứ vừa được bấm.
        """
        was_page = self.pages.currentIndex()
        self._ensure_page(page)                # build lazy page on first visit
        self.pages.setCurrentIndex(page)
        if page == self._ROW_WORKSPACE and was_page != page:
            self.workspace.refresh()           # refresh only when entering Workspace
        widget = self._page_widgets[page]
        if sub is not None and hasattr(widget, "select_subtab"):
            # Enforce the project gate here rather than at each entry point. A
            # greyed rail row cannot be clicked, but _goto is also reached from
            # RECENTS and from startup restore, and it used to open a sub-tab
            # the gate was holding shut — page shown, tab strip still hiding it.
            if hasattr(widget, "subtab_available") and not widget.subtab_available(sub):
                self.statusBar().showMessage(tr("app.nav.needs_project"), 4000)
            else:
                widget.select_subtab(sub)
        # Move the highlight with the content, however navigation was triggered —
        # a programmatic _goto used to leave it on whatever was clicked last.
        if not self._nav_building:
            self._select_nav_row(page, sub)
        self._update_dock_guard()
        # Switching pages updates which conversation is "current".
        self._refresh_history()
