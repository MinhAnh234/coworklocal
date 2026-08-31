"""Đọc/ghi file lịch sử run của Co4E — tách khỏi ``co4e_workflow_service.py``.

``Co4EWorkflowService`` lo vòng đời các run đang chạy; chỗ này lo đúng một
việc: đưa ``RunRecord`` ra đĩa và lấy lại được. Tách ra vì hành vi đọc/ghi ở
đây có những ràng buộc rất riêng — được ghi lại nguyên vẹn bên dưới — mà trộn
lẫn vào file điều phối thì không ai đọc tới.

DTO ở ``domain/workflows/run_record.py`` không được chạm đĩa, nên việc này
nằm ở tầng application chứ không nằm trong domain.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from ...domain.workflows.run_record import RunRecord
from ...infrastructure.persistence.json.atomic_json_file import AtomicJsonFile

#: Giữ N run gần nhất trên đĩa. Lịch sử chỉ để người dùng nhìn lại, không
#: phải sổ kiểm toán — để nó lớn vô hạn thì mỗi lần lưu lại phải tuần tự hoá
#: cả file, và lần lưu ấy nằm ngay trên đường đi của mọi sự kiện tiến độ.
HISTORY_CAP = 500


class RunHistoryStore:
    """Một file JSON chứa lịch sử run, kèm hai quy ước phải giữ nguyên.

    **Không cách ly file hỏng.** Bản đầu dùng ``AtomicJsonFile.read()``, nhưng
    review thấy nó đổi hành vi thật so với ``Co4ERunManager`` cũ: gặp JSON
    hỏng, ``AtomicJsonFile.read()`` ĐỔI TÊN file thành ``<tên>.bad-<mốc>`` rồi
    mới trả về mặc định, trong khi bản cũ chỉ bắt lỗi và ĐỂ NGUYÊN file tại
    chỗ. Đó là thay đổi quan sát được trên đĩa mà không test nào khoá lại và
    không có chú thích báo trước — Lâm (N3) quyết ngày 24/08: giữ hành vi cũ.
    Vì thế :meth:`load` đọc thủ công bằng ``json.loads``.

    **Ghi hỏng không được làm vỡ luồng gọi.** :meth:`save` nuốt ``OSError``,
    đúng như ``core/co4e_run_manager.py::_save_history``. Nó nằm trên đường đi
    của mọi hook tiến độ (``_on_event``/``_on_finished``/``_on_failed``); để
    lỗi ghi đĩa (đầy đĩa, mất quyền) ném ra là vỡ cả lượt xử lý sự kiện đang
    chạy, chỉ vì lịch sử lần này không lưu được. Người dùng vẫn thấy Flow
    Status đúng trong phiên hiện tại, chỉ là bản ghi trên đĩa lùi một bước.

    Ghi thì vẫn qua ``AtomicJsonFile``: bản tự viết bằng tmp + ``replace``
    thiếu ``fsync`` (dữ liệu có thể còn trong bộ đệm khi mất điện) và
    ``Path.replace`` thỉnh thoảng bị Defender từ chối trên Windows.
    """

    def __init__(self, path: Path):
        """Trỏ vào một file JSON. Chưa tồn tại cũng không sao — :meth:`load` coi như
        lịch sử rỗng và :meth:`save` tự tạo thư mục cha.
        """
        self.path = Path(path)

    def load(self) -> Tuple[Dict[str, RunRecord], int]:
        """Đọc lịch sử; trả về ``({id: RunRecord}, số thứ tự lớn nhất đã dùng)``.

        Số thứ tự trả kèm để bên gọi sinh id tiếp theo không đụng vào id đã có
        trong lịch sử — không có nó thì sau mỗi lần khởi động lại, ``run1``
        mới sẽ ghi đè ``run1`` cũ.

        File không có, không đọc được, hay JSON hỏng đều trả về rỗng: mất lịch
        sử là chuyện chấp nhận được, chặn ứng dụng khởi động thì không. Từng
        bản ghi hỏng cũng bị bỏ riêng lẻ, để một dòng lỗi không kéo theo cả
        file.
        """
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}, 0

        runs: Dict[str, RunRecord] = {}
        max_seq = 0
        for rec in data.get("runs", []):
            try:
                record = RunRecord.from_dict(rec)
            except Exception:
                continue
            if not record.id:
                continue
            runs[record.id] = record
            if record.id.startswith("run") and record.id[3:].isdigit():
                max_seq = max(max_seq, int(record.id[3:]))
        return runs, max_seq

    def save(self, runs: List[RunRecord]) -> None:
        """Ghi ``HISTORY_CAP`` run gần nhất xuống đĩa, ghi nguyên tử.

        Lỗi ghi bị nuốt có chủ ý — xem docstring của lớp.
        """
        payload = {"runs": [r.to_dict() for r in runs[-HISTORY_CAP:]]}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            AtomicJsonFile(self.path).write(payload)
        except OSError:
            pass


__all__ = ["RunHistoryStore", "HISTORY_CAP"]
