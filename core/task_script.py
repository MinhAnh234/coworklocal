"""Run a scheduled task of type ``script`` (tách khỏi ``task_executors.py``).

Khi công tắc "Chặn mạng" đang bật, lệnh của task chạy trong tiến trình bị hệ
điều hành cắt mạng — giống ``run_command`` của agent. Trước đây task script
chạy thẳng bằng ``subprocess.run``, không sandbox, nên lên mạng tự do.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def run_script(command: str, out_dir: Path, timeout_sec: int) -> str:
    """Chạy một task kiểu script bằng shell trong thư mục kết quả, có hạn giờ."""
    if not command.strip():
        raise RuntimeError("Script task has no command configured.")
    from ..application.network import network_guard

    if network_guard.is_blocked():
        return _run_script_without_network(command, out_dir, timeout_sec)
    proc = subprocess.run(command, shell=True, cwd=str(out_dir),
                          capture_output=True, text=True, timeout=max(1, timeout_sec))
    output = (proc.stdout or "") + (("\n[stderr]\n" + proc.stderr) if proc.stderr else "")
    if proc.returncode != 0:
        raise RuntimeError(f"Script exited with code {proc.returncode}:\n{output[-2000:]}")
    return output


def _run_script_without_network(command: str, out_dir: Path, timeout_sec: int) -> str:
    """Như :func:`run_script`, nhưng tiến trình không có mạng; không cô lập được thì không chạy."""
    from .deps import network_blocked_env, run_cancellable

    rc, output, _cancelled, timed_out, _exceeded = run_cancellable(
        command, cwd=str(out_dir), timeout=max(1, timeout_sec), shell=True,
        env=network_blocked_env(), isolate_network=True,
    )
    if timed_out:
        raise subprocess.TimeoutExpired(command, timeout_sec)
    if rc is None:
        raise RuntimeError("Script not run: network is blocked and the script could not be "
                           f"isolated from the network ({output.strip()}).")
    if rc != 0:
        raise RuntimeError(f"Script exited with code {rc} (network blocked):\n{output[-2000:]}")
    return output


__all__ = ["run_script"]
