"""Launch codebase-memory-mcp's OWN HTTP graph UI (``--ui=true``) as a
background process for the GraphRAG tab to embed/open — this is the richer
"Graph / Projects / Control" visualization the binary ships with, distinct
from this app's own D3 fallback graph.

Not every distributed build of the binary includes that UI (some are built
"without the embedded UI" — the CLI prints that exact message and never opens
the port). :meth:`CodebaseMemoryUiServer.start` tells the two failure modes
apart so the caller can show the right guidance instead of a generic timeout.
"""
from __future__ import annotations

import subprocess
import threading
import time
from typing import List, Optional

import requests

from .codebase_memory import resolve_binary

DEFAULT_PORT = 9749
_STARTUP_TIMEOUT = 8.0
_POLL_INTERVAL = 0.25
# Substring of the binary's own message when it was built without the UI
# (see the DeusData/codebase-memory-mcp --help output) — matched case-insensitively.
_NO_UI_MARKER = "built without the embedded ui"


class CmemUiError(RuntimeError):
    """The UI server could not be reached. ``no_ui_build`` is True when the
    binary itself reported it has no embedded UI (needs the ``-ui`` release
    asset) — a different remedy than a generic startup/timeout failure."""

    def __init__(self, message: str, no_ui_build: bool = False):
        """``no_ui_build`` đánh dấu trường hợp riêng: chạy được nhưng bản cài không kèm
        phần giao diện — thông báo cho người dùng phải khác hẳn lỗi chạy thường.
        """
        super().__init__(message)
        self.no_ui_build = no_ui_build


class CodebaseMemoryUiServer:
    """One ``codebase-memory-mcp --ui`` process, started on demand."""

    def __init__(self, binary_path: str = "", port: int = DEFAULT_PORT):
        """Chuẩn bị chỗ chạy máy chủ giao diện; chưa khởi động tiến trình nào."""
        self.binary = resolve_binary(binary_path)
        self.port = port
        self._proc: Optional[subprocess.Popen] = None

    @property
    def url(self) -> str:
        """Địa chỉ để mở giao diện. Chỉ nghe trên 127.0.0.1 — đây là công cụ cục bộ,
        không mở ra mạng.
        """
        return f"http://127.0.0.1:{self.port}/"

    @property
    def running(self) -> bool:
        """Tiến trình máy chủ còn sống không."""
        return self._proc is not None and self._proc.poll() is None

    def start(self, repo_path: str = "") -> str:
        """Start the UI server (no-op — just returns the URL — if one is
        already running) and block briefly until it answers. Raises
        :class:`CmemUiError` with a clear reason on failure/timeout."""
        if self.running:
            return self.url
        if not self.binary:
            raise CmemUiError("codebase-memory-mcp chưa được cài đặt.")
        cmd = [self.binary, "--ui=true", f"--port={self.port}"]
        try:
            self._proc = subprocess.Popen(
                cmd, cwd=repo_path or None, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise CmemUiError(f"Không khởi chạy được codebase-memory-mcp: {exc}")

        lines: List[str] = []
        no_ui_event = threading.Event()

        def _reader() -> None:
            """Chạy nền: đọc đầu ra của tiến trình, giữ lại để báo lỗi và bật cờ khi thấy
            dấu hiệu bản cài không có phần giao diện.
            """
            try:
                stream = self._proc.stdout
                if stream is None:
                    return
                for line in stream:
                    lines.append(line)
                    if _NO_UI_MARKER in line.lower():
                        no_ui_event.set()
            except (OSError, ValueError):
                pass

        threading.Thread(target=_reader, daemon=True).start()

        deadline = time.monotonic() + _STARTUP_TIMEOUT
        while time.monotonic() < deadline:
            try:
                resp = requests.get(self.url, timeout=1)
                if resp.status_code < 500:
                    return self.url
            except requests.RequestException:
                pass
            if no_ui_event.is_set():
                self.stop()
                raise CmemUiError(
                    "".join(lines).strip()[:400] or "Bản build này không có UI đồ thị nhúng.",
                    no_ui_build=True,
                )
            if self._proc.poll() is not None:
                self.stop()
                raise CmemUiError(
                    "".join(lines).strip()[:400] or "codebase-memory-mcp thoát ngay lập tức.")
            time.sleep(_POLL_INTERVAL)
        self.stop()
        raise CmemUiError(f"Hết thời gian chờ UI trên cổng {self.port}.")

    def stop(self) -> None:
        """Dừng máy chủ. Xin dừng tử tế trước, quá 3 giây thì buộc tắt.

        Mọi lỗi đều bị nuốt có chủ ý: đây là dọn dẹp lúc thoát, ném lỗi ở đây chỉ
        làm kẹt đường thoát của cả ứng dụng.
        """
        proc, self._proc = self._proc, None
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:  # noqa: BLE001 - best-effort cleanup, never raise on shutdown
                try:
                    proc.kill()
                except Exception:  # noqa: BLE001
                    pass
