"""Mục Tham số trong Cài đặt — R08-T07.

Bóc từ ``ui/settings_dialog.py``. Ba nhóm con: đính kèm, cấu trúc/GraphRAG,
và giới hạn tài nguyên sandbox.

Lưu ý khi đọc: nhóm thứ ba **hiện** ở đây nhưng **lưu** vào ``agent_security``
chứ không phải một khoá riêng — nó vốn nằm ở mục Bảo mật sandbox rồi được dời
sang đây cho gần các con số khác. Chỗ hiện và chỗ lưu khác nhau, đừng gộp.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QSpinBox

from ...i18n import tr


class ParameterSettingsWidget(QGroupBox):
    """Nhóm "Tham số" trong Cài đặt: hạn mức token cho tệp đính kèm, ngữ cảnh,
    số lượt song song và các ngưỡng khác.
    """
    def __init__(self, ctx, parent=None):
        """Nhóm Tham số: giới hạn token, ngưỡng rủi ro và các mức chặn của agent."""
        super().__init__(tr("settings.group.parameter"), parent)
        data = ctx.config.data
        sec = ctx.config.agent_security
        form = QFormLayout(self)

        def tieu_de(key: str) -> None:
            """Thêm một dòng tiêu đề phụ vào form."""
            lbl = QLabel(tr(key))
            lbl.setStyleSheet("font-weight:600; margin-top:6px;")
            form.addRow(lbl)

        # --- đính kèm ---
        att = data.get("attachments", {})
        tieu_de("settings.group.attachments")
        self.attach_files = QSpinBox()
        self.attach_files.setRange(1, 50)
        self.attach_files.setSuffix(tr("settings.max_files_suffix"))
        self.attach_files.setValue(max(1, int(att.get("max_files", 20))))
        self.attach_files.setToolTip(tr("settings.max_files_tooltip"))
        self.attach_tokens = QSpinBox()
        self.attach_tokens.setRange(1, 1000)
        self.attach_tokens.setSingleStep(5)
        self.attach_tokens.setSuffix(tr("settings.max_per_file_suffix"))
        # Lưu theo token, hiện theo nghìn token.
        self.attach_tokens.setValue(max(1, int(att.get("max_tokens", 500000)) // 1000))
        self.attach_tokens.setToolTip(tr("settings.max_per_file_tooltip"))
        form.addRow(tr("settings.max_files"), self.attach_files)
        form.addRow(tr("settings.max_per_file"), self.attach_tokens)

        # --- cấu trúc / GraphRAG ---
        st = data.get("structure", {})
        tieu_de("settings.group.structure")
        self.struct_nodes = QSpinBox()
        self.struct_nodes.setRange(0, 100000)
        self.struct_nodes.setSpecialValueText(tr("settings.unlimited"))
        self.struct_nodes.setSuffix(tr("settings.nodes_suffix"))
        self.struct_nodes.setValue(max(0, int(st.get("max_nodes", 500))))
        self.struct_nodes.setToolTip(tr("settings.nodes_tooltip"))
        self.struct_edges = QSpinBox()
        self.struct_edges.setRange(0, 200000)
        self.struct_edges.setSpecialValueText(tr("settings.unlimited"))
        self.struct_edges.setSuffix(tr("settings.edges_suffix"))
        self.struct_edges.setValue(max(0, int(st.get("max_edges", 500))))
        self.struct_edges.setToolTip(tr("settings.edges_tooltip"))
        form.addRow(tr("settings.max_nodes"), self.struct_nodes)
        form.addRow(tr("settings.max_edges"), self.struct_edges)

        # --- giới hạn sandbox (lưu vào agent_security) ---
        tieu_de("settings.group.sandbox_limits")
        self.sandbox_cpu = _gioi_han(" %", int(sec.get("resource_limit_cpu_percent", 0) or 0),
                                     hi=100_000)
        form.addRow(tr("settings.sandbox_cpu_label"), self.sandbox_cpu)
        self.sandbox_memory = _gioi_han(" MB", int(sec.get("resource_limit_memory_mb", 2048) or 2048))
        form.addRow(tr("settings.sandbox_memory_label"), self.sandbox_memory)
        self.sandbox_disk = _gioi_han(" MB", int(sec.get("resource_limit_disk_mb", 2048) or 2048))
        form.addRow(tr("settings.sandbox_disk_label"), self.sandbox_disk)

    # ---- lưu ------------------------------------------------------------

    def apply_to(self, data: dict) -> None:
        """Ghi các tham số từ form vào dict cấu hình.

        Ô nhập tính bằng NGHÌN token cho dễ đọc, nên phải nhân 1000 khi lưu.
        """
        att = data.setdefault("attachments", {})
        att["max_tokens"] = self.attach_tokens.value() * 1000
        att["max_files"] = self.attach_files.value()
        st = data.setdefault("structure", {})
        st["max_nodes"] = self.struct_nodes.value()
        st["max_edges"] = self.struct_edges.value()

    def apply_limits_to(self, sec: dict) -> None:
        """Ba con số này thuộc ``agent_security``, không thuộc ``structure``."""
        sec["resource_limit_cpu_percent"] = self.sandbox_cpu.value()
        sec["resource_limit_memory_mb"] = self.sandbox_memory.value()
        sec["resource_limit_disk_mb"] = self.sandbox_disk.value()


def _gioi_han(suffix: str, value: int, hi: int = 1_000_000) -> QSpinBox:
    """Ô nhập số nguyên có hậu tố đơn vị, chặn trong khoảng 0..``hi``."""
    box = QSpinBox()
    box.setRange(0, hi)
    box.setSuffix(suffix)
    box.setSpecialValueText(tr("settings.sandbox_unlimited"))   # 0 = không giới hạn
    box.setValue(value)
    return box
