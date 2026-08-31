"""EPIC R08-T14: graph_index_service.py — pure helpers moved out of
ui/structure_graph_view.py, no Qt.
"""
from __future__ import annotations

from cowork_local.application.workspaces.graph_index_service import extract_file_contents


def test_extract_file_contents_reads_text_files(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("print('hello')\n", encoding="utf-8")

    block, cache = extract_file_contents([str(f)], {}, str(tmp_path))

    assert "print('hello')" in block
    assert str(f) in cache
    assert cache[str(f)]


def test_extract_file_contents_reuses_the_cache(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("original", encoding="utf-8")
    seed_cache = {str(f): "cached content, not re-read"}

    block, cache = extract_file_contents([str(f)], seed_cache, str(tmp_path))

    assert "cached content, not re-read" in block


def test_extract_file_contents_skips_unreadable_paths_without_raising(tmp_path):
    missing = tmp_path / "does-not-exist.txt"
    block, cache = extract_file_contents([str(missing)], {}, str(tmp_path))
    assert block == ""


def test_extract_file_contents_respects_max_total_budget(tmp_path):
    f1 = tmp_path / "a.txt"
    f1.write_text("x" * 100, encoding="utf-8")
    f2 = tmp_path / "b.txt"
    f2.write_text("y" * 100, encoding="utf-8")

    block, cache = extract_file_contents([str(f1), str(f2)], {}, str(tmp_path), max_total=50)

    assert len(block) < 250   # bounded, not both files in full
