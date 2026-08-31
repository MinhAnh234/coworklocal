"""Đánh số phiên bản và chuyển đổi cấu hình — R02-T06.

Hôm nay ``config.json`` không có số phiên bản. Nghĩa là không có cách nào biết
file trên đĩa thuộc thời nào, và mọi thay đổi hình dạng phải xử lý bằng cách
đoán — ``config.py::_migrate_connectors()`` chính là một ví dụ: nó đoán "có
khoá ``office`` nghĩa là file cũ".

Ở đây đặt luật rõ:

* File có ``schema_version``. Thiếu ⇒ coi là **1** (mọi file đang tồn tại).
* Mỗi bước nâng cấp là một hàm ``v1 -> v2``, chạy tuần tự, không nhảy cóc.
* **Sao lưu trước khi nâng cấp.** Người dùng lùi về bản app cũ thì bản cũ đọc
  file mới có thể hỏng — phải còn đường về.
* Chỉ nâng, không hạ. File mới hơn app thì báo và dùng nguyên trạng, không cố
  đoán ngược.

Bước v1→v2 đầu tiên đi kèm R02-T05: gỡ ``api_key`` khỏi đĩa, đẩy vào
``SecretStore``.
"""
from __future__ import annotations

import copy
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict

from ..secrets.secret_store import SecretStore, provider_key

log = logging.getLogger(__name__)

#: Phiên bản app hiện đang ghi ra.
CURRENT_VERSION = 2

#: Thiếu ``schema_version`` ⇒ file có từ trước khi đánh số.
ASSUMED_VERSION = 1


def read_version(data: Dict[str, Any]) -> int:
    """Phiên bản schema của một dict cấu hình.

    File cũ chưa có trường này thì coi như ``ASSUMED_VERSION`` — đó chính là
    phiên bản trước khi trường được thêm vào.
    """
    try:
        return int(data.get("schema_version", ASSUMED_VERSION))
    except (TypeError, ValueError):
        return ASSUMED_VERSION


def _v1_to_v2(data: Dict[str, Any], secrets: SecretStore | None) -> Dict[str, Any]:
    """Chuyển API key từ file sang kho bí mật — R02-T05.

    Không có kho bí mật thì **không chuyển**: thà để khoá nằm nguyên trong file
    còn hơn xoá đi rồi người dùng mất khoá mà không hiểu vì sao. File giữ
    nguyên phiên bản 1, lần chạy sau trên máy có keyring sẽ chuyển.
    """
    if secrets is None or not getattr(secrets, "available", True):
        log.info("bỏ qua v1→v2: máy này chưa có kho bí mật dùng được")
        return data

    out = copy.deepcopy(data)
    moved = []
    for name, conf in (out.get("providers") or {}).items():
        if not isinstance(conf, dict):
            continue
        key = (conf.get("api_key") or "").strip()
        # "ollama" là giá trị bù nhìn — Ollama đòi có api_key nhưng bỏ qua nội
        # dung. Đẩy nó vào keyring chỉ tổ rác.
        if not key or key == "ollama":
            continue
        secrets.set(provider_key(name), key)
        conf["api_key"] = ""
        moved.append(name)

    out["schema_version"] = 2
    if moved:
        log.info("đã chuyển API key sang kho bí mật: %s", ", ".join(moved))
    return out


#: {phiên bản nguồn: hàm nâng lên phiên bản kế tiếp}
STEPS: Dict[int, Callable[[Dict[str, Any], SecretStore | None], Dict[str, Any]]] = {
    1: _v1_to_v2,
}


def backup(path: Path) -> Path | None:
    """Chép file trước khi nâng cấp. Trả về đường dẫn bản sao."""
    if not path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_suffix(path.suffix + f".v{stamp}.bak")
    try:
        shutil.copy2(path, target)
        return target
    except OSError as exc:
        log.warning("không sao lưu được %s: %s", path, exc)
        return None


def migrate(data: Dict[str, Any], *, secrets: SecretStore | None = None,
            path: Path | None = None) -> tuple[Dict[str, Any], bool]:
    """Nâng ``data`` lên :data:`CURRENT_VERSION`.

    Trả về ``(dữ_liệu, có_đổi_không)``. ``có_đổi_không`` là False thì chỗ gọi
    khỏi phải ghi lại đĩa.
    """
    version = read_version(data)

    if version > CURRENT_VERSION:
        # App cũ gặp file mới. Đoán ngược là cách nhanh nhất để mất dữ liệu.
        log.warning("config phiên bản %s mới hơn app (%s) — dùng nguyên trạng",
                    version, CURRENT_VERSION)
        return data, False

    if version == CURRENT_VERSION:
        return data, False

    if path is not None:
        backup(path)

    changed = False
    while version < CURRENT_VERSION:
        step = STEPS.get(version)
        if step is None:
            log.warning("thiếu bước nâng cấp từ phiên bản %s — dừng", version)
            break
        data = step(data, secrets)
        new_version = read_version(data)
        if new_version <= version:
            # Bước không nâng được phiên bản (ví dụ v1→v2 bỏ qua vì chưa có
            # keyring). Dừng, đừng lặp vô hạn.
            break
        version = new_version
        changed = True

    return data, changed
