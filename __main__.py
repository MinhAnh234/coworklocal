"""Entry point: ``python -m cowork_local``.

Also works when run directly as ``python __main__.py`` — see main().
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    # Imported lazily so that ``-h`` style tooling and tests can import the
    # package without spinning up a full Qt application.
    #
    # `from .app import run` requires this file to be loaded as part of the
    # `cowork_local` package (i.e. via `python -m cowork_local`). When run as
    # a plain script (`python __main__.py`), `__package__` is empty so the
    # relative import fails — in that case put the package root (the parent
    # of this file's directory) on sys.path and use an absolute import.
    """Điểm vào ``python -m cowork_local``.

    Import muộn để công cụ kiểu ``-h`` và test nạp được gói mà không phải dựng cả
    ứng dụng Qt. Chạy như script thường (``python __main__.py``) thì
    ``__package__`` rỗng nên import tương đối hỏng — lúc đó đưa thư mục cha vào
    ``sys.path`` và dùng import tuyệt đối.
    """
    if __package__:
        from .app import run
    else:
        parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent not in sys.path:
            sys.path.insert(0, parent)
        from cowork_local.app import run

    return run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
