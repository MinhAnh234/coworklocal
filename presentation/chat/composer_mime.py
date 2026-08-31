"""Đọc dữ liệu dán/kéo-thả vào ô soạn tin, và nhận diện lệnh trả lời tại chỗ.

Tách khỏi ``composer_widget.py`` vì hai bên đều cần: ô nhập
(``chat_input_box.py::_Input``) bắt sự kiện dán và thả, còn ``Composer`` bọc
ngoài quyết định tệp nào được nhận. Đợt tách widget (R08) để mấy hàm này ở lại
trong ``composer_widget.py`` trong khi phần gọi chúng đã sang
``chat_input_box.py`` — thành ra dán hay thả tệp vào ô chat đều ném
``NameError`` (F-12). Đặt ở một module thứ ba là chỗ duy nhất không lặp lại
được lỗi ấy.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import List

from PySide6.QtGui import QImage

from ...config import CONFIG_DIR

#: ``/skill`` hoặc ``/skill:<tên>`` đứng một mình — không có phần yêu cầu theo sau.
_BARE_SKILL = re.compile(r"^/skill:[\w\-.]+$")

#: ``/agent`` hoặc ``/agent:<tên>`` đứng một mình.
_BARE_AGENT = re.compile(r"^/agent:[\w\-.]+$")


def save_pasted_image(image) -> str | None:
    """Ghi ảnh vừa dán/kéo vào thư mục cấu hình; trả về đường dẫn, lỗi thì ``None``.

    Tên tệp lấy tới phần nghìn giây vì dán liên tiếp trong cùng một giây là
    chuyện thường — tính tới giây thôi là ảnh sau đè ảnh trước.
    """
    try:
        if not isinstance(image, QImage) or image.isNull():
            return None
        folder = CONFIG_DIR / "pasted"
        folder.mkdir(parents=True, exist_ok=True)
        name = "paste-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3] + ".png"
        path = folder / name
        if image.save(str(path), "PNG"):
            return str(path)
    except Exception:  # noqa: BLE001 — dán ảnh hỏng không đáng làm vỡ ô nhập
        return None
    return None


def is_local_skill_command(text: str) -> bool:
    """``/skill`` (liệt kê) hoặc ``/skill:<tên>`` (chọn) — lệnh trả lời ngay tại chỗ.

    Những lệnh này phải chạy được cả khi đang có lượt chat chạy dở, nên chúng đi
    thẳng chứ không vào hàng đợi. Khác với ``/skill:<tên> <yêu cầu>``: cái đó là
    một lượt chat thật và phải xếp hàng như mọi lượt khác.
    """
    t = (text or "").strip()
    return t == "/skill" or bool(_BARE_SKILL.match(t))


def is_local_agent_command(text: str) -> bool:
    """Như :func:`is_local_skill_command` nhưng cho lệnh ``/agent``."""
    t = (text or "").strip()
    return t == "/agent" or bool(_BARE_AGENT.match(t))


def paths_from_mime(md) -> List[str]:
    """Rút danh sách đường dẫn tệp từ dữ liệu kéo-thả/dán.

    Ưu tiên đường dẫn tệp thật; chỉ khi không có tệp nào mới xét tới ảnh trong
    bộ nhớ tạm và ghi nó ra tệp. Thứ tự này quan trọng: kéo một tệp ảnh từ
    Explorer thì dữ liệu mang CẢ đường dẫn lẫn ảnh xem trước, và ta muốn tệp
    gốc chứ không muốn một bản sao PNG.
    """
    paths: List[str] = []
    if md.hasUrls():
        for u in md.urls():
            if u.isLocalFile():
                paths.append(u.toLocalFile())
    if not paths and md.hasImage():
        p = save_pasted_image(md.imageData())
        if p:
            paths.append(p)
    return paths


__all__ = ["paths_from_mime", "save_pasted_image",
           "is_local_skill_command", "is_local_agent_command"]
