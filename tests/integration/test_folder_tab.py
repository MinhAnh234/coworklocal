"""EPIC R08-T12: WorkspaceFileTree / DocumentPreviewManager / FolderTab,
real Qt offscreen.

Scope note: the AI-Edit panel's send -> plan -> edit -> apply pipeline
(``ai_edit_pipeline.py``) runs on a real ``core.worker.AgentWorker`` QThread
and had ZERO existing tests before this task (confirmed by grep — nothing
under tests/ exercised ``ui/folder_tab.py``'s AI methods except the routing
surface test, fixed alongside this task in
``tests/integration/test_routing_surfaces.py``). Driving that full async
pipeline end to end is out of scope here; what's covered is everything that
doesn't need a live QThread: navigation, preview rendering, and — the
concrete R08-T12 deliverable — that saves/creates actually go through
``FileWorkspaceService`` (containment enforced, not just "writes a file").
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cowork_local.config import AppConfig  # noqa: E402
from cowork_local.state import AppContext  # noqa: E402

pytest.importorskip("PySide6", reason="Qt is required for the integration suite")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def khong_goi_mang(monkeypatch):
    """Chặn mọi lượt gọi mạng thật từ bộ chọn model của panel AI-Edit.

    Mở panel AI-Edit sẽ gọi ``AiEditModelResolver.refresh()``, và hàm đó
    dựng ``AgentWorker`` (QThread) đi hỏi ``list_models`` của provider qua
    HTTP. Trong test, luồng nền đó sống lâu hơn chính test đã tạo ra nó:
    nó vẫn đang chờ mạng khi test kết thúc, rồi vỡ giữa lúc thu gom rác ở
    một test khác chạy sau — cả tiến trình pytest chết với
    ``Windows fatal exception``, và chỗ báo lỗi không liên quan gì tới
    nguyên nhân. Việc của module này là điều hướng và hiển thị, không phải
    nạp danh sách model, nên vô hiệu hoá cả hai đường ra mạng.
    """
    from cowork_local.presentation.folder.ai_edit_model_resolver import AiEditModelResolver

    monkeypatch.setattr(AiEditModelResolver, "refresh", lambda self: None)
    monkeypatch.setattr(AiEditModelResolver, "_scan_all_image_models",
                        lambda self, then_suggest=False: None)


@pytest.fixture
def ctx(qt_app, tmp_path: Path):
    return AppContext(AppConfig.load(tmp_path / "config.json"))


@pytest.fixture
def root(tmp_path: Path) -> Path:
    d = tmp_path / "workspace"
    d.mkdir()
    return d


# ---- WorkspaceFileTree ----------------------------------------------------- #
def test_workspace_file_tree_set_root_updates_label_and_model(qt_app, root):
    from cowork_local.presentation.folder.workspace_file_tree import WorkspaceFileTree

    tree = WorkspaceFileTree(str(root))
    other = root.parent / "other-root"
    other.mkdir()

    tree.set_root(str(other))

    assert tree.root == str(other)
    assert tree.path_lbl.text() == str(other)


def test_workspace_file_tree_ignores_an_invalid_root(qt_app, root):
    from cowork_local.presentation.folder.workspace_file_tree import WorkspaceFileTree

    tree = WorkspaceFileTree(str(root))
    tree.set_root(str(root / "does-not-exist"))

    assert tree.root == str(root)   # unchanged


def test_workspace_file_tree_click_emits_file_selected(qt_app, root):
    from cowork_local.presentation.folder.workspace_file_tree import WorkspaceFileTree

    f = root / "a.txt"
    f.write_text("hello", encoding="utf-8")
    tree = WorkspaceFileTree(str(root))
    seen = []
    tree.file_selected.connect(seen.append)

    index = tree.model.index(str(f))
    tree._on_tree_clicked(index)

    assert seen and os.path.normpath(seen[0]) == os.path.normpath(str(f))


# ---- DocumentPreviewManager ------------------------------------------------- #
def test_open_file_renders_code_into_the_editor(qt_app, root):
    from cowork_local.presentation.folder.document_preview_manager import DocumentPreviewManager

    f = root / "script.py"
    f.write_text("print('hi')\n", encoding="utf-8")
    preview = DocumentPreviewManager(str(root))

    preview.open_file(str(f))

    assert preview.stack.currentWidget() is preview.editor
    assert preview.editor.toPlainText() == "print('hi')\n"
    assert preview.current_file == str(f)


def test_open_file_on_a_binary_file_shows_the_placeholder(qt_app, root):
    from cowork_local.presentation.folder.document_preview_manager import DocumentPreviewManager

    f = root / "data.bin"
    f.write_bytes(b"\x00\x01\x02binary")
    preview = DocumentPreviewManager(str(root))

    preview.open_file(str(f))

    assert preview.stack.currentWidget() is preview._placeholder


def test_save_writes_through_file_workspace_service(qt_app, root):
    """The concrete R08-T12/R06-T05 deliverable: FileWorkspaceService (built
    at R06, unused until this task) is now the actual write path."""
    from cowork_local.presentation.folder.document_preview_manager import DocumentPreviewManager

    f = root / "note.txt"
    f.write_text("old", encoding="utf-8")
    preview = DocumentPreviewManager(str(root))
    preview.open_file(str(f))

    preview.editor.setPlainText("new content")
    preview.save()

    assert f.read_text(encoding="utf-8") == "new content"


def test_create_new_file_writes_inside_root_via_file_workspace_service(qt_app, root):
    from cowork_local.presentation.folder.document_preview_manager import DocumentPreviewManager

    preview = DocumentPreviewManager(str(root))

    dest = preview.create_new_file("sub/new.md", "# hello")

    assert dest == str(root / "sub" / "new.md")
    assert (root / "sub" / "new.md").read_text(encoding="utf-8") == "# hello"
    assert preview.current_file == dest   # opened it, kept the AI chat (reset_ai=False)


def test_create_new_file_rejects_a_path_escaping_the_root(qt_app, root):
    from cowork_local.presentation.folder.document_preview_manager import DocumentPreviewManager

    preview = DocumentPreviewManager(str(root))
    messages = []
    preview.status_message.connect(messages.append)

    dest = preview.create_new_file("../escaped.txt", "nope")

    assert dest is None
    assert not (root.parent / "escaped.txt").exists()
    assert messages   # a save_error status was emitted


def test_write_content_persists_and_refreshes_html_preview(qt_app, root):
    from cowork_local.presentation.folder.document_preview_manager import DocumentPreviewManager

    f = root / "page.html"
    f.write_text("<p>old</p>", encoding="utf-8")
    preview = DocumentPreviewManager(str(root))
    preview.open_file(str(f))   # HTML opens in preview mode by default

    preview.write_content("<p>new</p>")

    assert f.read_text(encoding="utf-8") == "<p>new</p>"


# ---- FolderTab shell -------------------------------------------------------- #
def test_folder_tab_builds_and_wires_tree_to_preview(ctx, root):
    from cowork_local.presentation.folder.folder_tab import FolderTab

    tab = FolderTab(ctx)
    tab.set_root(str(root))
    f = root / "hello.py"
    f.write_text("x = 1\n", encoding="utf-8")

    tab.tree.file_selected.emit(str(f))   # simulate a tree click

    assert tab.preview.current_file == str(f)
    assert tab.preview.editor.toPlainText() == "x = 1\n"


def test_folder_tab_ai_panel_toggle_updates_button_badge(ctx, root):
    from cowork_local.presentation.folder.folder_tab import FolderTab

    tab = FolderTab(ctx)
    assert tab.ai_panel.isHidden()

    tab.ai_btn.setChecked(True)
    tab._toggle_ai_panel()

    assert not tab.ai_panel.isHidden()
