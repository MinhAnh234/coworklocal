"""Bản ghi "một lần chạy flow" — DTO thuần Python cho tầng domain.

Bối cảnh: ``Co4ERunManager``/``RunHandle`` cũ (``core/co4e_run_manager.py``)
trộn ba việc vào một ``QObject``: (1) dữ liệu một run cần nhớ để hiện Flow
Status, (2) logic chạy job trên ``AgentWorker``/``QThread``, và (3) logic
đọc/ghi lịch sử ra đĩa. Tách phần (1) ra thành ``RunRecord`` ở đây giúp nó độc
lập với Qt và với việc đọc/ghi đĩa — đúng quy ước ``domain/__init__.py``: domain
không được biết PySide6 tồn tại và không được chạm đĩa/mạng. Phần (2) và (3)
chuyển sang ``application/workflows/co4e_workflow_service.py``
(``Co4EWorkflowService``), nơi được phép import ``core/`` và làm việc với đĩa.

Vì sao trường ``wf`` là dict thô chứ không phải đối tượng ``Workflow``: lớp
``Workflow`` sống ở ``core/co4e.py``, và việc dựng nó từ/thành dict
(``workflow_to_dict``/``workflow_from_dict``) nằm trong module đó. Domain
không được import ``cowork_local.core.*``, nên ``RunRecord`` giữ nguyên đúng
hình dạng dữ liệu mà bản ghi lịch sử đã có sẵn trên đĩa hôm nay: một dict thô
(kết quả ``workflow_to_dict``) hoặc ``None``. Việc quy đổi dict <-> đối tượng
``Workflow`` là việc của tầng application, nơi được phép import ``core``.

Quirk giữ nguyên có chủ ý — đã bị "đóng đinh" bởi
``tests/characterization/test_co4e_run_manager_behavior.py`` (quirk #1 và #7
trong docstring đầu file đó, xem thêm ``RunHandle.to_record``/``from_record``
gốc) — ĐỪNG "dọn" các chỗ này khi đọc code dưới đây, chúng trông như bug nhưng
là hành vi đã được test khẳng định:
  * ``total`` âm bị ``max(0, total)`` kẹp về 0 ngay lúc khởi tạo, không giữ
    nguyên giá trị âm.
  * ``from_dict()`` đổi ``status == "running"`` đọc từ đĩa thành ``"stopped"``
    (lý do: app tắt giữa lúc một run đang "running" thì worker của nó đã mất
    theo, nên đọc lại không còn coi là đang chạy) — nhưng ``to_dict()`` vẫn ghi
    đúng ``"running"`` xuống đĩa tại thời điểm lưu. Đây là một round-trip
    *không đối xứng* có chủ ý.
  * ``from_dict({})``/``from_dict(None)`` mặc định ``status`` là ``"done"``
    (không phải ``"running"``) — nên KHÔNG bị nhánh phía trên đổi thành
    "stopped".

SEAM · dựng 2026-08-25 · chưa nối dây (F-05)
------------------------------------------------------------
Được nối khi: ``Co4EWorkflowService`` được nối dây — cùng điều kiện với seam ấy.
Để dormant thì sao: DTO này và ``core/co4e_run_manager.py::RunHandle`` là
hai bản của cùng một thứ; chỉ một bản được phép ở lại.

Cổng ``scripts/check_orphan_modules.py`` đếm tuổi seam từ ngày trên
và nhắc khi quá ``SEAM_MAX_AGE_DAYS``. Đổi nội dung dòng đó thì cổng
đọc theo — đừng sửa ngày để làm im lời nhắc.
"""
from __future__ import annotations

from typing import Dict, Optional


class RunRecord:
    """DTO domain: trạng thái sống của một lần chạy flow, thuần dữ liệu.

    Vai trò: đây là "danh từ" mà ``Co4EWorkflowService`` (application/) đọc/ghi
    và mà UI Flow Status hiển thị — không có hành vi chạy worker, không đọc/ghi
    đĩa. Nó ở tầng domain vì đây là quy tắc nghiệp vụ ổn định (hình dạng một
    lần chạy flow cần nhớ những gì) độc lập với Qt lẫn với cơ chế lưu trữ.
    """

    def __init__(self, run_id: str, wf_id: str, name: str, total: int,
                 plan_mode: bool, manual: bool, created_by: str = "", created_at: str = "",
                 project_id: str = ""):
        """Dựng một bản ghi run. ``total`` âm bị kẹp về 0 — quirk cố ý giữ nguyên từ
        ``Co4ERunManager`` cũ, xem docstring đầu file.
        """
        self.id = run_id
        self.wf_id = wf_id
        self.name = name
        self.project_id = project_id   # workspace run này thuộc về (Flow Status lọc theo project)
        self.total = max(0, total)     # quirk cố ý: total âm bị kẹp về 0, xem docstring đầu file
        self.done = 0
        self.status = "running"        # running | done | error | stopped
        self.plan_mode = plan_mode
        self.manual = manual
        self.created_by = created_by
        self.created_at = created_at
        self.error = ""
        self.node_status: Dict[str, str] = {}
        self.wf: Optional[dict] = None   # snapshot workflow dạng dict thô (xem docstring đầu file)
        self.out_dir = ""                # thư mục workspace mà run này ghi file vào

    @property
    def running(self) -> bool:
        """Run này còn đang chạy không."""
        return self.status == "running"

    def progress_text(self) -> str:
        """Chuỗi tiến độ để hiện lên bảng: "3/7" khi biết tổng số bước, còn không thì
        hiện trạng thái.
        """
        return f"{self.done}/{self.total}" if self.total else self.status

    # ---- (de)serialization --------------------------------------------
    def to_dict(self) -> dict:
        """Hình dạng bản ghi lịch sử trên đĩa.

        PHẢI khớp đúng bộ khoá mà ``RunHandle.to_record()`` gốc
        (``core/co4e_run_manager.py``) đang ghi hôm nay — file JSON lịch sử cũ
        và mới dùng chung một định dạng trong lúc cả hai lớp còn chạy song
        song (bản cũ chưa bị xoá).
        """
        return {
            "id": self.id, "wf_id": self.wf_id, "name": self.name,
            "total": self.total, "done": self.done, "status": self.status,
            "plan_mode": self.plan_mode, "manual": self.manual,
            "created_by": self.created_by, "created_at": self.created_at,
            "error": self.error, "node_status": dict(self.node_status),
            "wf": self.wf, "out_dir": self.out_dir, "project_id": self.project_id,
        }

    @classmethod
    def from_dict(cls, rec: dict) -> "RunRecord":
        """Dựng lại một run từ dict đọc ở file lịch sử.

        Mọi trường đều có mặc định và được ép kiểu: file lịch sử là dữ liệu cũ có
        thể thiếu trường mà bản mới đã thêm.
        """
        rec = dict(rec or {})
        r = cls(str(rec.get("id", "")), str(rec.get("wf_id", "")),
                 rec.get("name", ""), int(rec.get("total", 0) or 0),
                 bool(rec.get("plan_mode")), bool(rec.get("manual")),
                 created_by=rec.get("created_by", ""), created_at=rec.get("created_at", ""))
        r.done = int(rec.get("done", 0) or 0)
        r.status = rec.get("status", "done")
        # quirk cố ý (xem docstring đầu file): round-trip không đối xứng —
        # "running" đọc lại từ đĩa luôn bị chốt thành "stopped".
        if r.status == "running":
            r.status = "stopped"
        r.error = rec.get("error", "")
        r.node_status = dict(rec.get("node_status") or {})
        r.out_dir = rec.get("out_dir", "")
        r.project_id = rec.get("project_id", "")
        # Giữ nguyên dict thô -- KHONG parse thanh doi tuong Workflow o day (do
        # la viec cua tang application, xem docstring dau file).
        r.wf = rec.get("wf")
        return r
