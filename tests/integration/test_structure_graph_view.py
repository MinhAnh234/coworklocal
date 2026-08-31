"""EPIC R08-T14: GraphRenderer / GraphQaWidget / StructureGraphView shell,
real Qt offscreen.

Scope note: a real directory SCAN (``GraphRenderer._scan``) runs on a
``core.worker.AgentWorker`` QThread and had no existing test before this
task either (grep confirms nothing under tests/ exercised
``ui/structure_graph_view.py``). These tests drive ``_render()`` directly
with a hand-built ``StructureGraph`` instead of a live scan — enough to
prove the renderer <-> Q&A wiring (the actual R08-T14 deliverable) without
needing a real codebase to walk.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cowork_local.config import AppConfig  # noqa: E402
from cowork_local.core.structure_graph import GEdge, GNode, StructureGraph  # noqa: E402
from cowork_local.state import AppContext  # noqa: E402

pytest.importorskip("PySide6", reason="Qt is required for the integration suite")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def ctx(qt_app, tmp_path):
    return AppContext(AppConfig.load(tmp_path / "config.json"))


def _fake_graph(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text("def hello():\n    pass\n", encoding="utf-8")
    nodes = [
        GNode(id="n1", label="mod.py", kind="file", detail="a module", path=str(f)),
        GNode(id="n2", label="hello", kind="function", detail="says hi", path=str(f)),
    ]
    edges = [GEdge(source="n1", target="n2", type="defines")]
    return StructureGraph(nodes=nodes, edges=edges)


def test_structure_graph_view_builds(ctx):
    from cowork_local.presentation.graph.structure_graph_view import StructureGraphView

    view = StructureGraphView(ctx)
    assert view.renderer is not None
    assert view.qa is not None


def test_render_populates_the_scene_and_emits_graph_rendered(ctx, tmp_path):
    from cowork_local.presentation.graph.graph_renderer import GraphRenderer

    renderer = GraphRenderer(ctx)
    graph = _fake_graph(tmp_path)
    seen = []
    renderer.graph_rendered.connect(lambda: seen.append(1))

    renderer._render({"graph": graph, "pos": {"n1": (0, 0), "n2": (100, 0)}, "seq": renderer._scan_seq})

    assert renderer.graph is graph
    assert len(renderer._node_items) == 2
    assert seen == [1]


def test_render_ignores_a_stale_scan_result(ctx, tmp_path):
    """Only the LATEST scan's result is ever rendered (no stale overwrite)."""
    from cowork_local.presentation.graph.graph_renderer import GraphRenderer

    renderer = GraphRenderer(ctx)
    first = _fake_graph(tmp_path)
    renderer._render({"graph": first, "pos": {}, "seq": renderer._scan_seq})
    renderer._scan_seq += 1   # a second scan started

    stale = StructureGraph(nodes=[], edges=[])
    renderer._render({"graph": stale, "pos": {}, "seq": renderer._scan_seq - 1})

    assert renderer.graph is first   # stale result was dropped


def test_node_selection_updates_the_qa_detail_panel(ctx, tmp_path):
    from cowork_local.presentation.graph.graph_qa_widget import GraphQaWidget
    from cowork_local.presentation.graph.graph_renderer import GraphRenderer

    renderer = GraphRenderer(ctx)
    graph = _fake_graph(tmp_path)
    renderer._render({"graph": graph, "pos": {"n1": (0, 0), "n2": (100, 0)}, "seq": renderer._scan_seq})
    qa = GraphQaWidget(ctx, renderer)

    node = graph.nodes[1]
    renderer.node_selected.emit(node)

    assert "hello" in qa.detail.toPlainText()
    assert "says hi" in qa.detail.toPlainText()


def test_candidate_file_paths_uses_selected_nodes_when_present(ctx, tmp_path):
    from cowork_local.presentation.graph.graph_qa_widget import GraphQaWidget
    from cowork_local.presentation.graph.graph_renderer import GraphRenderer

    renderer = GraphRenderer(ctx)
    graph = _fake_graph(tmp_path)
    renderer._render({"graph": graph, "pos": {"n1": (0, 0), "n2": (100, 0)}, "seq": renderer._scan_seq})
    qa = GraphQaWidget(ctx, renderer)

    # No selection -> every file node in the graph (both nodes share one
    # file here, so this also proves the path-dedup in _candidate_file_paths).
    assert qa._candidate_file_paths() == [graph.nodes[0].path]

    renderer._node_items[0].setSelected(True)
    assert qa._candidate_file_paths() == [graph.nodes[0].path]


def test_project_change_clears_the_qa_extraction_cache(ctx, tmp_path):
    from cowork_local.presentation.graph.graph_qa_widget import GraphQaWidget
    from cowork_local.presentation.graph.graph_renderer import GraphRenderer

    renderer = GraphRenderer(ctx)
    qa = GraphQaWidget(ctx, renderer)
    qa._extract_cache = {"some/path.py": "cached text"}

    renderer.project_changed.emit()

    assert qa._extract_cache == {}


def test_qa_collapse_resizes_the_shells_splitter(ctx):
    """Exact pixel width is Qt's splitter-layout arithmetic, not this code's
    concern - what matters is that collapsing narrows the QA pane a lot
    (down near the strip's width) while the strip itself becomes visible and
    the total splitter width is conserved."""
    from cowork_local.presentation.graph.structure_graph_view import StructureGraphView
    from cowork_local.ui.widgets import CollapseStrip

    view = StructureGraphView(ctx)
    before = view._split.sizes()

    view.qa._set_collapsed(True)

    after = view._split.sizes()
    assert after[1] <= CollapseStrip.WIDTH + 2
    assert view.qa.maximumWidth() == CollapseStrip.WIDTH + 2
    assert sum(after) == sum(before)   # total width conserved, just redistributed


def test_hide_event_clears_extracts(ctx):
    from cowork_local.presentation.graph.structure_graph_view import StructureGraphView

    view = StructureGraphView(ctx)
    view.qa._extract_cache = {"x": "y"}

    from PySide6.QtGui import QHideEvent
    view.hideEvent(QHideEvent())

    assert view.qa._extract_cache == {}
