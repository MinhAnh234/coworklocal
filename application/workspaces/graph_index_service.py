"""Temporary file-content extraction for Graph-RAG Q&A (R08-T14, moved out
of ``ui/structure_graph_view.py`` — that file's module-level
``_pdf_to_markdown``/``_extract_file_contents``, lines 964-1034 of the
original 1035-line file). Runs inside the ask worker's job function so the
answer is synthesized from real file content, not just the graph structure.

Pure Python: no Qt. Best-effort throughout (never raises) — a failed
extraction degrades to "no content for this file", not a broken Q&A turn.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple


def pdf_to_markdown(pdf_path: str, out_dir: str) -> Optional[str]:
    """Convert a PDF to Markdown with opendataloader-pdf when available
    (richer structure than a plain text dump). Best-effort — returns None
    if the package isn't installed or the call fails, so the caller falls
    back to ``core/doc_extract.py``."""
    try:
        import opendataloader_pdf  # optional; auto-installed elsewhere if present
    except Exception:  # noqa: BLE001
        try:
            from cowork_local.core.deps import ensure_module
            if ensure_module("opendataloader_pdf", "opendataloader-pdf") is None:
                return None
            import opendataloader_pdf  # noqa: F811
        except Exception:  # noqa: BLE001
            return None
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for call in (
        lambda: opendataloader_pdf.convert(input_path=[str(pdf_path)], output_dir=str(out),
                                           generate_markdown=True),
        lambda: opendataloader_pdf.convert(input_path=str(pdf_path), output_dir=str(out)),
        lambda: opendataloader_pdf.convert(str(pdf_path), str(out)),
    ):
        try:
            call()
            break
        except TypeError:
            continue
        except Exception:  # noqa: BLE001
            return None
    mds = list(out.rglob(Path(pdf_path).stem + "*.md")) or list(out.rglob("*.md"))
    for md in mds:
        try:
            return md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return None


def extract_file_contents(paths: List[str], cache: Dict[str, str], tmp_dir: str,
                          max_files: int = 15, max_total: int = 120_000
                          ) -> Tuple[str, Dict[str, str]]:
    """Read the ACTUAL content of ``paths`` (PDF -> markdown via
    opendataloader when available, else ``doc_extract`` for office/pdf/
    text). Returns ``(block, cache)`` — ``block`` is the concatenated
    content for the prompt (bounded), ``cache`` maps path -> text for
    reuse. Never raises."""
    from cowork_local.core import doc_extract

    cache = dict(cache or {})
    parts, total = [], 0
    for p in paths[:max_files]:
        if total >= max_total:
            break
        text = cache.get(p)
        if text is None:
            try:
                if Path(p).suffix.lower() == ".pdf":
                    text = pdf_to_markdown(p, tmp_dir)
                    if not text:
                        text, _n = doc_extract.extract_text(p)
                else:
                    text, _n = doc_extract.extract_text(p)
            except Exception:  # noqa: BLE001
                text = ""
            cache[p] = text or ""
        text = cache.get(p) or ""
        if not text:
            continue
        chunk = text[: max(0, max_total - total)]
        total += len(chunk)
        parts.append(f'--- {Path(p).name} ({p}) ---\n{chunk}')
    return ("\n\n".join(parts), cache)


__all__ = ["pdf_to_markdown", "extract_file_contents"]
