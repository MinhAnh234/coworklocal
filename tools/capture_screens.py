"""Capture every CoworkLocal screen to PNG, offscreen, for the UI audit page.

Run:  python tools/capture_screens.py

Two safety measures, both mandatory — this script drives the REAL application:

1. **Data isolation.** ``config.CONFIG_DIR`` is ``Path.home() / ".cowork_local"``, a
   module-level constant resolved at import time. We copy that folder to a temp
   directory and repoint ``USERPROFILE``/``HOME`` at it *before* importing
   ``cowork_local``, so every write the app makes lands in the copy. The user's
   real data is never opened for writing.

2. **Schedulers disabled.** ``MainWindow.__init__`` starts ``TaskScheduler`` and
   ``RoutingScheduler``, which would *execute the user's scheduled tasks* — real
   agent turns writing real files. Both ``start`` methods are patched to no-ops
   before the window is built.

We also construct ``MainWindow`` directly rather than calling ``app.run()``:
``run()`` seeds built-in skills/flows and calls ``ctx.config.save()``.

Screens that fail to render (QtWebEngine generally cannot initialise offscreen)
are recorded in the manifest with their error. They are never silently skipped —
the audit page renders an explicit "could not capture" placeholder for them.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent      # …/cowork_local
OUT_DIR = REPO / "docs" / "screens"
THEMES = ("dark", "light")


def _own_member(widget, name: str) -> bool:
    """True when `name` is declared by the app on `widget`, not inherited from Qt.

    Instance attributes live in ``vars(widget)``; methods live on the class, so
    both are checked. Only classes defined inside ``cowork_local`` count, so a
    Qt base class that happens to use the same name can never be mistaken for
    the app's own control.
    """
    if name in vars(widget):
        return True
    for base in type(widget).__mro__:
        if getattr(base, "__module__", "").startswith("cowork_local") and name in vars(base):
            return True
    return False


def owner_of(root, name: str):
    """The widget in `root`'s subtree that actually holds `name` today.

    EPIC R08 split every screen's god-widget into child widgets, so a control
    that used to be ``tab.gran_combo`` now lives at ``tab.chart.gran_combo``,
    and ``ScheduleTaskTab.columns`` moved to ``ScheduleTaskTab.kanban.columns``.
    Checkers ask for a control by name and get back whichever widget owns it
    today, so a further split does not break them again — while a control that
    is genuinely gone still returns ``None`` and is still reported as a loss.

    Breadth-first, so the shallowest owner wins if a name appears twice.
    """
    from PySide6.QtWidgets import QWidget

    seen: set[int] = set()
    queue = [root]
    while queue:
        w = queue.pop(0)
        if id(w) in seen:
            continue
        seen.add(id(w))
        if _own_member(w, name):
            return w
        queue.extend(c for c in w.children() if isinstance(c, QWidget))
    return None


def control(root, name: str, default=None):
    """The control named `name` anywhere in `root`'s subtree — see `owner_of`.

    Falls back to a plain ``getattr`` on `root` so a screen that already bridges
    its old attribute names itself keeps working: ``MonitoringTab.__getattr__``
    maps ``ov_*`` onto the extracted tabs, and a name served that way is on no
    widget's ``__dict__`` for `owner_of` to find.
    """
    holder = owner_of(root, name)
    if holder is not None:
        return getattr(holder, name, default)
    return getattr(root, name, default)


def _isolate_home() -> Path:
    """Copy the real config dir into a temp HOME and repoint the env at it."""
    real = Path.home() / ".cowork_local"
    sandbox = Path(tempfile.mkdtemp(prefix="cowork-capture-"))
    if real.exists():
        shutil.copytree(real, sandbox / ".cowork_local", dirs_exist_ok=True)
    else:
        (sandbox / ".cowork_local").mkdir(parents=True, exist_ok=True)
    for var in ("USERPROFILE", "HOME"):
        os.environ[var] = str(sandbox)
    os.environ.pop("HOMEDRIVE", None)
    os.environ.pop("HOMEPATH", None)
    return sandbox


def _load_fonts() -> int:
    """Register system fonts with the offscreen platform.

    The offscreen plugin ships with NO font database (``QFontDatabase.families()``
    returns an empty list), so every glyph renders as a tofu box — unusable when
    the screenshots are the deliverable. Loading the real Windows faces fixes
    both Latin and Vietnamese diacritics, and Consolas covers the code views.
    """
    from PySide6.QtGui import QFontDatabase

    wanted = [
        "SegUIVar.ttf", "segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf",
        "seguisb.ttf", "consola.ttf", "consolab.ttf", "arial.ttf",
    ]
    root = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Fonts"
    loaded = 0
    for name in wanted:
        path = root / name
        if path.exists() and QFontDatabase.addApplicationFont(str(path)) != -1:
            loaded += 1
    return loaded


def _apply_theme(app, name: str | None = None) -> str:
    """Load the app's real stylesheet onto `app`.

    `MainWindow` does not style itself — `run()` calls `app.setStyleSheet` — so a
    checker that builds the window directly measures a window with no padding,
    no margins and no borders. Every QSS-driven layout bug is invisible there.
    """
    from cowork_local import theme
    from cowork_local.config import AppConfig

    name = name or AppConfig.load().theme
    theme.set_active_theme(name)
    app.setStyleSheet(theme.stylesheet(name))
    return name


def _freeze_schedulers() -> None:
    """No-op the background engines so nothing is executed while we capture."""
    from cowork_local.core.task_scheduler import TaskScheduler
    TaskScheduler.start = lambda self: None                      # type: ignore[assignment]
    try:
        from cowork_local.core.routing.scheduler import RoutingScheduler
        RoutingScheduler.start = lambda self: None                # type: ignore[assignment]
    except Exception:
        pass


def main() -> int:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sandbox = _isolate_home()
    sys.path.insert(0, str(REPO.parent))        # so `import cowork_local` works
    sys.path.insert(0, str(Path(__file__).resolve().parent))   # sibling: seed_demo_data
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    app = QApplication([])

    n_fonts = _load_fonts()
    print(f"[fonts] registered {n_fonts} face(s) with the offscreen platform")
    if not n_fonts:
        print("  WARNING: no fonts loaded — every screenshot will render as tofu boxes")

    _freeze_schedulers()

    import cowork_local.theme as theme
    from cowork_local.config import AppConfig, CONFIG_DIR
    from cowork_local.i18n import set_language, tr
    from cowork_local.state import AppContext

    assert str(sandbox) in str(CONFIG_DIR), (
        f"isolation failed: CONFIG_DIR={CONFIG_DIR} is not inside {sandbox}")
    print(f"[isolated] CONFIG_DIR -> {CONFIG_DIR}")

    # Fill the sandbox with demo data so the screenshots show a working app.
    # Safe by construction: seed() re-asserts it is inside a capture sandbox.
    from seed_demo_data import seed
    counts = seed()
    print("[seeded] " + " · ".join(f"{k}={v}" for k, v in counts.items()))

    from cowork_local.app import MainWindow

    cfg = AppConfig.load()
    set_language("vi")
    ctx = AppContext(cfg)

    manifest: list[dict] = []
    # Label of the nav row selected right now, recorded into every shot so the
    # "is the rail pointing at the right thing?" question is machine-checked
    # instead of eyeballed across 54 images.
    nav_state = {"label": "", "expected": ""}

    def nav_to(win, page: int, sub=None, expect: str = "") -> None:
        """Navigate the way a user does, and record where the rail ends up.

        Since the rail became a flat list, ``_goto`` moves the highlight itself
        (``_select_nav_row``), so this no longer needs the two-step workaround
        that existed while selecting a Workspace child destroyed the row being
        selected.
        """
        win._ensure_page(page)
        win._goto(page, sub)
        app.processEvents()
        app.processEvents()
        cur = next((t.currentItem() for t in (win.nav, win.nav_bottom)
                    if t.currentItem() is not None and t.currentItem().isSelected()),
                   None)
        nav_state["label"] = cur.text(0) if cur is not None else ""
        nav_state["expected"] = expect or nav_state["label"]

    def shot(widget, slug: str, title: str, note: str = "") -> None:
        """Grab `widget` for the active theme; record success or the error."""
        rec = {"slug": slug, "title": title, "theme": theme.current_theme(),
               "note": note, "file": "", "error": "",
               "nav": nav_state["label"], "nav_expected": nav_state["expected"]}
        try:
            app.processEvents()
            app.processEvents()
            pm = widget.grab()
            if pm.isNull() or pm.width() < 2:
                raise RuntimeError("grab() returned an empty pixmap")
            name = f"{slug}-{theme.current_theme()}.png"
            pm.save(str(OUT_DIR / name))
            rec["file"] = f"screens/{name}"
            print(f"  ok    {name}  ({pm.width()}x{pm.height()})")
        except Exception as exc:                                  # noqa: BLE001
            rec["error"] = f"{type(exc).__name__}: {exc}"
            print(f"  FAIL  {slug}: {rec['error']}")
        manifest.append(rec)

    for th in THEMES:
        print(f"\n=== theme: {th} ===")
        ctx.config.theme = th
        theme.set_active_theme(th)
        app.setStyleSheet(theme.stylesheet(th))

        win = MainWindow(ctx, user_name="local")
        win.resize(1600, 1000)
        win.show()
        app.processEvents()

        # ---- main screens, driven through the app's own navigation API ------
        ROW_DASH, ROW_SCHED, ROW_WS, ROW_MON = 0, 1, 2, 3

        nav_to(win, ROW_DASH, None, expect=tr("app.tab.dashboard"))
        shot(win, "dashboard", "Dashboard", "ui/dashboard_tab.py:35")

        nav_to(win, ROW_SCHED, None, expect=tr("app.tab.schedule"))
        sched = win._page_widgets[ROW_SCHED]
        shot(win, "schedule-kanban", "Schedule Task — Kanban", "ui/schedule_task_tab.py:70")
        try:                        # combo index 1 == Calendar view
            sched.view_combo.setCurrentIndex(1)
            app.processEvents()
            shot(win, "schedule-calendar", "Schedule Task — Calendar", "ui/calendar_view.py:88")
            sched.view_combo.setCurrentIndex(0)
        except Exception as exc:                                  # noqa: BLE001
            manifest.append({"slug": "schedule-calendar", "title": "Schedule Task — Calendar",
                             "theme": th, "note": "ui/calendar_view.py:88", "file": "",
                             "error": f"{type(exc).__name__}: {exc}"})
            print(f"  FAIL  schedule-calendar: {exc}")

        # Workspace: capture with no project selected, then with one selected so
        # the project-gated sub-tabs (Cowork, GraphRAG) actually exist.
        nav_to(win, ROW_WS, None, expect=tr("app.tab.workspace"))
        ws = win.workspace
        shot(win, "workspace-project", "Workspace ▸ Project", "ui/workspace_tab.py:188")
        try:
            if ws.project_list.count():
                ws.project_list.setCurrentRow(0)
                app.processEvents()
        except Exception:                                          # noqa: BLE001
            pass

        for attr, slug, title, note in (
            ("_cowork_tab_idx",   "workspace-cowork",   "Workspace ▸ Cowork",   "ui/cowork_tab.py:21"),
            ("_co4e_tab_idx",     "workspace-co4e",     "Workspace ▸ Co4E",     "ui/co4e_tab.py:228"),
            ("_folder_tab_idx",   "workspace-folder",   "Workspace ▸ Folder",   "ui/folder_tab.py:238"),
            ("_graphrag_tab_idx", "workspace-graphrag", "Workspace ▸ GraphRAG", "ui/structure_graph_view.py:188"),
        ):
            idx = getattr(ws, attr, None)
            if idx is None:
                manifest.append({"slug": slug, "title": title, "theme": th, "note": note,
                                 "file": "", "error": "sub-tab index not present"})
                continue
            nav_to(win, ROW_WS, idx, expect=ws.tabs.tabText(idx))
            shot(win, slug, title, note)

        # Monitoring: enumerate its sub-tabs from the app itself.
        nav_to(win, ROW_MON, None, expect=tr("app.tab.monitoring"))
        mon = win._page_widgets[ROW_MON]
        try:
            subs = mon.nav_subtabs()
        except Exception as exc:                                   # noqa: BLE001
            subs = []
            print(f"  FAIL  monitoring subtabs: {exc}")
        for label, sub, _icon in subs:
            nav_to(win, ROW_MON, sub, expect=label)
            slug = "monitoring-" + "".join(
                c.lower() if c.isalnum() else "-" for c in label).strip("-")
            shot(win, slug, f"Monitoring ▸ {label}", "ui/monitoring_tab.py:132")

        # Dialogs/overlays below are not nav destinations.
        nav_state["label"] = nav_state["expected"] = ""

        # ---- dialogs: built directly and shown (never exec(), it blocks) -----
        for slug, title, note, build in _dialog_specs(ctx, win):
            try:
                dlg = build()
                dlg.show()
                app.processEvents()
                shot(dlg, slug, title, note)
                dlg.close()
            except Exception as exc:                               # noqa: BLE001
                manifest.append({"slug": slug, "title": title, "theme": th, "note": note,
                                 "file": "", "error": f"{type(exc).__name__}: {exc}"})
                print(f"  FAIL  {slug}: {type(exc).__name__}: {exc}")

        # ---- overlays --------------------------------------------------------
        try:
            help_dock = win.help_agent
            help_dock._expand()
            app.processEvents()
            shot(help_dock, "overlay-help-panel", "Help dock — expanded panel",
                 "ui/help_agent_widget.py:79")
        except Exception as exc:                                   # noqa: BLE001
            print(f"  FAIL  overlay-help-panel: {exc}")

        win.close()

    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    bad_nav = [r for r in manifest
               if r["nav_expected"] and r["nav"] != r["nav_expected"]]
    checked = sum(1 for r in manifest if r["nav_expected"])
    print(f"\n[nav] rail selection matches the screen: {checked - len(bad_nav)}/{checked}")
    for r in bad_nav:
        print(f"  MISMATCH {r['slug']} [{r['theme']}]: "
              f"rail says '{r['nav']}', screen is '{r['nav_expected']}'")

    ok = sum(1 for r in manifest if r["file"])
    bad = [r for r in manifest if not r["file"]]
    print(f"\ncaptured {ok}/{len(manifest)}")
    if bad:
        print("could NOT capture (recorded in manifest, shown as placeholders):")
        for r in bad:
            print(f"  - {r['slug']} [{r['theme']}]: {r['error']}")
    print(f"sandbox (safe to delete): {sandbox}")
    return 0


def _dialog_specs(ctx, win):
    """(slug, title, note, factory) for each dialog we can build headlessly.

    Signatures differ per dialog (some take ctx first, some take parent first,
    some require a real model object) — each factory below matches the actual
    ``__init__`` it calls, not a guessed one.
    """
    # NOTE: two different classes share the name `CustomAgent` —
    # core/custom_agents.py:23 and core/co4e.py:117. Co4EAgentDialog uses the
    # co4e one (it has `.role`); importing the other raises AttributeError.
    from cowork_local.core.co4e import CustomAgent
    from cowork_local.ui.settings_dialog import SettingsDialog
    from cowork_local.ui.task_editor_dialog import TaskEditorDialog
    from cowork_local.ui.skills_dialog import SkillsDialog, SkillEditDialog
    from cowork_local.ui.file_edit_dialog import FileEditDialog
    from cowork_local.ui.co4e_agent_dialog import Co4EAgentDialog
    from cowork_local.ui.ext_connector_dialog import ExtConnectorEditDialog
    from cowork_local.ui.permission_dialog import PermissionDialog
    from cowork_local.ui.agents_admin_tab import AgentEditDialog
    from cowork_local.ui.login_dialog import LoginDialog

    return [
        # SettingsDialog(ctx, parent)
        ("dialog-settings", "Settings", "ui/settings_dialog.py:26",
         lambda: SettingsDialog(ctx, win)),
        # TaskEditorDialog(task, all_tasks, parent, ctx)
        ("dialog-task-editor", "Task Editor", "ui/task_editor_dialog.py:55",
         lambda: TaskEditorDialog(None, [], win, ctx)),
        # SkillsDialog(parent, ctx)
        ("dialog-skills", "Skills manager", "ui/skills_dialog.py:108",
         lambda: SkillsDialog(win, ctx)),
        # SkillEditDialog(parent, skill, ctx)
        ("dialog-skill-edit", "Skill editor", "ui/skills_dialog.py:23",
         lambda: SkillEditDialog(win, None, ctx)),
        ("dialog-file-edit", "File view & AI edit", "ui/file_edit_dialog.py:50",
         lambda: FileEditDialog(ctx, "", win)),
        # Co4EAgentDialog(ctx, agent, skill_names, parent) — agent must be real
        ("dialog-co4e-agent", "Co4E agent editor", "ui/co4e_agent_dialog.py:23",
         lambda: Co4EAgentDialog(ctx, CustomAgent(id="preview"), [], win)),
        # ExtConnectorEditDialog(parent, category, connector)
        ("dialog-ext-connector", "External connector", "ui/ext_connector_dialog.py:23",
         lambda: ExtConnectorEditDialog(win, "other", None)),
        # PermissionDialog(action, parent) — `preview` is a dict, not a string
        ("dialog-permission", "Permission request", "ui/permission_dialog.py:13",
         lambda: PermissionDialog(
             {"name": "run_command",
              "preview": {"title": "Run command", "kind": "command",
                          "text": "npm install --save-dev vitest"}}, win)),
        # AgentEditDialog(parent, ctx, agent, default_model_hint)
        ("dialog-agent-edit", "Admin agent editor", "ui/agents_admin_tab.py:35",
         lambda: AgentEditDialog(win, ctx, None, "")),
        ("dialog-login", "Login (dead screen — not wired)", "ui/login_dialog.py:57",
         lambda: LoginDialog(ctx, win)),
    ]


if __name__ == "__main__":
    raise SystemExit(main())
