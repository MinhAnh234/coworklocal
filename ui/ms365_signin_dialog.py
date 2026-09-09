"""Microsoft 365 sign-in dialog (DF-007) — thin UI over the working device-code
flow in ``core/ms365_auth.py``. There was an older MS365 sign-in UI in this
app; it was removed as dead code (no entry point — see
``ui/settings_dialog.py`` module docstring) before this feature existed, so
this is a fresh, small dialog rather than a resurrection of that one.

Usage: ``if ensure_signed_in(parent, ctx.config): ...`` — returns ``True``
immediately (no dialog shown) when already signed in.
"""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout,
)

from ..core import ms365_auth
from ..i18n import tr


class _SignInWorker(QThread):
    """Chạy ``sign_in_device_code()`` (blocking, poll tới khi xong/hết hạn) ở
    luồng nền — xem ``core/worker.py::AgentWorker`` cho cùng idiom (bắt hết
    exception, phát signal thay vì để lỗi giết luồng âm thầm)."""
    code_ready = Signal(dict)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config

    def run(self) -> None:  # noqa: D401
        try:
            result = ms365_auth.sign_in(lambda flow: self.code_ready.emit(flow), self._config)
            self.finished_ok.emit(result or {})
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI, never crashes the thread
            self.failed.emit(str(exc))


class Ms365SignInDialog(QDialog):
    """Modal: hiện user_code + verification_uri, tự mở trình duyệt, đóng lại
    khi đăng nhập xong (hoặc người dùng bấm Hủy)."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._worker: _SignInWorker | None = None
        self.setWindowTitle(tr("ms365_signin.title"))
        self.setModal(True)

        layout = QVBoxLayout(self)
        self._intro_lbl = QLabel(tr("ms365_signin.intro"))
        self._intro_lbl.setWordWrap(True)
        layout.addWidget(self._intro_lbl)

        self._code_lbl = QLabel()
        self._code_lbl.setWordWrap(True)
        self._code_lbl.hide()
        layout.addWidget(self._code_lbl)

        self._open_link_btn = QPushButton(tr("ms365_signin.open_link"))
        self._open_link_btn.hide()
        self._open_link_btn.clicked.connect(self._open_link)
        layout.addWidget(self._open_link_btn)

        self._error_lbl = QLabel()
        self._error_lbl.setWordWrap(True)
        self._error_lbl.setStyleSheet("color: #c0392b;")
        self._error_lbl.hide()
        layout.addWidget(self._error_lbl)

        btn_row = QHBoxLayout()
        self._signin_btn = QPushButton(tr("ms365_signin.button"))
        self._signin_btn.setObjectName("primary")
        self._signin_btn.clicked.connect(self._start_sign_in)
        self._cancel_btn = QPushButton(tr("ms365_signin.cancel"))
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch(1)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._signin_btn)
        layout.addLayout(btn_row)

        self._verification_uri = ""

    def _open_link(self) -> None:
        if self._verification_uri:
            webbrowser.open(self._verification_uri)

    def _start_sign_in(self) -> None:
        self._signin_btn.setEnabled(False)
        self._signin_btn.setText(tr("ms365_signin.signing_in"))
        self._error_lbl.hide()
        self._worker = _SignInWorker(self._config, self)
        self._worker.code_ready.connect(self._on_code_ready)
        self._worker.finished_ok.connect(self._on_finished_ok)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_code_ready(self, flow: dict) -> None:
        self._verification_uri = flow.get("verification_uri_complete") or flow.get(
            "verification_uri", "")
        self._code_lbl.setText(
            tr("ms365_signin.code_hint", url=flow.get("verification_uri", "")) +
            f"\n\n{flow.get('user_code', '')}")
        self._code_lbl.show()
        self._open_link_btn.show()
        if self._verification_uri:
            webbrowser.open(self._verification_uri)

    def _on_finished_ok(self, _result: dict) -> None:
        self.accept()

    def _on_failed(self, err: str) -> None:
        self._signin_btn.setEnabled(True)
        self._signin_btn.setText(tr("ms365_signin.button"))
        self._error_lbl.setText(tr("ms365_signin.failed", err=err))
        self._error_lbl.show()

    def reject(self) -> None:
        # NOTE: MSAL's acquire_token_by_device_flow() has no cancellation hook,
        # so a worker already polling keeps polling in the background until it
        # times out on its own (a few minutes) — closing this dialog just stops
        # the UI from waiting on it. Its late signals are harmless no-ops
        # against an already-closed (but not destroyed) dialog.
        super().reject()


def ensure_signed_in(parent, config) -> bool:
    """True nếu đã (hoặc vừa) đăng nhập MS365; False nếu người dùng hủy hoặc
    đăng nhập thất bại và đóng dialog."""
    if ms365_auth.is_signed_in(config):
        return True
    dialog = Ms365SignInDialog(config, parent)
    return dialog.exec() == QDialog.Accepted
