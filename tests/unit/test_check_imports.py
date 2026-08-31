"""Unit tests for the Clean Architecture AST Import Guard (check_imports.py)."""
from __future__ import annotations

from pathlib import Path
from scripts.check_imports import FORBIDDEN_MODULE_PREFIXES, scan_file


def test_clean_python_file_passes(tmp_path: Path) -> None:
    """Verify that pure Python code without GUI imports produces 0 violations."""
    clean_code = """
import os
import json
from dataclasses import dataclass
from typing import List

@dataclass
class UserRequest:
    id: str
    prompt: str
"""
    clean_file = tmp_path / "clean_service.py"
    clean_file.write_text(clean_code, encoding="utf-8")

    violations = scan_file(clean_file, FORBIDDEN_MODULE_PREFIXES)
    assert len(violations) == 0


def test_forbidden_pyside_import_detected(tmp_path: Path) -> None:
    """Verify that PySide6 import is caught with correct line number."""
    dirty_code = """
from dataclasses import dataclass
from PySide6.QtWidgets import QWidget

class BadService:
    pass
"""
    dirty_file = tmp_path / "bad_service.py"
    dirty_file.write_text(dirty_code, encoding="utf-8")

    violations = scan_file(dirty_file, FORBIDDEN_MODULE_PREFIXES)
    assert len(violations) == 1
    assert violations[0].line_number == 3
    assert "PySide6" in violations[0].imported_module


def test_forbidden_ui_and_app_import_detected(tmp_path: Path) -> None:
    """Verify that importing concrete UI or app modules from domain is caught."""
    dirty_code = """
import ui.chat_panel
from app import MainWindow
"""
    dirty_file = tmp_path / "cross_layer_leak.py"
    dirty_file.write_text(dirty_code, encoding="utf-8")

    violations = scan_file(dirty_file, FORBIDDEN_MODULE_PREFIXES)
    assert len(violations) == 2
    modules = [v.imported_module for v in violations]
    assert "ui.chat_panel" in modules
    assert "app" in modules
