"""Spawn a shell command inside a Windows AppContainer with NO network capability.

Why this exists
---------------
The old "block network" for agent shell commands only pointed the proxy env
vars at a dead port (``core/deps.py::network_blocked_env``). Anything that
ignores proxies (``Invoke-WebRequest -NoProxy``, raw sockets, ``certutil``,
.NET ``WebClient``...) still reached the internet. An AppContainer token that
is granted no ``internetClient``/``privateNetworkClientServer`` capability is
refused by the kernel firewall for every outbound connection, loopback
included, no matter which tool makes it. No admin rights are needed.

An AppContainer can only open files whose ACL admits its SID (or ALL
APPLICATION PACKAGES). System32 and Program Files already do; the workdir and
the app's own Python install do not, so :func:`spawn` grants the profile SID
access to those folders first (an extra ACE, nothing is removed).

:class:`AppContainerProcess` quacks like ``subprocess.Popen`` for the subset
``core/deps.py::_run_cancellable_body`` uses (``pid``, ``stdout``/``stderr``
text streams, ``poll``/``wait``/``kill``/``returncode``), so the Stop button,
timeouts, Job Objects and resource limits keep working unchanged.
"""
from __future__ import annotations

import io
import locale
import os
import subprocess
import sys
import threading
from typing import Dict, Iterable, Optional

PROFILE_NAME = "cowork_local.agent_netblock"
_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _adv = ctypes.WinDLL("advapi32", use_last_error=True)
    _uenv = ctypes.WinDLL("userenv", use_last_error=True)

    class _SECURITY_CAPABILITIES(ctypes.Structure):
        _fields_ = [("AppContainerSid", ctypes.c_void_p), ("Capabilities", ctypes.c_void_p),
                    ("CapabilityCount", wintypes.DWORD), ("Reserved", wintypes.DWORD)]

    class _STARTUPINFOW(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                    ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                    ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                    ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                    ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                    ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                    ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
                    ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

    class _STARTUPINFOEXW(ctypes.Structure):
        _fields_ = [("StartupInfo", _STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p)]

    class _PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                    ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

    class _SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                    ("bInheritHandle", wintypes.BOOL)]

    _uenv.CreateAppContainerProfile.restype = ctypes.c_long
    _uenv.CreateAppContainerProfile.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p,
        wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
    _uenv.DeriveAppContainerSidFromAppContainerName.restype = ctypes.c_long
    _uenv.DeriveAppContainerSidFromAppContainerName.argtypes = [
        wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
    _uenv.GetAppContainerFolderPath.restype = ctypes.c_long
    _uenv.GetAppContainerFolderPath.argtypes = [
        wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_wchar_p)]
    _adv.ConvertSidToStringSidW.restype = wintypes.BOOL
    _adv.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
    _k32.InitializeProcThreadAttributeList.restype = wintypes.BOOL
    _k32.InitializeProcThreadAttributeList.argtypes = [
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)]
    _k32.UpdateProcThreadAttribute.restype = wintypes.BOOL
    _k32.UpdateProcThreadAttribute.argtypes = [
        ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t, ctypes.c_void_p,
        ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
    _k32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    _k32.CreatePipe.restype = wintypes.BOOL
    _k32.CreatePipe.argtypes = [ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE),
                                ctypes.POINTER(_SECURITY_ATTRIBUTES), wintypes.DWORD]
    _k32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
    _k32.CreateProcessW.restype = wintypes.BOOL
    _k32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL,
        wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(_STARTUPINFOEXW),
        ctypes.POINTER(_PROCESS_INFORMATION)]
    _k32.ResumeThread.argtypes = [wintypes.HANDLE]
    _k32.WaitForSingleObject.restype = wintypes.DWORD
    _k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    _k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.GetStdHandle.restype = wintypes.HANDLE
    _k32.OpenProcess.restype = wintypes.HANDLE

    _ALREADY_EXISTS = ctypes.c_long(0x800700B7).value
    _PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
    _PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
    _EXTENDED_STARTUPINFO_PRESENT = 0x00080000
    _CREATE_UNICODE_ENVIRONMENT = 0x00000400
    _CREATE_NO_WINDOW = 0x08000000
    _CREATE_SUSPENDED = 0x00000004
    _STARTF_USESTDHANDLES = 0x00000100
    _HANDLE_FLAG_INHERIT = 0x00000001
    _STILL_ACTIVE = 259

_profile_lock = threading.Lock()
_profile: Dict[str, object] = {}
_granted: set = set()


class NetworkIsolationUnavailable(RuntimeError):
    """This machine cannot start a network-less process — callers must refuse to run."""


def is_supported() -> bool:
    """True on Windows builds that ship the AppContainer API (Windows 8+)."""
    if not _IS_WINDOWS:
        return False
    try:
        return bool(_uenv.CreateAppContainerProfile)
    except AttributeError:
        return False


def _profile_sid():
    """``(sid pointer, sid string, temp folder)`` of the shared no-network profile."""
    with _profile_lock:
        if _profile:
            return _profile["sid"], _profile["sid_str"], _profile["temp"]
        sid = ctypes.c_void_p()
        hr = _uenv.CreateAppContainerProfile(PROFILE_NAME, "Cowork Local agent (no network)",
                                             "Agent shell commands with the network blocked",
                                             None, 0, ctypes.byref(sid))
        if hr == _ALREADY_EXISTS:
            hr = _uenv.DeriveAppContainerSidFromAppContainerName(PROFILE_NAME, ctypes.byref(sid))
        if hr != 0 or not sid.value:
            raise NetworkIsolationUnavailable(f"AppContainer profile error 0x{hr & 0xFFFFFFFF:08X}")
        text = ctypes.c_wchar_p()
        if not _adv.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            raise NetworkIsolationUnavailable("Could not read the AppContainer SID")
        sid_str = text.value
        folder = ctypes.c_wchar_p()
        temp = ""
        if _uenv.GetAppContainerFolderPath(sid_str, ctypes.byref(folder)) == 0 and folder.value:
            temp = os.path.join(folder.value, "Temp")
            os.makedirs(temp, exist_ok=True)
        _profile.update(sid=sid, sid_str=sid_str, temp=temp)
        return sid, sid_str, temp


_PERMS = {"write": "(OI)(CI)(M)", "read": "(OI)(CI)(RX)", "read_here": "(OI)(NP)(RX)"}


def _qt_package_dir() -> str:
    """Folder of the installed PySide6/Qt binaries ('' if PySide6 is absent)."""
    try:
        import importlib.util

        spec = importlib.util.find_spec("PySide6")
    except (ImportError, ValueError):
        return ""
    return os.path.dirname(spec.origin) if spec and spec.origin else ""


def _covers(folder: str, target: str) -> bool:
    """True if ``target`` is ``folder`` itself or lies somewhere below it."""
    if not folder or not target:
        return False
    folder, target = os.path.normcase(folder), os.path.normcase(target)
    return target == folder or target.startswith(folder.rstrip("\\/") + os.sep)


def _icacls(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["icacls", *args], capture_output=True, text=True,
                          creationflags=_CREATE_NO_WINDOW)


def grant_access(path: str, sid_str: str, mode: str) -> None:
    """Let the AppContainer SID open ``path``.

    ``mode`` is ``"write"``/``"read"`` (inherited by everything below) or
    ``"read_here"`` (this folder and the files directly in it, no deeper).

    An inherited ACE must never reach the Qt WebEngine binaries: Chromium's
    sandboxed render process then fails to load Qt6WebEngineCore.dll
    (STATUS_DLL_NOT_FOUND) and every web view in the app goes blank. A folder
    that contains the PySide6 install is therefore refused.
    """
    path = os.path.abspath(path)
    key = (os.path.normcase(path), mode)
    if key in _granted or not os.path.exists(path):
        return
    if mode != "read_here" and _covers(path, _qt_package_dir()):
        raise NetworkIsolationUnavailable(
            f"Refusing to sandbox a folder that contains the app's Qt runtime: {path}")
    perm = _PERMS[mode]
    listing = (_icacls(path).stdout or "").lower()
    if f"{sid_str}:{perm}".lower() not in listing:
        done = _icacls(path, "/grant", f"*{sid_str}:{perm}", "/Q", "/C")
        if done.returncode != 0:
            raise NetworkIsolationUnavailable(
                f"Could not grant the sandbox access to {path}: {(done.stderr or done.stdout).strip()}")
    _granted.add(key)


def _repair_inherited_grant(path: str, sid_str: str) -> None:
    """Drop an inherited grant that an earlier build put on the app's venv."""
    key = (os.path.normcase(os.path.abspath(path)), "repaired")
    if key in _granted or not os.path.isdir(path):
        return
    listing = (_icacls(path).stdout or "").lower()
    if f"{sid_str}:(oi)(ci)".lower() in listing:
        _icacls(path, "/remove:g", f"*{sid_str}", "/Q", "/C")
    _granted.add(key)


def _interpreter_grants():
    """``(folder, mode)`` pairs that let the sandbox run the app's Python.

    The base install is read-only and holds no Qt; a venv only needs its root
    (``pyvenv.cfg``) and ``Scripts`` — never ``Lib/site-packages``.
    """
    qt_dir = _qt_package_dir()
    if _covers(sys.base_prefix, qt_dir):
        # PySide6 lives in the base install itself: expose only the executable
        # and the compiled stdlib modules, never the tree holding Qt.
        grants = [(sys.base_prefix, "read_here"), (os.path.join(sys.base_prefix, "DLLs"), "read")]
    else:
        grants = [(sys.base_prefix, "read")]
    if os.path.normcase(sys.prefix) != os.path.normcase(sys.base_prefix):
        grants += [(sys.prefix, "read_here"), (os.path.join(sys.prefix, "Scripts"), "read")]
    return [(folder, mode) for folder, mode in grants
            if mode == "read_here" or not _covers(folder, qt_dir)]


def _env_block(env: Dict[str, str]) -> ctypes.Array:
    """Sorted, double-NUL-terminated UTF-16 environment block for CreateProcessW."""
    items = sorted(env.items(), key=lambda kv: kv[0].upper())
    text = "".join(f"{k}={v}\0" for k, v in items if k and "=" not in k) + "\0"
    return ctypes.create_unicode_buffer(text, len(text))


def _pipe():
    """Anonymous pipe; only the child's (write) end is inheritable."""
    sa = _SECURITY_ATTRIBUTES(ctypes.sizeof(_SECURITY_ATTRIBUTES), None, True)
    read, write = wintypes.HANDLE(), wintypes.HANDLE()
    if not _k32.CreatePipe(ctypes.byref(read), ctypes.byref(write), ctypes.byref(sa), 0):
        raise ctypes.WinError(ctypes.get_last_error())
    _k32.SetHandleInformation(read, _HANDLE_FLAG_INHERIT, 0)
    return read, write


class AppContainerProcess:
    """The ``subprocess.Popen`` subset that ``deps._run_cancellable_body`` relies on."""

    def __init__(self, handle, pid: int, stdout: io.TextIOBase, stderr: io.TextIOBase):
        """Wrap an already-started process handle and its two output streams."""
        self._handle = handle
        self.pid = pid
        self.stdout = stdout
        self.stderr = stderr
        self.returncode: Optional[int] = None

    def poll(self) -> Optional[int]:
        """Exit code if the process has finished, else None."""
        if self.returncode is None and self._handle:
            code = wintypes.DWORD()
            if _k32.GetExitCodeProcess(self._handle, ctypes.byref(code)) and code.value != _STILL_ACTIVE:
                self.returncode = ctypes.c_int32(code.value).value
                _k32.CloseHandle(self._handle)
                self._handle = None
        return self.returncode

    def wait(self, timeout: Optional[float] = None) -> int:
        """Block until exit; raise ``subprocess.TimeoutExpired`` like Popen does."""
        if self.returncode is None and self._handle:
            ms = 0xFFFFFFFF if timeout is None else int(timeout * 1000)
            if _k32.WaitForSingleObject(self._handle, ms) != 0:
                raise subprocess.TimeoutExpired("appcontainer", timeout)
        return self.poll()

    def kill(self) -> None:
        """Terminate the process (the Job Object in deps kills its children)."""
        if self.returncode is None and self._handle:
            _k32.TerminateProcess(self._handle, 1)

    def communicate(self, timeout: Optional[float] = None):
        """Read both streams to the end and wait; returns ``(stdout, stderr)``."""
        chunks: Dict[str, str] = {}

        def _drain(name, stream):
            chunks[name] = stream.read()

        readers = [threading.Thread(target=_drain, args=(n, s), daemon=True)
                   for n, s in (("out", self.stdout), ("err", self.stderr))]
        for t in readers:
            t.start()
        for t in readers:
            t.join(timeout)
        self.wait(timeout)
        return chunks.get("out", ""), chunks.get("err", "")


def spawn(command: str, cwd: Optional[str], env: Optional[Dict[str, str]],
          readable_dirs: Iterable[str] = ()) -> AppContainerProcess:
    """Start ``cmd.exe /c command`` in the no-network AppContainer.

    Raises :class:`NetworkIsolationUnavailable` when that cannot be done —
    callers must then refuse the command rather than run it with the network on.
    """
    if not is_supported():
        raise NetworkIsolationUnavailable("AppContainer is only available on Windows")
    sid, sid_str, temp = _profile_sid()
    cwd = os.path.abspath(cwd or os.getcwd())
    _repair_inherited_grant(sys.prefix, sid_str)
    grant_access(cwd, sid_str, "write")
    for folder, mode in [*_interpreter_grants(), *((d, "read") for d in readable_dirs if d)]:
        grant_access(folder, sid_str, mode)

    child_env = dict(os.environ if env is None else env)
    if temp:
        child_env["TEMP"] = child_env["TMP"] = temp
    child_env.setdefault("PYTHONIOENCODING", "utf-8")
    env_block = _env_block(child_env)

    out_r, out_w = _pipe()
    err_r, err_w = _pipe()
    handles = (wintypes.HANDLE * 2)(out_w, err_w)
    caps = _SECURITY_CAPABILITIES(sid, None, 0, 0)
    size = ctypes.c_size_t()
    _k32.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
    attr = ctypes.create_string_buffer(size.value)
    pi = _PROCESS_INFORMATION()
    try:
        if not (_k32.InitializeProcThreadAttributeList(attr, 2, 0, ctypes.byref(size))
                and _k32.UpdateProcThreadAttribute(
                    attr, 0, _PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES, ctypes.byref(caps),
                    ctypes.sizeof(caps), None, None)
                and _k32.UpdateProcThreadAttribute(
                    attr, 0, _PROC_THREAD_ATTRIBUTE_HANDLE_LIST, handles,
                    ctypes.sizeof(handles), None, None)):
            raise NetworkIsolationUnavailable(str(ctypes.WinError(ctypes.get_last_error())))
        si = _STARTUPINFOEXW()
        si.StartupInfo.cb = ctypes.sizeof(si)
        si.StartupInfo.dwFlags = _STARTF_USESTDHANDLES
        si.StartupInfo.hStdOutput = out_w
        si.StartupInfo.hStdError = err_w
        si.lpAttributeList = ctypes.addressof(attr)
        comspec = os.environ.get("COMSPEC") or r"C:\Windows\System32\cmd.exe"
        cmdline = ctypes.create_unicode_buffer(f'"{comspec}" /d /s /c "{command}"')
        flags = (_EXTENDED_STARTUPINFO_PRESENT | _CREATE_UNICODE_ENVIRONMENT
                 | _CREATE_NO_WINDOW | _CREATE_SUSPENDED)
        if not _k32.CreateProcessW(None, cmdline, None, None, True, flags,
                                   ctypes.addressof(env_block), cwd,
                                   ctypes.byref(si), ctypes.byref(pi)):
            raise NetworkIsolationUnavailable(
                f"Could not start the sandboxed command: {ctypes.WinError(ctypes.get_last_error())}")
        _k32.ResumeThread(pi.hThread)
        _k32.CloseHandle(pi.hThread)
    except BaseException:
        for h in (out_r, err_r):
            _k32.CloseHandle(h)
        raise
    finally:
        _k32.DeleteProcThreadAttributeList(attr)
        _k32.CloseHandle(out_w)
        _k32.CloseHandle(err_w)

    def _stream(handle) -> io.TextIOBase:
        fd = msvcrt.open_osfhandle(handle.value, os.O_RDONLY)
        return io.TextIOWrapper(io.FileIO(fd, "rb"), encoding=locale.getpreferredencoding(False),
                                errors="replace")

    return AppContainerProcess(pi.hProcess, pi.dwProcessId, _stream(out_r), _stream(err_r))


__all__ = ["AppContainerProcess", "NetworkIsolationUnavailable", "PROFILE_NAME",
           "grant_access", "is_supported", "spawn"]
