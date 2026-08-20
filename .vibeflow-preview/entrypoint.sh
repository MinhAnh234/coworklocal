#!/bin/sh
# Boot the Cowork-Local PySide6 desktop app on Qt's built-in VNC server, then
# expose the live GUI to the browser through noVNC + websockify on :6080.
#
# This entrypoint is intended to be run from a `python:3.11-slim-bookworm`
# container via podman-compose.  All setup (Qt runtime libs, noVNC, PySide6
# wheels) happens here so we don't need a custom image / Dockerfile.
# Idempotent: reruns are fast (apt reuses debs, pip uses the named cache vol).

set -e

log() { printf '[entrypoint] %s\n' "$*"; }

# ---------------------------------------------------------------------------
# 1. System runtime libraries: Qt6 needs EGL/GL/XCB; noVNC needs websockify.
# ---------------------------------------------------------------------------
if [ ! -f /var/cache/cowork_setup.stamp ]; then
    log "installing apt packages (first run only)…"
    apt-get update -qq
    apt-get install -y --no-install-recommends \
        libegl1 libgl1 libglib2.0-0 libdbus-1-3 libfontconfig1 \
        libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 \
        libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
        libxcb-render-util0 libxcb-shape0 libxcb-sync1 \
        libxcb-xfixes0 libxcb-xinerama0 libxcb-xkb1 libxcb-util1 \
        libxcomposite1 libxdamage1 libxrandr2 libxss1 libxtst6 \
        libxi6 libxrender1 libfreetype6 \
        fonts-dejavu fonts-noto-cjk \
        netcat-openbsd ca-certificates >/dev/null
    rm -rf /var/lib/apt/lists/*
    touch /var/cache/cowork_setup.stamp
    log "apt setup done."
else
    log "apt setup already done (skipping)."
fi

# ---------------------------------------------------------------------------
# 2. Python dependencies (cached in the named `pip-cache` volume).
#    `websockify` is shipped as a pip wheel and bundles the noVNC web
#    assets under its package `web/` directory, so we don't need the
#    (unavailable on slim-bookworm) apt `novnc` / `websockify` packages.
# ---------------------------------------------------------------------------
log "ensuring python deps…"
pip install --no-cache-dir --quiet \
    "PySide6>=6.6" "pydantic>=2" requests psutil websockify numpy
log "python deps OK."

# ---------------------------------------------------------------------------
# 3. Make the workspace importable as `cowork_local` (the package name that
#    `python -m cowork_local` and the test suite expect).  Compose mounts the
#    live repo at /workspace; we add a thin symlink at /opt/cowork_local.
# ---------------------------------------------------------------------------
ln -sfn /workspace /opt/cowork_local
export PYTHONPATH=/opt

# ---------------------------------------------------------------------------
# 4. Launch the app on Qt's built-in VNC platform (no Xvfb needed).
#    Qt VNC listens on QT_QPA_VNC_HOST:QT_QPA_VNC_PORT (127.0.0.1:5900).
# ---------------------------------------------------------------------------
: > /var/log/app.log
log "launching app on Qt VNC platform…"
python -m cowork_local >/var/log/app.log 2>&1 &
APP_PID=$!

# Wait until the VNC socket accepts a connection (or give up after 60s).
for i in $(seq 1 120); do
    if nc -z 127.0.0.1 "${QT_QPA_VNC_PORT:-5900}" 2>/dev/null; then
        log "VNC server up on 127.0.0.1:${QT_QPA_VNC_PORT:-5900} (pid ${APP_PID})."
        break
    fi
    if ! kill -0 "${APP_PID}" 2>/dev/null; then
        log "app process died before VNC was up; log tail:"
        tail -n 60 /var/log/app.log >&2 || true
        exit 1
    fi
    sleep 0.5
done

if ! nc -z 127.0.0.1 "${QT_QPA_VNC_PORT:-5900}" 2>/dev/null; then
    log "VNC never came up; log tail:"
    tail -n 60 /var/log/app.log >&2 || true
    exit 1
fi

# ---------------------------------------------------------------------------
# 5. Bridge browser -> VNC.  websockify serves the noVNC web client on :6080
#    and proxies WebSocket connections to the raw VNC server.  The noVNC web
#    assets are bundled inside the websockify pip wheel.
# ---------------------------------------------------------------------------
NOVNC_WEB="$(python - <<'PY'
import os, websockify
print(os.path.join(os.path.dirname(websockify.__file__), "web"))
PY
)"
[ -f "${NOVNC_WEB}/vnc.html" ] || { log "noVNC web assets not found at ${NOVNC_WEB}, aborting."; exit 1; }

log "noVNC web assets: ${NOVNC_WEB}"
log "starting noVNC bridge on 0.0.0.0:6080 -> 127.0.0.1:${QT_QPA_VNC_PORT:-5900}"
exec websockify --web="${NOVNC_WEB}" 0.0.0.0:6080 "127.0.0.1:${QT_QPA_VNC_PORT:-5900}"
