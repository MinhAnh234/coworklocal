"""Vỏ chuyển tiếp — R08-T02.

Phần thân đã chuyển sang ``presentation/chat/composer_widget.py`` (thanh công
cụ), ``chat_input_box.py`` (ô nhập) và ``composer_mime.py`` (đọc dữ liệu
dán/kéo-thả).

Bốn hàm ``_save_pasted_image``/``_is_local_*_command``/``_paths_from_mime``
được nối lại dưới đúng tên cũ: chúng là tên riêng tư nên không thuộc API công
khai, nhưng file này vốn cũng đang chuyển tiếp ``_Input`` và ``_SkillPopup``
— nối tiếp một nửa thì vỏ chuyển tiếp không còn trung thực với bản gốc.
"""
from __future__ import annotations

from ..presentation.chat.chat_input_box import _Input, _SkillPopup  # noqa: F401
from ..presentation.chat.composer_mime import (  # noqa: F401
    is_local_agent_command as _is_local_agent_command,
    is_local_skill_command as _is_local_skill_command,
    paths_from_mime as _paths_from_mime,
    save_pasted_image as _save_pasted_image,
)
from ..presentation.chat.composer_widget import (  # noqa: F401
    Composer,
)
