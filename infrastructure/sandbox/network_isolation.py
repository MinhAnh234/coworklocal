"""Start a shell command that the operating system keeps off the network.

Used whenever "Block network" is on for agent ``run_command`` calls and for
scheduled script tasks. The contract is fail-closed: if isolation cannot be
set up, :class:`NetworkIsolationUnavailable` is raised and the caller refuses
the command instead of running it with the network open.

* Windows: an AppContainer with no network capability
  (:mod:`.appcontainer_process`).
* macOS: ``sandbox-exec`` with a profile that denies every network operation.
* Linux: ``unshare --net`` in a new user namespace (an empty network namespace
  has only a downed loopback). If unprivileged namespaces are disabled,
  ``unshare`` itself fails and the command never runs.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Dict, Optional

from .appcontainer_process import NetworkIsolationUnavailable

_MACOS_PROFILE = "(version 1)(allow default)(deny network*)"


def spawn_without_network(command: str, cwd: Optional[str], env: Optional[Dict[str, str]]):
    """A ``Popen``-like process running ``command`` through the shell, with no network."""
    if sys.platform == "win32":
        from . import appcontainer_process

        return appcontainer_process.spawn(command, cwd, env)
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        argv = ["sandbox-exec", "-p", _MACOS_PROFILE, "/bin/sh", "-c", command]
    elif sys.platform.startswith("linux") and shutil.which("unshare"):
        argv = ["unshare", "--user", "--map-root-user", "--net", "/bin/sh", "-c", command]
    else:
        raise NetworkIsolationUnavailable(
            "No network isolation is available on this system (needs AppContainer, "
            "sandbox-exec or unshare).")
    return subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, bufsize=1,
                            start_new_session=True)


__all__ = ["NetworkIsolationUnavailable", "spawn_without_network"]
