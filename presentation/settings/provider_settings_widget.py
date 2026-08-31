"""Mục AI Provider trong Cài đặt — R08-T07.

Chọn nhà cung cấp, base URL, API key, model — kèm hai nút Tải model và Test
kết nối chạy ở luồng nền.

Điểm cần biết khi sửa: widget giữ **bản nháp cho từng provider**
(``_staging``). Người dùng đổi sang provider khác rồi quay lại thì thấy đúng
những gì mình vừa gõ, dù chưa bấm Lưu. Nếu đọc thẳng từ config thay vì từ bản
nháp là mất phần đang gõ dở.
"""
from __future__ import annotations

from typing import Dict

from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QWidget,
)

from ...config import PROVIDER_LABELS
from ...core.worker import AgentWorker
from ...i18n import tr
from ...ui.icons import icon


class ProviderSettingsWidget(QGroupBox):
    """Nhóm "Nhà cung cấp AI" trong hộp thoại Cài đặt.

    Giữ một BẢN NHÁP riêng cho từng provider (``_staging``): đổi qua lại giữa
    các provider trong lúc chỉnh không được làm mất thứ vừa gõ, và chỉ khi
    bấm Lưu mới ghi xuống cấu hình thật.
    """
    def __init__(self, ctx, parent=None):
        """Nhóm Provider: endpoint, khoá API và model của từng provider.

        Sửa trên một bản nháp (``_staging``) chứ không sửa thẳng cấu hình: người dùng
        bấm Huỷ thì mọi thay đổi biến mất, kể cả khoá API vừa gõ.
        """
        super().__init__(tr("settings.group.provider"), parent)
        self.ctx = ctx
        data = ctx.config.data
        self._workers = []

        self._staging: Dict[str, dict] = {
            key: dict(conf) for key, conf in data["providers"].items()
        }
        self.provider_combo = QComboBox()
        for key, label in PROVIDER_LABELS.items():
            self.provider_combo.addItem(label, key)
        _select(self.provider_combo, ctx.config.active_provider)
        self._current_key = self.provider_combo.currentData()

        conf = self._staging.get(self._current_key, {})
        self.prov_base = QLineEdit(conf.get("base_url", ""))
        self.prov_key = QLineEdit(conf.get("api_key", ""))
        self.prov_key.setEchoMode(QLineEdit.Password)
        self.prov_model = _model_combo(conf.get("model", ""))
        self.prov_status = QLabel("")
        self.prov_status.setObjectName("hint")
        self.prov_status.setWordWrap(True)

        form = QFormLayout(self)
        form.addRow(tr("settings.active_provider"), self.provider_combo)
        form.addRow(tr("settings.base_url"), self.prov_base)
        form.addRow(tr("settings.api_key"), self.prov_key)
        form.addRow(tr("settings.model"), self._hang_model())
        form.addRow("", self.prov_status)

        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)

    # ---- lưu ------------------------------------------------------------

    def apply_to(self, data: dict) -> None:
        """Ghi provider đang chọn và toàn bộ bản nháp vào dict cấu hình."""
        data["active_provider"] = self.provider_combo.currentData()
        self._stash()
        for key, staged in self._staging.items():
            data["providers"].setdefault(key, {}).update({
                "base_url": staged.get("base_url", ""),
                "api_key": staged.get("api_key", ""),
                "model": staged.get("model", ""),
            })

    # ---- bản nháp từng provider -----------------------------------------

    def _stash(self) -> None:
        """Cất nội dung đang gõ vào bản nháp của provider hiện tại."""
        self._staging.setdefault(self._current_key, {}).update({
            "base_url": self.prov_base.text().strip(),
            "api_key": self.prov_key.text(),
            "model": self.prov_model.currentText().strip(),
        })

    def _on_provider_changed(self) -> None:
        """Đổi provider: cất bản nháp cũ rồi nạp bản nháp mới lên các ô nhập."""
        self._stash()
        self._current_key = self.provider_combo.currentData()
        conf = self._staging.get(self._current_key, {})
        self.prov_base.setText(conf.get("base_url", ""))
        self.prov_key.setText(conf.get("api_key", ""))
        self.prov_model.clear()
        if conf.get("model"):
            self.prov_model.addItem(conf["model"])
            self.prov_model.setCurrentText(conf["model"])
        else:
            self.prov_model.setCurrentText("")
        self.prov_status.setText("")

    def _conf_hien_tai(self, provider: str) -> dict:
        """Cấu hình dùng để thử kết nối/nạp model.

        Provider đang mở thì lấy thẳng từ ô nhập (kể cả thứ chưa lưu); provider
        khác thì lấy từ bản nháp đã cất.
        """
        if provider == self._current_key:
            return {"base_url": self.prov_base.text().strip(),
                    "api_key": self.prov_key.text(),
                    "model": self.prov_model.currentText().strip()}
        conf = self._staging.get(provider, {})
        return {"base_url": conf.get("base_url", ""), "api_key": conf.get("api_key", ""),
                "model": conf.get("model", "")}

    # ---- hàng model + hai nút -------------------------------------------

    def _hang_model(self) -> QWidget:
        """Dựng hàng "Model": ô chọn model kèm nút nạp danh sách và nút thử kết nối."""
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.prov_model, 1)

        btn = QPushButton(tr("settings.load"))
        btn.setIcon(icon("download"))
        btn.setToolTip(tr("settings.load_tooltip"))
        btn.clicked.connect(lambda: self._load_models(self.provider_combo.currentData()))
        lay.addWidget(btn)

        test_btn = QPushButton(tr("settings.test_connection"))
        test_btn.setIcon(icon("flask"))
        test_btn.setToolTip(tr("settings.test_connection_tooltip"))
        test_btn.clicked.connect(lambda: self._test_connection(self.provider_combo.currentData()))
        lay.addWidget(test_btn)

        # Hai nút giữ kích thước tự nhiên, combo là thứ phải nhường. Không có
        # dòng này thì bề rộng tối thiểu của hàng bằng combo cộng cả hai nút,
        # không co lại được, và dialog sinh ra thanh cuộn ngang.
        for b in (btn, test_btn):
            b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        row.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        return row

    # ---- việc chạy nền ---------------------------------------------------

    def _load_models(self, provider: str) -> None:
        """Nạp danh sách model của provider ở luồng nền.

        Giữ nguyên model đang chọn ở đầu danh sách, kể cả khi máy chủ không trả
        về nó — người dùng có thể đang dùng một model không được liệt kê.
        """
        conf = self._conf_hien_tai(provider)
        combo, status = self.prov_model, self.prov_status

        def job(worker):
            """Chạy nền: hỏi provider danh sách model."""
            from ...providers import build_provider
            prov = build_provider(provider, conf)
            return {"models": prov.list_models(), "error": getattr(prov, "last_error", "")}

        def done(result):
            """Đổ danh sách vào ô chọn, giữ model đang chọn ở đầu."""
            models = result.get("models") or []
            current = combo.currentText().strip()
            combo.clear()
            if current:
                combo.addItem(current)
            for m in models:
                if m != current:
                    combo.addItem(m)
            combo.setCurrentText(current)
            if models:
                status.setText(tr("settings.loaded_models", n=len(models),
                                  provider=PROVIDER_LABELS.get(provider, provider)))
            else:
                status.setText(tr("settings.load_models_error",
                                  err=result.get("error", "")
                                  or tr("settings.load_models_error_unknown")))

        self._chay_nen(job, done,
                       lambda e: status.setText(tr("settings.load_failed", err=e)),
                       tr("settings.loading_models"))

    def _test_connection(self, provider: str) -> None:
        """Thử kết nối tới provider ở luồng nền, tô xanh/đỏ kết quả."""
        conf = self._conf_hien_tai(provider)
        status = self.prov_status

        def job(worker):
            """Chạy nền: gọi thử provider để xác nhận kết nối."""
            from ...providers import build_provider
            ok, message = build_provider(provider, conf).test_connection()
            return {"ok": ok, "message": message}

        def done(result):
            """Hiện kết quả thử, tô xanh khi thành công và đỏ khi thất bại."""
            status.setText(result.get("message", ""))
            status.setStyleSheet("color: #090;" if result.get("ok") else "color: #c00;")

        def failed(e):
            """Thử kết nối ném lỗi: hiện lỗi bằng màu đỏ."""
            status.setText(str(e))
            status.setStyleSheet("color: #c00;")

        self._chay_nen(job, done, failed, tr("settings.testing_connection"))

    def _chay_nen(self, job, done, failed, dang_lam: str) -> None:
        """Chạy một việc ở luồng nền và hiện dòng trạng thái trong lúc chờ.

        Giữ tham chiếu tới worker trong ``self._workers``: để nó bị thu gom giữa
        chừng là luồng chết lặng lẽ, không lỗi, không kết quả.
        """
        w = AgentWorker(job)
        w.finished_ok.connect(done)
        w.failed.connect(failed)
        # Giữ tham chiếu: worker bị thu gom giữa chừng là luồng chết lặng lẽ.
        self._workers.append(w)
        self.prov_status.setText(dang_lam)
        w.start()


def _model_combo(value: str) -> QComboBox:
    """Ô chọn model cho phép gõ tay.

    Ép co lại theo bề rộng được cấp: mặc định Qt cho combo rộng bằng mục dài
    nhất, mà id model thì rất dài — hàng đó sẽ tràn ra ngoài hộp thoại và đẻ ra
    thanh cuộn ngang (tệ hơn ở màn 125%/150%). Phần bung ra để popup lo.
    """
    combo = QComboBox()
    combo.setEditable(True)
    # Mặc định combo rộng bằng mục dài nhất; id model thì dài, nên hàng này
    # tràn ra ngoài dialog và đẻ ra thanh cuộn ngang (tệ hơn ở màn 125%/150%).
    # Cho nó co lại, phần bung ra để popup lo.
    combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(8)
    combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    if value:
        combo.addItem(value)
        combo.setCurrentText(value)
    return combo


def _select(combo: QComboBox, value: str) -> None:
    """Chọn mục mang dữ liệu ``value`` trong một combo; không có thì để nguyên."""
    i = combo.findData(value)
    if i >= 0:
        combo.setCurrentIndex(i)
