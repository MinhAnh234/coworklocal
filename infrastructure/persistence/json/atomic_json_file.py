"""Ghi JSON kiểu không-hỏng-file — R02-T01.

Vấn đề đang có: ``config.py::save()`` gọi thẳng ``path.write_text(...)``. Hàm
đó mở file, cắt cụt về 0 byte, rồi mới ghi nội dung mới. Mất điện, tắt máy, hay
process bị kill đúng khoảng giữa thì file cấu hình còn lại **rỗng hoặc ghi dở**
— và người dùng mất toàn bộ cấu hình.

Cách làm ở đây theo đúng thứ tự bắt buộc:

1. Ghi vào file tạm cùng thư mục (phải cùng ổ đĩa thì bước 3 mới nguyên tử)
2. ``flush()`` + ``os.fsync()`` — ép dữ liệu xuống đĩa thật, không nằm trong
   bộ đệm của hệ điều hành
3. ``os.replace()`` — nguyên tử trên cả Windows lẫn POSIX

Bất kỳ lúc nào chết giữa chừng, file đích vẫn là **bản cũ nguyên vẹn**. Không
bao giờ có trạng thái ghi dở.

Phần đọc có chính sách phục hồi: file hỏng thì giữ lại thành ``.bad`` để còn
cứu tay, rồi trả về giá trị mặc định — hỏng cấu hình không được chặn khởi động,
đúng như ``config.py`` hiện tại đang làm.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class AtomicJsonFile:
    """Một file JSON, đọc ghi an toàn.

    >>> f = AtomicJsonFile(Path("cau_hinh.json"))
    >>> f.write({"theme": "dark"})
    >>> f.read(default={})
    {'theme': 'dark'}
    """

    def __init__(self, path: Path, *, indent: int = 2):
        """Trỏ vào một file JSON. ``indent`` giữ file còn đọc và so sánh được bằng mắt
        trong git diff.
        """
        self.path = Path(path)
        self.indent = indent

    # ---- đọc ------------------------------------------------------------
    def read(self, default: Any = None) -> Any:
        """Nội dung file, hoặc ``default`` nếu chưa có / hỏng.

        Không ném lỗi. File hỏng được đổi tên thành ``<tên>.bad-<thời điểm>``
        rồi mới trả mặc định — hỏng thì cứu được, chứ đừng ghi đè im lặng.
        """
        if not self.path.exists():
            return default
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._quarantine()
            return default
        except OSError:
            # Không đọc được (khoá file, mất quyền) — KHÔNG cách ly, vì file
            # có thể vẫn tốt nguyên.
            return default

    def _quarantine(self) -> Path | None:
        """Đổi tên file JSON hỏng thành ``.bad-<mốc thời gian>`` thay vì xoá.

        Giữ lại để còn cứu dữ liệu, và để lần ghi sau bắt đầu từ file sạch.
        """
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = self.path.with_suffix(self.path.suffix + f".bad-{stamp}")
        try:
            os.replace(self.path, target)
            return target
        except OSError:
            return None

    # ---- ghi ------------------------------------------------------------
    #: Số lần thử lại ``os.replace`` và khoảng nghỉ giữa các lần (giây).
    _REPLACE_TRIES = 6
    _REPLACE_BACKOFF = 0.02

    @classmethod
    def _replace_ben_bi(cls, src: Path, dst: Path) -> None:
        """``os.replace`` có thử lại — bắt buộc trên Windows.

        MoveFileEx trả ERROR_ACCESS_DENIED khi có tiến trình khác đang giữ
        handle lên nguồn hoặc đích. Trên Windows thật thì gần như luôn là
        Defender hoặc Search Indexer quét file vừa tạo, giữ handle vài chục
        mili-giây rồi nhả. Không phải lỗi quyền thật, thử lại là hết.

        Đo trên máy dev 25/08: hỏng 1 trong 7 lượt chạy 20 lần ghi, tức
        khoảng 1 trên 140 lần lưu. Không có vòng này thì người dùng thỉnh
        thoảng bấm Lưu là văng lỗi mà không tài nào tái hiện.

        POSIX không có kiểu hỏng này nên vòng lặp chạy đúng một lượt.
        """
        for lan in range(cls._REPLACE_TRIES):
            try:
                os.replace(src, dst)
                return
            except PermissionError:
                if lan == cls._REPLACE_TRIES - 1:
                    raise
                time.sleep(cls._REPLACE_BACKOFF * (2 ** lan))

    def write(self, data: Any) -> None:
        """Ghi ``data``. Hoặc thành công trọn vẹn, hoặc file cũ còn nguyên."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, indent=self.indent, ensure_ascii=False)

        # File tạm phải nằm CÙNG thư mục: os.replace chỉ nguyên tử trong cùng
        # một hệ thống tệp. Để ở %TEMP% là có thể rơi sang ổ khác và biến
        # thành copy + delete — mất luôn tính nguyên tử.
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=f".{self.path.name}.", suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())     # xuống đĩa thật, không chỉ vào bộ đệm
            self._replace_ben_bi(tmp, self.path)   # nguyên tử, có thử lại
        except BaseException:
            # Kể cả KeyboardInterrupt/SystemExit cũng phải dọn file tạm, đừng
            # để rác .tmp nằm lại cạnh file cấu hình.
            tmp.unlink(missing_ok=True)
            raise

    # ---- tiện ích -------------------------------------------------------
    def exists(self) -> bool:
        """File đã tồn tại trên đĩa chưa."""
        return self.path.exists()

    def __repr__(self) -> str:
        """Biểu diễn ngắn kèm đường dẫn, cho log và thông báo lỗi."""
        return f"AtomicJsonFile({self.path})"
