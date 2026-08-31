"""Factory dựng tab Co4E Studio cho bootstrap.py — điểm nối duy nhất giữa
lớp Qt cũ (``cowork_local.ui.co4e_tab.Co4ETab``, đang chờ tách nhỏ) và phần
lắp ráp ứng dụng.

Vì sao có file này dù chưa tách xong widget con nào: quy ước #2 của team là
"nộp factory, không tự lắp vào app" — người giữ bootstrap.py (Nam, N1) cần
chốt được chữ ký sớm (hạn lắp 28/08) trong khi phần thân bên trong Co4E Studio
vẫn còn đang được tách dần sang presentation/co4e/*.py và
application/workflows/co4e_workflow_service.py.

Chữ ký ``build_co4e_tab(ctx, workflow_service)`` KHÔNG có default cho
``workflow_service``: nếu cho default None, lúc bootstrap.py gọi thiếu tham số
vẫn hợp lệ cú pháp, dựng ra tab không có service, và lỗi chỉ nổ muộn bên trong
widget khi người dùng bấm Run — thay vì nổ ngay tại dòng lắp ráp. Chưa có
service thật thì bên gọi tự truyền fake (xem tests/fakes/fake_co4e_workflow_service.py).

QUAN TRỌNG — đây KHÔNG phải bản cuối: thân hàm hiện tại chỉ bọc nguyên
``Co4ETab`` cũ 1:1 và CHƯA dùng đến ``workflow_service``. Chữ ký thì giữ
nguyên — đó là hợp đồng với bootstrap.py.

Cập nhật 25/08 — cả 6 widget con (skills/agent list, canvas, node property,
run control, chat view) ĐÃ tách xong khỏi ``ui/co4e_tab.py`` và ``Co4ETab``
NỘI BỘ đã lắp ráp lại từ các panel mới đó (xem ``ui/co4e_tab.py``:
``_build_sidebar``/``_build_runs_page``/``_build_chat``) — phần "lắp ráp từ
widget đã tách" coi như xong. PHẦN CÒN LẠI — đổi ``Co4ETab`` để thật sự dùng
``workflow_service`` thay cho ``core/co4e_run_manager.py::Co4ERunManager`` nội
bộ — ĐÃ QUYẾT ĐỊNH HOÃN LẠI thành một task riêng, không làm chung với việc
tách widget: ``self.manager`` (``Co4ERunManager``) bị dùng ở 24 chỗ trong
``Co4ETab``, và khác với các bước tách widget (chỉ động tới phần DỰNG UI),
việc đổi sang ``Co4EWorkflowService`` đòi phải (1) viết một adapter Qt thật
(``WorkflowRunner``) bọc ``AgentWorker``/``QThread`` — hiện chưa tồn tại, và
(2) sửa mọi chỗ đọc ``RunHandle.wf`` như một đối tượng ``Workflow`` (ví dụ
``ui/co4e_tab.py`` dòng ~1330: ``h.wf.nodes``) thành đọc dict thô
(``RunRecord.wf``) — tức là chạm trực tiếp vào đúng luồng gọi AI thật/QThread
mà mọi bước tách widget trước đó đã cố tình né. Trước khi đổi, cần lưới an
toàn riêng (characterization đầy đủ cho ``Co4ERunManager``) — xem
``tests/characterization/test_co4e_run_manager_behavior.py`` hiện có cho một
phần hành vi, chưa phủ hết 24 điểm gọi này.

SEAM · dựng 2026-08-25 · chưa nối dây (F-05)
------------------------------------------------------------
Được nối khi: ``presentation/shell/bootstrap.py`` gọi ``build_co4e_tab`` thay cho việc dựng thẳng ``ui.co4e_tab.Co4ETab``.
Để dormant thì sao: Hạn lắp đã ghi trong file là 28/08 và đã qua. Factory
không ai gọi thì chữ ký của nó không còn được kiểm chứng bởi bất cứ đường
chạy thật nào.

Cổng ``scripts/check_orphan_modules.py`` đếm tuổi seam từ ngày trên
và nhắc khi quá ``SEAM_MAX_AGE_DAYS``. Đổi nội dung dòng đó thì cổng
đọc theo — đừng sửa ngày để làm im lời nhắc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


def build_co4e_tab(ctx, workflow_service) -> QWidget:
    """Factory tạo tab Co4E Studio.

    Vai trò: hàm lắp ráp ở tầng presentation, là API ổn định mà
    bootstrap.py gọi để lấy widget tab Co4E — không phải nơi chứa logic.
    Logic thật vẫn nằm ở ``cowork_local.ui.co4e_tab.Co4ETab`` cho tới khi
    được tách hết sang các module trong presentation/co4e/.

    ``workflow_service`` chưa được dùng ở bản này (Co4ETab cũ tự quản lý
    state qua Co4ERunManager nội bộ). Tham số vẫn bắt buộc ngay từ bây giờ
    để chữ ký không phải đổi ở lượt tách kế tiếp — chỉ thân hàm đổi.
    """
    # Import trong thân hàm, không ở đầu module: ui/co4e_tab.py hiện kéo theo
    # toàn bộ cây widget Co4E Studio cũ (canvas, run manager, chat view...).
    # Đặt ở đây để module factory này nhẹ khi bootstrap.py chỉ cần đọc chữ ký/
    # import hàm mà chưa gọi nó — chi phí load Qt widget nặng chỉ trả khi
    # build_co4e_tab() thực sự được gọi. Không phải để né circular import
    # (ui/co4e_tab.py không import ngược presentation/co4e/).
    from ...ui.co4e_tab import Co4ETab

    return Co4ETab(ctx)
