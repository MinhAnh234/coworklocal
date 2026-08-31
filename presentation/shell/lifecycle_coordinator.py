"""Vòng đời cửa sổ chính — R08-T10.

Bóc từ ``app.py::MainWindow``. Hai việc, đều không phải việc của giao diện:

1. **Canh cửa sổ theo màn hình đang đứng.** Người dùng có hai màn khác độ phân
   giải và khác tỉ lệ phóng; kéo cửa sổ sang màn kia là vùng làm việc đổi. Đây
   là số học thuần, không đụng widget nào ngoài chính cửa sổ.
2. **Tắt cho sạch.** Dừng bộ lập lịch, dừng mọi lượt chạy còn dở, ngắt tiến
   trình MCP. Thiếu một bước là để lại tiến trình con chạy mồ côi sau khi
   người dùng đã thoát.

Các hàm ``closeEvent``/``moveEvent``/``resizeEvent`` vẫn phải nằm ở lớp cửa sổ
— Qt gọi thẳng vào đó — nhưng phần quyết định thì ở đây.
"""
from __future__ import annotations

from PySide6.QtGui import QGuiApplication

#: Cửa sổ chiếm bao nhiêu phần màn hình khi mở lần đầu.
SCREEN_SHARE_W, SCREEN_SHARE_H = 0.80, 0.85

#: Chừa mép để cửa sổ không đụng thanh tác vụ.
MARGIN = 60

#: Kích thước tối thiểu mong muốn — vẫn phải nhỏ hơn màn hình thật.
MIN_W, MIN_H = 820, 520


class LifecycleCoordinator:
    """Vòng đời cửa sổ: canh vừa màn hình, theo dõi đổi màn hình, và quyết định
    đóng cửa sổ là thoát hẳn hay thu về khay.
    """
    def __init__(self, window):
        """Theo dõi màn hình cửa sổ đang nằm trên, để khôi phục đúng vị trí và tỉ lệ khi
        mở lại.
        """
        self.window = window
        self._last_screen = None

    # ---- canh theo màn hình ----------------------------------------------

    def fit_to_screen(self, want_w: int, want_h: int) -> None:
        """Canh cửa sổ vừa vùng làm việc của màn hình đang chứa nó."""
        w = self.window
        screen = w.screen() or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        if avail is None:
            w.resize(want_w, want_h)
            return

        # Lấy một phần màn hình: không bao giờ nhỏ hơn kích thước yêu cầu, cũng
        # không bao giờ lớn hơn thứ màn hình hiển thị nổi.
        width = min(max(want_w, int(avail.width() * SCREEN_SHARE_W)),
                    avail.width() - MARGIN)
        height = min(max(want_h, int(avail.height() * SCREEN_SHARE_H)),
                     avail.height() - MARGIN)
        self._apply_minimum(avail)
        w.resize(max(width, 1), max(height, 1))

        frame = w.frameGeometry()
        frame.moveCenter(avail.center())
        w.move(frame.topLeft())

    def screen_maybe_changed(self) -> bool:
        """Gọi khi cửa sổ bị di chuyển. Trả True nếu đúng là đã đổi màn hình.

        Trả về bool để chỗ gọi biết có cần xếp lại mấy thứ nổi hay không —
        kéo cửa sổ trong cùng một màn thì không cần làm gì cả.
        """
        w = self.window
        screen = w.screen()
        if screen is self._last_screen:
            return False
        self._last_screen = screen
        avail = screen.availableGeometry() if screen else None
        if avail is not None:
            self._apply_minimum(avail)
        return True

    def _apply_minimum(self, avail) -> None:
        # Kích thước tối thiểu không bao giờ được vượt quá thứ màn hình hiển
        # thị nổi — nếu không thì cửa sổ không thu nhỏ vừa màn được nữa.
        """Đặt kích thước tối thiểu, nhưng không bao giờ vượt quá thứ màn hình hiển thị
        nổi — vượt thì cửa sổ không thu nhỏ vừa màn được nữa.
        """
        self.window.setMinimumSize(min(MIN_W, avail.width() - MARGIN),
                                   min(MIN_H, avail.height() - MARGIN))

    # ---- đóng và tắt ------------------------------------------------------

    def should_keep_running(self) -> bool:
        """Đóng cửa sổ có nghĩa là chạy nền tiếp, hay là thoát hẳn?

        Chạy nền tiếp chỉ khi có khay hệ thống để quay lại — không có khay mà
        vẫn ẩn đi thì người dùng mất luôn đường vào app.
        """
        w = self.window
        if w.tray is None or w._really_quit:
            return False
        return bool(w.ctx.config.data.get("tray", {}).get("minimize_on_close", True))

    def shutdown(self) -> None:
        """Dừng mọi thứ đang chạy. Thứ tự có ý nghĩa: bộ lập lịch trước, để nó
        không kịp khởi động thêm việc mới trong lúc ta đang dừng việc cũ."""
        w = self.window
        w.task_scheduler.stop()          # dừng luôn các task đã lên lịch
        if getattr(w, "routing_scheduler", None) is not None:
            w.routing_scheduler.stop()

        for tab in (w.cowork,):
            for worker in tab.active_workers():
                if worker.isRunning():
                    worker.request_stop()
                    worker.wait(1500)

        if hasattr(w.structure, "stop_cmem_ui"):
            w.structure.stop_cmem_ui()

        # Không bao giờ để lại tiến trình MCP đã kết nối chạy mồ côi.
        w.ctx.stop_mcp_connections()
