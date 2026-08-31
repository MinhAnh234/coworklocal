"""Workspace file operations for non-agent-loop callers (EPIC R06, R08)."""

from .ai_edit_output import parse_ai_output, split_code_block
from .file_preview_helpers import is_probably_text, pptx_available, read_text
from .file_workspace_service import FileWorkspaceService
from .graph_index_service import extract_file_contents, pdf_to_markdown

__all__ = [
    "FileWorkspaceService",
    "read_text",
    "is_probably_text",
    "pptx_available",
    "split_code_block",
    "parse_ai_output",
    "pdf_to_markdown",
    "extract_file_contents",
]
