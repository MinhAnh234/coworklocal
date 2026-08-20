"""Lift the hand-written audit sections out of 10-18.ui-audit.html.

That file was edited by hand: eight sections carry richer wireframes, prose and
interactive tables than the generator produces, plus the CSS and scripts they
need. Keeping two HTML files around means they drift, so this pulls the
hand-written parts into ``tools/audit_handwritten.py`` — a data module the
builder merges back in, making ``docs/ui-audit.html`` the single output again.

Two things are tokenised out before storing, so they stay generated rather than
frozen at extraction time:
  {{SHOT}}      the screenshot block (keeps ~8 MB of base64 out of the module)
  {{CONTROLS}}  the AST-derived control inventory (must track controls.json)

Workflow when you hand-edit one of those sections directly in the page:
    1. edit docs/ui-audit.html
    2. python tools/extract_handwritten.py     (reads it back into the module)
    3. python tools/build_audit_page.py        (regenerates, edits preserved)
Pass another filename to import sections from a different copy.
"""
from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
OUT = REPO / "tools" / "audit_handwritten.py"

# Hand-written sections are DETECTED, not listed: every section whose text
# differs from what the generator alone would emit is stored.
#
# There used to be a fixed list here, and it cost a section — "Monitoring ▸ Công
# cụ" was hand-written but missing from the list, so each rebuild quietly put
# the generated version back. Diffing against the live output cannot work (it
# already contains the merged result and would find nothing), so the reference
# is a generator-only render produced in-process, with the merge disabled.
#
# These are the ones known so far; anything else detected is added on top.
KNOWN = [
    "monitoring-sự-kiện-bảo-mật", "monitoring-lịch-sử-gọi-mcp",
    "monitoring-nhật-ký-hành-động", "monitoring-trạng-thái-agent",
    "monitoring-agents-admin", "monitoring-icon", "monitoring-công-cụ",
    "dialog-settings", "dialog-task-editor",
]

SECTION = re.compile(r'<section class="sec" id="([^"]+)">(.*?)</section>', re.S)
BODY = re.compile(r'(<div class="bd">.*)', re.S)
SHOT = re.compile(r'<div class="shot">.*?</div>', re.S)
CONTROLS = re.compile(r'<details class="ctl">.*?</details>', re.S)
STYLE = re.compile(r"<style>(.*?)</style>", re.S)
SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)


def bodies(html: str) -> dict[str, str]:
    """slug -> the section's <div class="bd"> … </div>, header excluded."""
    out = {}
    for m in SECTION.finditer(html):
        b = BODY.search(m.group(2))
        if b:
            out[m.group(1)] = b.group(1).strip()
    return out


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def main(argv: list[str]) -> int:
    src_path = DOCS / (argv[0] if argv else "ui-audit.html")
    if not src_path.exists():
        print(f"khong thay {src_path}")
        return 1

    src = src_path.read_text(encoding="utf-8")
    # Screenshots are re-embedded by the builder; keep the base64 out of here.
    hand = bodies(re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]+", "<IMG>", src))

    sys.path.insert(0, str(REPO / "tools"))
    import build_audit_page as B

    # Render what the generator ALONE would produce, into a temp file, and treat
    # every section that differs from it as hand-written.
    with tempfile.TemporaryDirectory() as tmp:
        keep_out, keep_hand = B.OUT, B.HAND_SECTIONS
        B.OUT, B.HAND_SECTIONS = Path(tmp) / "gen-only.html", {}
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                B.main()
            made = bodies(re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]+", "<IMG>",
                                 B.OUT.read_text(encoding="utf-8")))
        finally:
            B.OUT, B.HAND_SECTIONS = keep_out, keep_hand

    detected = sorted(s for s, body in hand.items() if norm(body) != norm(made.get(s, "")))
    slugs = [s for s in hand if s in set(detected) | set(KNOWN)]
    new = [s for s in detected if s not in KNOWN]
    gone = [s for s in KNOWN if s in hand and s not in detected]
    if new:
        print(f"phat hien them section viet tay: {new}")
    if gone:
        # Not an error: a hand section can be edited back to match the generator.
        print(f"section trong KNOWN nay giong ban sinh: {gone}")

    stored = {}
    for slug in slugs:
        body = hand[slug]
        body = SHOT.sub("{{SHOT}}", body, count=1)
        body = CONTROLS.sub("{{CONTROLS}}", body, count=1)
        stored[slug] = body

    # CSS rules and scripts the hand edits added. Compared against the builder's
    # OWN constants, not its output — the output already carries the merge.

    extra_css = "\n".join(
        ln for ln in STYLE.search(src).group(1).splitlines()
        if ln.strip() and ln not in B.CSS)
    # Scripts already sitting INSIDE a stored section travel with it — collecting
    # them again would bind every listener twice (the +/- steppers would then
    # count by two). Only page-level scripts belong in EXTRA_JS.
    gen_js = {norm(B.JS)}
    in_section = "".join(stored.values())
    extra_js = [j for j in SCRIPT.findall(src)
                if norm(j) not in gen_js and j not in in_section]

    parts = [
        '"""Hand-written audit sections, extracted from 10-18.ui-audit.html.\n\n'
        "GENERATED by tools/extract_handwritten.py — do not edit by hand; edit the\n"
        "source HTML and re-run it. build_audit_page.py substitutes {{SHOT}} and\n"
        '{{CONTROLS}} so those stay generated.\n"""\n',
        "SECTIONS = {",
    ]
    for slug, body in stored.items():
        parts.append(f"    {slug!r}: {body!r},")
    parts.append("}\n")
    parts.append(f"EXTRA_CSS = {extra_css!r}\n")
    parts.append("EXTRA_JS = [")
    for j in extra_js:
        parts.append(f"    {j!r},")
    parts.append("]\n")
    OUT.write_text("\n".join(parts), encoding="utf-8")

    print(f"section viet tay   : {len(stored)}")
    for slug, body in stored.items():
        print(f"   {slug:32} {len(body):>7,} ky tu"
              f"  shot={'{{SHOT}}' in body}  ctl={'{{CONTROLS}}' in body}")
    print(f"CSS them           : {len(extra_css.splitlines())} dong")
    print(f"script them        : {len(extra_js)}")
    print(f"ghi -> {OUT.relative_to(REPO)}  ({OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
