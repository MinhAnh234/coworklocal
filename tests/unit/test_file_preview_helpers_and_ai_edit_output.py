"""EPIC R08-T12: pure helpers moved out of ui/folder_tab.py into
application/workspaces/ (file_preview_helpers.py, ai_edit_output.py) — no Qt,
directly unit-testable, unlike when they lived as private module functions
inside the Qt widget file.
"""
from __future__ import annotations

from cowork_local.application.workspaces.ai_edit_output import (
    parse_ai_output,
    split_code_block,
)
from cowork_local.application.workspaces.file_preview_helpers import (
    is_probably_text,
    read_text,
)


def test_read_text_returns_file_contents(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    assert read_text(str(f)) == "hello"


def test_read_text_on_missing_file_returns_a_note_not_raise(tmp_path):
    result = read_text(str(tmp_path / "missing.txt"))
    assert "could not read file" in result


def test_is_probably_text_true_for_utf8(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello world", encoding="utf-8")
    assert is_probably_text(str(f)) is True


def test_is_probably_text_false_for_null_bytes(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"\x00\x01\x02")
    assert is_probably_text(str(f)) is False


def test_split_code_block_extracts_fenced_block_and_summary():
    text = "Here is the change:\n\n```python\nprint('hi')\n```"
    content, summary = split_code_block(text)
    assert content == "print('hi')\n"
    assert summary == "Here is the change:"


def test_split_code_block_no_fence_returns_none_and_full_text():
    content, summary = split_code_block("just prose, no code")
    assert content is None
    assert summary == "just prose, no code"


def test_parse_ai_output_extracts_file_target():
    text = "FILE: new/thing.py\n```python\nx = 1\n```"
    target, content, summary, image_gens = parse_ai_output(text)
    assert target == "new/thing.py"
    assert content == "x = 1\n"
    assert image_gens == []


def test_parse_ai_output_extracts_image_gen_directives():
    text = ("Adding an illustration.\n"
            "IMAGE_GEN: a red fox in a forest => assets/fox.png\n"
            "```html\n<img src='assets/fox.png'>\n```")
    target, content, summary, image_gens = parse_ai_output(text)
    assert image_gens == [("a red fox in a forest", "assets/fox.png")]
    assert "IMAGE_GEN" not in summary


def test_parse_ai_output_no_directives_or_code_block():
    target, content, summary, image_gens = parse_ai_output("just an answer")
    assert target is None
    assert content is None
    assert image_gens == []
    assert summary == "just an answer"
