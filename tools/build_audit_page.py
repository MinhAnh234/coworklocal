"""Generate docs/ui-audit.html — the UI/UX audit page.

Reads docs/screens/manifest.json (produced by tools/capture_screens.py) and
emits one section per captured screen: the CURRENT screenshot on top, the
PROPOSED wireframe below, plus the problems found and what changes.

Driven by the manifest so a screen can never be silently dropped: anything in
the manifest without an entry in ANALYSIS still gets a section, flagged as
"chưa phân tích".

Run:  python tools/build_audit_page.py
"""
from __future__ import annotations

import base64
import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
MANIFEST = DOCS / "screens" / "manifest.json"
OUT = DOCS / "ui-audit.html"

# Eight sections were written by hand and are richer than anything this script
# produces. They live in a data module (rebuilt by tools/extract_handwritten.py)
# and are merged in below, so ui-audit.html stays the ONE output file instead of
# a generated file plus a hand-edited copy that drift apart.
try:
    from audit_handwritten import EXTRA_CSS as HAND_CSS
    from audit_handwritten import EXTRA_JS as HAND_JS
    from audit_handwritten import SECTIONS as HAND_SECTIONS
except ImportError:                                          # pragma: no cover
    sys.path.insert(0, str(REPO / "tools"))
    from audit_handwritten import EXTRA_CSS as HAND_CSS
    from audit_handwritten import EXTRA_JS as HAND_JS
    from audit_handwritten import SECTIONS as HAND_SECTIONS

# Screenshots are inlined as data: URIs so the page is ONE self-contained file —
# copy it anywhere and the images travel with it. `--external` opts out, leaving
# the images as `screens/*.png` next to a much smaller HTML.
STANDALONE = "--external" not in sys.argv

# --------------------------------------------------------------------------
# Per-screen analysis. `wf` is a wireframe of the PROPOSED layout, built from
# the tiny class vocabulary defined in CSS below (.r=row, .c=col, .b=box …).
# --------------------------------------------------------------------------

# Wireframes carry the SAME demo content as the screenshots above them, so the
# two can be compared like-for-like instead of "real app vs empty boxes".
#
# RECENTS is SCOPED TO THE ACTIVE PROJECT, matching today's behaviour: history is
# stored inside the project's own folder (config.py:590 → workspace_tab.py:453)
# and the sidebar groups threads per project (sidebar.py:193). A flat, global
# recents list would silently drop both — a regression, not a simplification.
RECENTS = ["📌 Gom số liệu doanh thu", "Dựng slide trình bày Q3"]


# Floating on every screen, pinned bottom-right — same corner as the app.
# The app spends 84×64px there: a 64px badge plus an 18px chevron beside it
# (help_agent_widget.py:34-37). That is a lot of permanent real estate for a
# thing you open a few times a day, so the proposal is one 26px dot. The label
# moves to hover/tooltip and to the panel header; nothing is removed.
DOCK_FAB = ('<div class="dock fab" title="AI Assistant — trợ lý cách dùng app">'
            '<span class="spark">✨</span></div>')
DOCK_BADGE = DOCK_FAB          # name kept: 16 screens already reference it


def rail(active: str = "", project: str = "Báo cáo tài chính Q3",
         *, empty: bool = False) -> str:
    """The proposed flat sidebar, with `active` highlighted.

    `empty=True` renders the no-project state. Running the app with zero
    projects shows Cowork and GraphRAG simply *gone* from the menu; here they
    stay put but dimmed, and the actions that need a project are disabled with
    a reason rather than vanishing.
    """
    items = ["Project", "Cowork", "Co4E", "Folder", "GraphRAG", "Schedule Task"]
    needs_project = {"Cowork", "GraphRAG"}
    rows = "".join(
        f'<div class="i{" on" if n == active else ""}'
        f'{" off" if empty and n in needs_project else ""}">{n}</div>'
        for n in items)
    if empty:
        return ('<div class="rail">'
                '<div class="menutog"><span>MENU</span><span class="chev">‹</span></div>'
                '<div class="rpick empty"><span>Chưa có project</span>'
                '<span class="cv">▾</span></div>'
                '<div class="newbtn off">+ Đoạn chat mới</div>'
                '<div class="hint">Tạo project trước</div>'
                f'{rows}'
                '<div class="sep"></div><div class="hd">RECENTS</div>'
                '<div class="i sm off">trống</div>'
                '<div class="grow"></div><div class="sep"></div>'
                '<div class="i">Dashboard</div><div class="i">Monitoring</div>'
                '<div class="i">Cài đặt</div>'
                '<div class="acct"><span>👤 local</span>'
                '<span class="lang">VN ▾</span><span class="thm">🌙</span></div></div>')
    recents = "".join(f'<div class="i sm">{t}</div>' for t in RECENTS)
    return (
        '<div class="rail">'
        # The app already collapses the rail to icons only (150px ↔ 54px,
        # app.py:409). Keep the control and keep it where it is.
        '<div class="menutog"><span>MENU</span><span class="chev">‹</span></div>'
        f'<div class="rpick"><span>📁 {project}</span><span class="cv">▾</span></div>'
        '<div class="newbtn">+ Đoạn chat mới</div>'
        f'{rows}'
        '<div class="sep"></div>'
        '<div class="hd">RECENTS</div>'
        f'<div class="scope">📁 {project}</div>'
        f'{recents}'
        '<div class="i sm allp">Tất cả project…</div>'
        '<div class="grow"></div>'
        '<div class="sep"></div>'
        '<div class="i">Dashboard</div><div class="i">Monitoring</div>'
        '<div class="i">Cài đặt</div>'
        '<div class="acct"><span>👤 local</span>'
        '<span class="lang">VN ▾</span><span class="thm">🌙</span></div>'
        '</div>')


def rail_collapsed() -> str:
    """The rail after the MENU button folds it to icons only (54px)."""
    icons = ["▣", "▤", "◫", "⌥", "◈", "▦"]
    rows = "".join(f'<div class="i ic{" on" if i == 1 else ""}">{g}</div>'
                   for i, g in enumerate(icons))
    return ('<div class="rail narrow">'
            '<div class="menutog"><span class="chev">›</span></div>'
            '<div class="newbtn ic">+</div>'
            f'{rows}<div class="grow"></div>'
            '<div class="i ic">◔</div><div class="i ic">◕</div>'
            '<div class="acct ic">👤</div></div>')


def projbar(name: str = "") -> str:
    """Deprecated: the project picker moved into the sidebar (see `rail`).

    It scopes ctx.active_project_id — global app state (state.py:60) — so a bar
    inside each screen's content area wrongly implied it was per-screen, and left
    it far from the "+ Đoạn chat mới" button it governs.
    """
    return ""


def grp(label: str, action: str = "", *, collapse: str = "") -> str:
    """A list-group heading, optionally with its own create/manage button.

    Putting "+" beside WORKFLOWS (and beside AGENTS) is what replaces the "＋"
    that used to live on the flow tab strip: removing the strip removed its
    button too, and the create action has to land somewhere explicit.
    """
    chev = {"left": "‹", "right": "›"}.get(collapse, "")
    tail = f'<span class="pchev">{chev}</span>' if chev else ""
    act = f'<span class="gact">{action}</span>' if action else ""
    return f'<div class="hd2 row">{label}<span class="ghd">{act}{tail}</span></div>'


def li(text: str, sub: str = "", *, on: bool = False) -> str:
    """One row in a list pane."""
    s = f'<span class="s">{sub}</span>' if sub else ""
    return f'<div class="li{" on" if on else ""}">{text}{s}</div>'


def card(title: str, meta: str) -> str:
    """One Kanban card."""
    return f'<div class="card">{title}<span class="s">{meta}</span></div>'


# --------------------------------------------------------------------------
# What each screen IS. `d` = one-paragraph purpose; `r` = the regions visible in
# the screenshot, left→right / top→bottom, so a reader can map the picture.
# --------------------------------------------------------------------------
DESCRIPTIONS: dict[str, dict] = {
    "dashboard": {"d": "Token đã tiêu và chi phí quy ra tiền, theo kỳ.",
        "r": [("Header", "kỳ · granularity · metric · tiền tệ"),
              ("6 thẻ", "Total · In · Out · Cache · Cost · Ngân sách"),
              ("Biểu đồ", "spline + đường so sánh kỳ trước"), ("Thói quen", "top task tốn token")]},
    "schedule-kanban": {"d": "Kanban các tác vụ hẹn giờ. Bộ lập lịch chạy nền dù màn này đóng.",
        "r": [("Lane", "một cột mỗi trạng thái"),
              ("Thẻ", "kéo đổi lane · double-click sửa · chuột phải: Chạy ngay / Lịch sử")]},
    "schedule-calendar": {"d": "Cùng dữ liệu Kanban, xếp theo ngày.",
        "r": [("Ô ngày", "nút + tạo task lúc 09:00 ngày đó")]},
    "workspace-project": {"d": "Khai báo project — đơn vị gom nhóm của app. Mỗi project có sandbox riêng "
        "và Instructions chèn vào mọi chat. Đây là <b>bộ chọn project duy nhất</b>.",
        "r": [("Trái", "danh sách project — chỉ hiện ở tab này"),
              ("Phải", "Tên · Mô tả · Instructions · thư mục")]},
    "workspace-cowork": {"d": "Chat với agent. Agent đọc/ghi tệp trong sandbox, chạy lệnh, gọi MCP.",
        "r": [("Lịch sử", "chat gom theo project; nhãn đậm = tên project, <b>chỉ là nhãn</b>"),
              ("Hội thoại", "bong bóng theo trục thời gian"), ("Files", "tệp đầu ra, gập được"),
              ("Composer", "Enter gửi · /skill · /agent"),
              ("Hàng dưới", "thư mục sandbox (chỗ thứ 2 lộ project) · model · Định tuyến · Tự chạy")]},
    "workspace-co4e": {"d": "Xưởng dựng workflow node-graph. Lưu toàn cục, không theo project.",
        "r": [("Sidebar", "3 tab icon: Workflows · Agents · Skills — kéo thả được"),
              ("Dải tab", "Flow Status ghim + mỗi workflow một tab"), ("Canvas", "node và cạnh"),
              ("Phải", "cấu hình bước đang chọn")]},
    "workspace-folder": {"d": "Duyệt tệp + nhờ AI sửa. AI <b>không ghi đè</b> — đề xuất diff, bấm Apply mới ghi.",
        "r": [("Cây trái", "hệ thống tệp thật"), ("Viewer", "code / HTML / PDF / ảnh / bảng tính"),
              ("Panel AI", "yêu cầu → plan → diff → Apply"), ("Terminal", "shell thật, không qua sandbox")]},
    "workspace-graphrag": {"d": "Đồ thị tri thức về cấu trúc mã/tài liệu + agent hỏi đáp trên đó.",
        "r": [("Đồ thị", "node theo loại, cạnh có nhãn quan hệ"), ("Phải", "hỏi đáp dựa trên đồ thị")]},
    "monitoring-tổng-quan": {"d": "Chi phí, tài nguyên máy, sandbox, nhật ký gần đây.",
        "r": [("Trái", "Token & chi phí · Hoạt động · Tài nguyên · Bảng giá model"),
              ("Phải", "Sandbox · Quyền · Audit log")]},
    "monitoring-sự-kiện-bảo-mật": {"d": "Nhật ký lần agent chạm thứ nhạy cảm: lệnh bị chặn, truy cập ngoài sandbox.",
        "r": [("Ô lọc", "có nút ✨ biến câu hỏi thành từ khoá")]},
    "monitoring-lịch-sử-gọi-mcp": {"d": "Mọi lần agent gọi MCP server ngoài.",
        "r": [("Bảng", "không có ô lọc như 2 màn log kia — khác biệt không chủ đích")]},
    "monitoring-nhật-ký-hành-động": {"d": "Nhật ký cấp ứng dụng: ai đổi cấu hình, ai chạy task.", "r": []},
    "monitoring-trạng-thái-agent": {"d": "Agent nào đang bật và nguồn định nghĩa.", "r": []},
    "monitoring-agents-admin": {"d": "Quản trị agent hệ thống. Cũng là nơi chọn model cho robot trợ giúp.",
        "r": [("Nút Kiểm tra", "probe provider thật")]},
    "monitoring-công-cụ": {"d": "Bật/tắt công cụ dựng sẵn và khai báo kết nối ngoài. "
        "Màn <b>duy nhất</b> còn hiện dải tab bên trong.",
        "r": [("Tool", "công cụ dựng sẵn + tự kiểm tra Internet"), ("Connector", "MCP · REST · MS365 · Jira")]},
    "monitoring-icon": {"d": "Thư viện icon, dùng lại khi đặt icon cho agent Co4E.", "r": []},
    "dialog-settings": {"d": "Thiết lập toàn app. Cuộn dọc, không mục lục.",
        "r": [("5 nhóm", "Ngôn ngữ · Provider · Bảo mật (khoá mật khẩu) · Tham số · Routing")]},
    "dialog-task-editor": {"d": "Khai báo tác vụ hẹn giờ: nội dung, lịch lặp, phụ thuộc, thông báo.",
        "r": [("5 nhóm", "Cơ bản · Lịch · Đầu vào · Phụ thuộc · Thực thi")]},
    "dialog-skills": {"d": "Quản lý skill — khối hướng dẫn tái dùng, gõ <code>/skill</code> để chèn.",
        "r": [("Ô tick", "chính là bật/tắt skill")]},
    "dialog-skill-edit": {"d": "Soạn skill: tên, mô tả, hướng dẫn.",
        "r": [("✨", "sinh hướng dẫn từ mô tả ngắn")]},
    "dialog-file-edit": {"d": "Xem và nhờ AI sửa tệp, mở từ panel Files trong chat.",
        "r": [("Tệp nhị phân", "trích văn bản, chỉ đọc"), ("Lưu", "tạo .bak trước khi ghi")]},
    "dialog-co4e-agent": {"d": "Định nghĩa agent Co4E: tính cách, quyền, model, skill.", "r": []},
    "dialog-ext-connector": {"d": "Khai báo kết nối ngoài, 2 chế độ.",
        "r": [("MCP (stdio)", "lệnh + tham số"), ("REST", "URL · key · header"), ("Test", "thử kết nối thật")]},
    "dialog-permission": {"d": "Chốt chặn cuối trước khi agent làm việc có hậu quả. "
        "Bật Tự chạy thì bỏ qua bước này.",
        "r": [("Xem trước", "lệnh sắp chạy hoặc diff sắp ghi")]},
    "dialog-agent-edit": {"d": "Soạn agent hệ thống: gắn vào chức năng nào, provider/model gì.", "r": []},
    "dialog-login": {"d": "Màn đăng nhập — <b>đã dựng xong nhưng không nơi nào gọi</b>. "
        "App khởi động thẳng với user \“local\”, quyền admin.",
        "r": [("3 trang", "Khởi tạo · Đăng nhập · Offline")]},
    "overlay-help-panel": {"d": "Trợ lý dùng app, nổi ở góc phải và có mặt trên mọi màn. "
        "Cố tình không có công cụ — chỉ hỏi đáp cách dùng.",
        "r": [("3 trạng thái", "tab mép phải → huy hiệu → panel 340×460, "
               "<b>luôn ghim góc dưới phải</b>"),
              ("3 nút", "<b>›</b> ẩn vào cạnh phải · <b>—</b> thu nhỏ về huy hiệu · "
               "tab mép để hiện lại"),
              ("Model", "chọn ở Monitoring ▸ Agents Admin, agent chức năng “help”")]},
}


ANALYSIS: dict[str, dict] = {
    "workspace-project": {
        "problems": [
            "<b>Pane trái đổi danh tính theo tab</b> (<code>workspace_tab.py:310-338</code>): "
            "Project → danh sách project, Cowork → History, còn lại → trống.",
            "History chỉ tới được từ tab Cowork.",
            "Bộ chọn project chỉ có ở tab Project.",
            "2/3 chiều cao dưới là khoảng trống chết.",
            "Header <i>“Workspace — Projects”</i> hiện ở <b>mọi</b> sub-tab.",
        ],
        "changes": [
            "History lên sidebar thành <b>RECENTS</b>, luôn thấy.",
            "Thanh chọn project ở đầu trang, dùng chung mọi màn.",
            "Pane trái cố định, không đổi danh tính.",
            "Header đổi theo màn.",
        ],
        "wf": rail("Project") + (
            '<div class="main">'
            + projbar() +
            '<div class="r tb"><div class="ttl">Quản lý project</div><div class="grow"></div>'
            '<div class="btn pri">+ Project mới</div></div>'
            '<div class="r grow">'
            '<div class="c w32 pane">'
            '<div class="hd2 row">PROJECT<span class="pchev">‹</span></div>'
            + li("Trạm sạc EV — Cổng vận hành", "6 đoạn chat · 4 task")
            + li("Báo cáo tài chính Q3", "2 đoạn chat · 3 task", on=True)
            + li("Cổng tra cứu tài liệu ISO", "1 đoạn chat · 1 task")
            + '<div class="grow"></div></div>'
            '<div class="c grow"><div class="lbl">Tên</div>'
            '<div class="inp">Báo cáo tài chính Q3</div>'
            '<div class="lbl">Mô tả</div>'
            '<div class="inp">Tự động gom số liệu từ Excel phòng ban, dựng bảng tổng hợp và slide.</div>'
            '<div class="lbl">Instructions</div>'
            '<div class="inp tall">Đơn vị tiền tệ mặc định VND. Làm tròn tới nghìn đồng.<br>'
            'Mọi con số phải truy được về file nguồn.</div>'
            '<div class="lbl">Thư mục làm việc</div>'
            '<div class="r tb"><div class="inp grow">…\\workspaces\\bao-cao-tai-chinh-q3</div>'
            '<div class="btn">Đổi</div><div class="btn">Mở</div></div>'
            '<div class="grow"></div>'
            '<div class="r tb end"><div class="btn pri">Lưu project</div></div>'
            '</div></div></div>'),
    },
    "workspace-cowork": {
        "problems": [
            "Hàng dưới composer nhồi 5 control + usage/cost + nút thư mục "
            "(<code>chat_panel.py:142-181</code>).",
            "Không có lối tắt “chat mới” — phải chọn project → mở nav → Cowork.",
            "<b>Màn duy nhất thấy được History.</b>",
            "Ba pane bóp vùng đọc hội thoại còn chưa tới 60% bề ngang.",
            "<b>Biết project nào, nhưng không đổi được.</b> Project hiện ở 2 chỗ (nhãn nhóm Lịch sử, "
            "nhãn thư mục đáy) — cả hai chỉ là nhãn. Đổi phải quay về tab Project "
            "(<code>workspace_tab.py:323</code>).",
        ],
        "changes": [
            "<b>Bộ chọn project lên sidebar</b> — nó là trạng thái toàn cục "
            "(<code>ctx.active_project_id</code>), không phải của riêng màn nào.",
            "<b>Bộ chọn project + nút “+ Đoạn chat mới” đặt cạnh nhau</b> ở đầu sidebar: "
            "chọn project rồi bấm, không rời màn. Nút cũ trên toolbar <b>giữ nguyên</b>.",
            "History lên sidebar, <b>vẫn gom theo project</b> + mục “Tất cả project…”.",
            "Usage/cost xuống thanh trạng thái; vùng gõ chỉ còn nhập · đính kèm · gửi.",
        ],
        "wf": rail("Cowork") + (
            '<div class="main">'
            + projbar() +
            '<div class="r tb"><div class="ttl">Gom số liệu doanh thu</div>'
            '<div class="s">qwen2.5-coder</div>'
            '<div class="grow"></div><div class="btn">Skills</div>'
            '<div class="btn">Cuộc trò chuyện mới</div></div>'
            # Files pane kept — the app has it, collapsible, and it is where
            # "Xem & sửa bằng AI" is reached from.
            '<div class="r grow"><div class="c grow chat">'
            '<div class="msg u">Có 6 file Excel trong thư mục input, gom lại thành 1 bảng '
            'tổng hợp giúp mình.</div>'
            '<div class="msg a">Đã đọc cả 6 file. Lưu ý: <b>PB_Marketing.xlsx</b> để cột “Doanh thu” '
            'ở cột F thay vì D và có 3 dòng trống ở cuối.<br><br>'
            'Mình đã chuẩn hoá và xuất <b>tonghop_q3.xlsx</b> — 1.284 dòng, tổng 42.7 tỷ VND.</div>'
            '<div class="grow"></div></div>'
            '<div class="c w22 pane"><div class="hd2 row">TỆP ĐẦU RA (3)'
            '<span class="pchev">›</span></div>'
            + li("tonghop_q3.xlsx") + li("BaoCao_Q3.pptx") + li("README.md")
            + '<div class="grow"></div></div></div>'
            '<div class="r tb"><div class="inp grow">Nhập yêu cầu…  (Enter để gửi)</div>'
            '<div class="btn">📎</div><div class="btn pri">Gửi</div></div>'
            '<div class="stat">Agent: qwen2.5-coder · Định tuyến: Tắt &nbsp;·&nbsp; '
            '↓292.8K ↑102.7K · $0.31 &nbsp;·&nbsp; 📁 bao-cao-tai-chinh-q3</div>'
            '</div>'),
    },
    "workspace-co4e": {
        "problems": [
            "<b>Bốn lớp điều hướng chồng nhau</b>: nav → tab icon sidebar → dải tab flow → panel phải.",
            "Dải tab flow lặp lại danh sách Workflows ngay bên trái.",
            "Panel cấu hình 11 trường dọc, phải cuộn.",
        ],
        "changes": [
            "Bỏ dải tab flow; chọn workflow từ danh sách trái.",
            "3 tab icon → 3 mục có nhãn cùng danh sách.",
            "Còn <b>2 lớp</b>: chọn trái → sửa phải.",
        ],
        "wf": rail("Co4E") + (
            '<div class="main">'
            + projbar() +
            '<div class="r tb"><div class="ttl">Quy trình phát triển tính năng</div>'
            '<div class="grow"></div><div class="btn">+ Bước</div><div class="btn">Auto ▾</div>'
            '<div class="btn pri">▷ Chạy</div></div>'
            '<div class="r grow">'
            '<div class="c w26 pane">'
            + grp("WORKFLOWS", "+ Mới", collapse="left")
            + li("Quy trình phát triển tính năng", "5 bước · đã lưu", on=True)
            + li("Rà soát bảo mật định kỳ", "2 bước · đã lưu")
            + li("Dựng báo cáo từ Excel", "3 bước · đã lưu")
            + grp("AGENTS (5)", "+ Mới")
            + li("Phân tích yêu cầu", "ANALYST") + li("Thiết kế giải pháp", "ARCHITECT")
            + li("Lập trình viên", "CODER") + li("Kiểm thử", "TESTER")
            + li("Soạn tài liệu", "WRITER")
            + grp("SKILLS (5)", "Quản lý…")
            + li("Rà soát bảo mật · Viết test trước · Chuẩn hoá Excel · …")
            + grp("LẦN CHẠY (6)")
            + li("✓ Quy trình phát triển", "5/5 · 08-08 15:32")
            + li("✕ Rà soát bảo mật", "3/5 · 08-06 16:32")
            + li("■ Dựng báo cáo từ Excel", "1/5 · 08-04 18:32")
            + '<div class="grow"></div>'
            '<div class="r tb"><div class="btn">✎</div><div class="btn">⧉</div>'
            '<div class="btn">🗑</div><div class="btn grow">▷ Chạy nền</div></div></div>'
            '<div class="c grow"><div class="b canvas grow">'
            '<div class="node ok">Phân tích yêu cầu</div><div class="arw">→</div>'
            '<div class="node ok">Thiết kế</div><div class="arw">→</div>'
            '<div class="node run">Lập trình viên</div><div class="arw">→</div>'
            '<div class="node">Kiểm thử</div></div></div>'
            '<div class="c w26 pane"><div class="hd2 row">CẤU HÌNH BƯỚC<span class="pchev">›</span></div>'
            '<div class="li">▾ Cơ bản<span class="s">Lập trình viên · CODER</span></div>'
            '<div class="inp">Hiện thực theo thiết kế. Viết test trước khi sửa logic nghiệp vụ.</div>'
            '<div class="li">▸ Model &amp; quyền<span class="s">qwen2.5-coder · full</span></div>'
            '<div class="li">▸ Skills &amp; tệp<span class="s">Viết test trước</span></div>'
            '<div class="li">▸ Agent song song<span class="s">chưa có</span></div>'
            '<div class="grow"></div></div>'
            '</div></div>'),
    },
    "workspace-folder": {
        "problems": [
            "<b>Năm vùng cùng lúc</b>: path · cây · viewer · panel AI · terminal.",
            "Hàng nút viewer trộn 5 chức năng khác loại.",
        ],
        "changes": [
            "Path bar gộp vào tiêu đề.",
            "Panel AI thành lớp phủ phải; terminal xuống đáy dạng thanh mỏng.",
        ],
        "wf": rail("Folder", "Trạm sạc EV — Cổng vận hành") + (
            '<div class="main">'
            + projbar("Trạm sạc EV — Cổng vận hành") +
            '<div class="r tb"><div class="ttl">Thư mục</div>'
            '<div class="s">…\\workspaces\\tram-sac-ev</div><div class="grow"></div>'
            '<div class="btn">Sửa</div><div class="btn">✨ AI</div><div class="btn pri">Lưu</div></div>'
            '<div class="r grow">'
            '<div class="c w26 pane">'
            + li("📁 src") + li("　📄 main.py") + li("　📁 billing")
            + li("　　📄 session.py", on=True) + li("📁 tests")
            + li("　📄 test_stations.py") + li("📄 README.md")
            + '<div class="grow"></div></div>'
            '<div class="c grow"><div class="b code grow">'
            '<span class="cm"># billing/session.py</span><br>'
            '<span class="kw">def</span> <span class="fn">close_session</span>(sid):<br>'
            '&nbsp;&nbsp;s = repo.get(sid)<br>'
            '&nbsp;&nbsp;s.ended_at = <span class="kw">None</span>'
            '  <span class="cm"># ← lỗi tính tiền</span><br>'
            '&nbsp;&nbsp;<span class="kw">return</span> bill(s)</div></div>'
            '<div class="c w28 pane ai"><div class="hd2 row">✨ AI SỬA TỆP<span class="pchev">›</span></div>'
            '<div class="msg u">Sửa lỗi tính dư tiền khi phiên bị ngắt đột ngột.</div>'
            '<div class="msg a">Lấy mốc heartbeat cuối làm <b>ended_at</b>.</div>'
            '<div class="diff"><span class="del">- s.ended_at = None</span><br>'
            '<span class="add">+ s.ended_at = last_heartbeat(sid)</span></div>'
            '<div class="grow"></div>'
            '<div class="r tb"><div class="btn">Bỏ</div><div class="btn pri">Áp dụng</div></div></div>'
            '</div><div class="stat">▸ Terminal — bật khi cần</div></div>'),
    },
    "workspace-graphrag": {
        "problems": [
            "Hai hàng toolbar riêng biệt — nên là một.",
            "Nút <b>Messages/Graph</b> đổi hẳn nội dung pane nhưng trông như nút thường.",
        ],
        "changes": [
            "Gộp hai hàng toolbar thành một.",
            "Messages/Graph thành cặp tab rõ ràng phía trên pane trái.",
        ],
        "wf": rail("GraphRAG", "Cổng tra cứu tài liệu ISO") + (
            '<div class="main">'
            + projbar("Cổng tra cứu tài liệu ISO") +
            '<div class="r tb"><div class="ttl">GraphRAG</div>'
            '<div class="inp grow">…\\workspaces\\cong-tra-cuu-iso</div>'
            '<div class="btn pri">Quét</div><div class="btn">Xuất PNG</div></div>'
            '<div class="r grow"><div class="c grow">'
            '<div class="r tb"><div class="tab on">Đồ thị</div><div class="tab">Tin nhắn</div>'
            '<div class="grow"></div><div class="s">1.902 node · 3.418 cạnh</div></div>'
            '<div class="b canvas grow">'
            '<div class="node ok">ISO 9001</div><div class="arw">→</div>'
            '<div class="node">Điều 7.5</div><div class="arw">→</div>'
            '<div class="node">Hồ sơ</div></div></div>'
            '<div class="c w28 pane"><div class="hd2 row">HỎI ĐÁP TRÊN ĐỒ THỊ<span class="pchev">›</span></div>'
            '<div class="msg u">Điều khoản nào nói về kiểm soát hồ sơ?</div>'
            '<div class="msg a">Điều <b>7.5.3</b> — Kiểm soát thông tin dạng văn bản. '
            'Có 12 tài liệu trùng số hiệu, xem <b>trung_lap.md</b>.</div>'
            '<div class="grow"></div>'
            '<div class="r tb"><div class="inp grow">Đặt câu hỏi…</div>'
            '<div class="btn pri">Hỏi</div></div></div></div></div>'),
    },
    "dashboard": {
        "problems": [
            "<b>Tám control trên một hàng</b> header.",
            "Trùng <b>Monitoring ▸ Tổng quan</b>: cùng StatCard + BudgetCard.",
            "Sáu thẻ số bằng nhau — không thấy đâu là chỉ số chính.",
        ],
        "changes": [
            "Header tách 2 hàng: thời gian / bộ lọc.",
            "Nâng <b>Chi phí</b> làm thẻ chính, 4 thẻ còn lại phụ.",
        ],
        "wf": rail() + (
            '<div class="main">'
            '<div class="r tb"><div class="ttl">Dashboard</div><div class="grow"></div>'
            '<div class="btn">◀</div><div class="btn">08/03 – 08/09</div><div class="btn">▶</div></div>'
            '<div class="r tb"><div class="btn">Theo tuần ▾</div><div class="btn">Chi phí ▾</div>'
            '<div class="btn">USD ▾</div><div class="grow"></div><div class="btn">⟳</div></div>'
            '<div class="r"><div class="b hero">$0.31<span class="s">Tổng chi phí · 57 lượt</span></div>'
            '<div class="c grow"><div class="r">'
            '<div class="b kpi">395.4K<span class="s">Tổng token</span></div>'
            '<div class="b kpi">292.8K<span class="s">Input</span></div></div>'
            '<div class="r"><div class="b kpi">102.7K<span class="s">Output</span></div>'
            '<div class="b kpi">108.9K<span class="s">Cache</span></div></div></div></div>'
            '<div class="b chart grow"><svg viewBox="0 0 400 90" preserveAspectRatio="none">'
            '<polyline points="0,20 60,55 120,45 180,38 240,18 300,52 400,78" '
            'fill="none" stroke="currentColor" stroke-width="2"/></svg></div>'
            '<div class="r"><div class="b grow">Tốn nhiều nhất: Dựng slide trình bày — 105.4K (26%)</div></div>'
            '</div>'),
    },
    "schedule-kanban": {
        "problems": [
            "<b>7 lane bị cắt ở mép phải</b> — lane <i>Paused</i> mất một nửa.",
            "Kéo-thả <b>có tác dụng thật</b>: thả vào <i>Running</i> là <b>chạy task ngay</b> "
            "(<code>schedule_task_tab.py:265</code>), không cảnh báo.",
            "Kanban/Calendar là combo, không phải tab.",
        ],
        "changes": [
            "Giữ <b>đủ 7 lane</b>, thu hẹp cho vừa một màn. Không gộp lane nào.",
            "Combo → cặp tab <b>Kanban | Lịch</b>.",
            "Lane <i>Running</i> có viền cảnh báo.",
        ],
        # All 7 STATUSES are shown — merging any of them into an "other" menu
        # would hide existing functionality, which this redesign must not do.
        "wf": rail("Schedule Task") + (
            '<div class="main">'
            '<div class="r tb"><div class="tab on">Kanban</div><div class="tab">Lịch</div>'
            '<div class="grow"></div><div class="btn pri">+ Task</div><div class="btn">✨ AI tạo</div></div>'
            '<div class="r grow k7">'
            f'<div class="c lane"><div class="hd2">BACKLOG (2)</div>'
            f'{card("[AI] Xuất DS khách hàng B2B", "Chưa đặt lịch")}'
            f'{card("Rà soát bảo mật trước release", "high")}'
            '<div class="grow"></div></div>'
            f'<div class="c lane"><div class="hd2">ĐÃ LÊN LỊCH (2)</div>'
            f'{card("Quét lại chỉ mục ISO", "08-11 14:32")}'
            f'{card("Báo cáo doanh thu 08:00", "08-09 14:32")}'
            '<div class="grow"></div></div>'
            f'<div class="c lane warn"><div class="hd2">ĐANG CHẠY (1) ⚠</div>'
            f'{card("Đồng bộ heartbeat trạm sạc", "08-08 · high")}'
            '<div class="grow"></div></div>'
            f'<div class="c lane"><div class="hd2">CHỜ DUYỆT (1)</div>'
            f'{card("Chờ kế toán duyệt số liệu T7", "Chưa đặt lịch")}'
            '<div class="grow"></div></div>'
            f'<div class="c lane"><div class="hd2">XONG (2)</div>'
            f'{card("Sao lưu CSDL hằng đêm", "08-07 · critical")}'
            f'{card("[AI] Slide tổng kết Q3", "Thành công")}'
            '<div class="grow"></div></div>'
            f'<div class="c lane"><div class="hd2">LỖI (1)</div>'
            f'{card("Kiểm tra chứng chỉ TLS", "critical · Lỗi")}'
            '<div class="grow"></div></div>'
            f'<div class="c lane"><div class="hd2">TẠM DỪNG (1)</div>'
            f'{card("Dọn log cũ hơn 90 ngày", "low")}'
            '<div class="grow"></div></div>'
            '</div>'
            '<div class="stat">Đủ <b>7 lane</b> theo <code>core.tasks.STATUSES</code> — '
            'không gộp, không giấu lane nào. Lane hẹp lại để vừa một màn, hết cuộn ngang.</div></div>'),
    },
    "monitoring-tổng-quan": {
        "problems": [
            "<b>Sáu group box, hai cột</b> — màn dày đặc nhất app.",
            "Trộn 3 mối quan tâm: chi phí · tài nguyên · bảo mật.",
            "Bảng giá model nhét chung hàng với thanh CPU/RAM.",
        ],
        "changes": [
            "Tách thành các mục có tiêu đề, cuộn dọc một cột chính.",
            "Bảng giá model tách ra thành mục riêng.",
        ],
        "wf": rail() + (
            '<div class="main"><div class="ttl">Monitoring</div>'
            '<div class="r tb"><div class="tab on">Tổng quan</div><div class="tab">Bảo mật</div>'
            '<div class="tab">MCP</div><div class="tab">Hành động</div><div class="tab">Agent</div>'
            '<div class="tab">Agents Admin</div><div class="tab">Công cụ</div><div class="tab">Icon</div></div>'
            '<div class="c grow">'
            '<div class="hd2">TOKEN &amp; CHI PHÍ</div>'
            '<div class="r"><div class="b kpi">395.4K<span class="s">Tổng token</span></div>'
            '<div class="b kpi">$0.31<span class="s">Chi phí</span></div>'
            '<div class="b kpi">57<span class="s">Lượt gọi</span></div>'
            '<div class="b kpi">—<span class="s">Ngân sách</span></div></div>'
            '<div class="hd2">TÀI NGUYÊN</div>'
            '<div class="r"><div class="b grow">CPU 34% · RAM 2.1/8 GB · Đĩa 41 GB trống</div></div>'
            '<div class="hd2">SANDBOX &amp; QUYỀN</div>'
            '<div class="r"><div class="b grow">Tệp: chỉ trong workspace · Mạng: chặn · '
            'Tiến trình: giới hạn 4</div></div>'
            '<div class="hd2 row">BẢNG GIÁ MODEL'
            '<span class="ghd"><span class="gact">Nhập · Xuất · Thêm · Tự dò</span>'
            '<span class="pchev">USD ▾</span></span></div>'
            '<div class="b tbl">'
            '<div class="tr th"><span>Model</span><span>Vào</span><span>Ra</span>'
            '<span>Cache</span><span>Đơn vị</span></div>'
            '<div class="tr"><span>qwen2.5-coder:7b</span><span>0.00</span><span>0.00</span>'
            '<span>0.00</span><span>/Mtok</span></div>'
            '<div class="tr"><span>gpt-4o-mini</span><span>0.15</span><span>0.60</span>'
            '<span>0.08</span><span>/Mtok</span></div></div>'
            '<div class="hd2 row">NHẬT KÝ GẦN ĐÂY'
            '<span class="ghd"><span class="gact">Xem tất cả</span></span></div>'
            '<div class="b grow"><span class="bad">✕ Chặn đọc personal.xlsx (ngoài sandbox)</span><br>'
            '<span class="ok">✓ pytest tests/test_stations.py → 4 passed</span><br>'
            '<span class="bad">✕ jira.create_issue — 401 token hết hạn</span></div>'
            '</div></div>'),
    },
    "monitoring-công-cụ": {
        "problems": [
            "Màn <b>duy nhất còn hiện dải tab</b> — 7 màn Monitoring kia bị ẩn. Không nhất quán.",
            "Tab <b>Tool</b>/<b>Connector</b> lọt thỏm trong một mục nav.",
            "Cấu hình kết nối tách khỏi Settings → thiết lập ở 2 nơi.",
        ],
        "changes": [
            "Bỏ ẩn dải tab cho toàn bộ Monitoring → 8 tab một hàng; Tool/Connector ngang hàng.",
        ],
        "wf": rail() + (
            '<div class="main"><div class="ttl">Monitoring</div>'
            '<div class="r tb"><div class="tab">Tổng quan</div><div class="tab">Bảo mật</div>'
            '<div class="tab">MCP</div><div class="tab">Hành động</div><div class="tab">Agent</div>'
            '<div class="tab">Agents Admin</div><div class="tab on">Công cụ</div>'
            '<div class="tab">Icon</div></div>'
            '<div class="r tb"><div class="tab on">Tool</div><div class="tab">Connector</div>'
            '<div class="grow"></div><div class="btn">Kiểm tra Internet</div></div>'
            '<div class="c grow pane">'
            + li("read_file", "Đọc tệp trong sandbox — ☑ bật")
            + li("write_file", "Ghi tệp trong sandbox — ☑ bật")
            + li("run_command", "Chạy lệnh shell — ☑ bật")
            + li("fetch_url", "Tải nội dung URL — ☑ bật · ✓ Internet OK")
            + li("image_gen", "Sinh ảnh — ☐ tắt")
            + '<div class="grow"></div></div></div>'),
    },
    "overlay-help-panel": {
        "problems": [
            "<b>Hai vùng bấm cho một tính năng.</b> Huy hiệu mở, chevron ẩn — nằm sát nhau, "
            "dễ bấm nhầm.",
            "<b>Vùng bấm quá nhỏ.</b> Chevron rộng <b>18px</b>, tab mép <b>16px</b> "
            "(<code>help_agent_widget.py:36-38</code>) — dưới ngưỡng ~24px để bấm thoải mái, "
            "nhất là trên màn cảm ứng.",
            "<b>Ba trạng thái, thừa một.</b> “Nép mép” và “huy hiệu” đều nghĩa là <i>đang đóng</i>; "
            "người dùng phải học hai kiểu đóng và hai đường quay lại.",
            "<b>Chiếm 84×64px vĩnh viễn</b> ngay góc dưới phải (huy hiệu 64 + khe 2 + "
            "chevron 18 — <code>help_agent_widget.py:34-37</code>) — ở màn Cowork nó nằm đè "
            "lên vùng nút Gửi, dù cả ngày chỉ mở vài lần.",
            "Huy hiệu dùng <b>chính icon app</b> (<code>help_agent_widget.py:49-53</code>, "
            "dự phòng là glyph robot) nên nhìn không khác gì icon cửa sổ; nhãn "
            "“Trợ lý App” / “App Assistant” / “アプリアシスタント” nói <i>chỗ dùng</i> "
            "chứ không nói <i>nó là gì</i>.",
        ],
        "changes": [
            "<b>Một chấm 26px, không chữ.</b> Bỏ luôn chevron rời — chỗ chiếm giảm từ "
            "<b>84×64 xuống 26×26</b> (<b>−88% diện tích</b>). Vẫn là một vùng bấm, "
            "26px ≥ ngưỡng bấm thoải mái.",
            "<b>Tên: “AI Assistant”</b> — giữ nguyên ở cả <b>3 ngôn ngữ</b>, sửa đúng một "
            "khoá <code>help_agent.title</code> (<code>i18n.py:470</code>) thay cho "
            "“App Assistant / Trợ lý App / アプリアシスタント”. Tên dài không còn là vấn đề "
            "vì nó không nằm trên màn lúc bình thường.",
            "<b>Chữ chỉ hiện khi rê chuột / focus bàn phím</b> — chấm nở thành pill "
            "“✨ AI Assistant”. Lúc bình thường màn hình không có chữ nào thừa.",
            "<b>“Ẩn trợ lý” dời vào menu ⋯</b> trong header panel, cạnh “Thu nhỏ”. "
            "Không mất chức năng — chỉ chuyển tới lúc người dùng <i>đang</i> tương tác.",
            "Thường ngày chỉ còn <b>2 trạng thái</b>: đóng ↔ mở. Ẩn hẳn thành lựa chọn hiếm.",
            "Tab mép nới từ <b>16px → 28px</b> cho bấm được.",
            "Ở màn có ô nhập dưới đáy (Cowork), chấm <b>nâng lên trên hàng nhập</b>, "
            "không đè nút Gửi.",
        ],
        "wf": ('<div class="main dlg">'
               '<div class="r tb"><div class="ttl">Trợ lý — thu gọn còn một chấm</div></div>'
               '<div class="r grow">'
               # 1. at rest — drawn to scale beside the old footprint
               '<div class="c w24"><div class="lbl">Bình thường</div>'
               '<div class="b grow ctr2" style="gap:14px">'
               '<div class="oldbox">cũ 84×64</div>'
               '<div class="fab"><span class="spark">✨</span></div></div>'
               '<div class="s">26×26 · không chữ, không chevron · −88% diện tích</div></div>'
               # 2. hover — the label appears only on demand
               '<div class="c w24"><div class="lbl">Rê chuột / focus</div>'
               '<div class="b grow ctr2">'
               '<span class="fabpill"><span class="fab"><span class="spark">✨</span></span>'
               'AI Assistant</span></div>'
               '<div class="s">tên chỉ hiện lúc cần</div></div>'
               # 3. open — hide lives in the ⋯ menu
               '<div class="c grow"><div class="lbl">Mở — “Ẩn” nằm trong menu ⋯</div>'
               '<div class="b grow pnl">'
               '<div class="r tb phdr"><span class="spark">✨</span><b>AI Assistant</b>'
               '<div class="grow"></div><span class="mut">— ⋯</span></div>'
               '<div class="mnu"><div class="mi">Thu nhỏ về chấm</div>'
               '<div class="mi">Ẩn trợ lý vào cạnh phải</div>'
               '<div class="mi">Đổi model…</div></div>'
               '<div class="msg a">Xin chào Nam, mình giúp gì khi bạn dùng app?</div>'
               '<div class="grow"></div>'
               '<div class="r tb"><div class="inp grow">Hỏi về cách dùng app…</div>'
               '<div class="btn pri">Gửi</div></div></div></div>'
               # 4. hidden — wider edge tab
               '<div class="c w18"><div class="lbl">Đã ẩn</div>'
               '<div class="b grow ctr2"><div class="edge wide">‹</div></div>'
               '<div class="s">tab mép 28px</div></div>'
               '</div></div>'),
    },
    "dialog-settings": {
        "problems": [
            "Năm group cuộn dọc, không mục lục.",
            "Sandbox khoá bằng <b>mật khẩu hard-code</b> (<code>settings_dialog.py:115</code>).",
            "Provider/Ngôn ngữ/Giao diện ở top bar, tách khỏi Settings.",
        ],
        "changes": [
            "Thêm cột mục lục bên trái; gom Provider/Ngôn ngữ/Giao diện vào đây.",
        ],
        "wf": ('<div class="main dlg"><div class="ttl">Cài đặt</div><div class="r grow">'
               '<div class="c w26 pane">'
               + li("Chung", "ngôn ngữ · giao diện · khay", on=True)
               + li("AI Provider", "Ollama · qwen2.5-coder")
               + li("Bảo mật sandbox", "🔒 cần mở khoá")
               + li("Tham số", "đính kèm · GraphRAG · tài nguyên")
               + li("Auto Model Routing", "đang Tắt")
               + '<div class="grow"></div></div>'
               '<div class="c grow"><div class="lbl">Ngôn ngữ hiển thị</div>'
               '<div class="inp">Tiếng Việt (VN)</div>'
               '<div class="lbl">Giao diện</div><div class="inp">Theo hệ thống</div>'
               '<div class="lbl">Nhà cung cấp AI</div><div class="inp">Ollama (local models)</div>'
               '<div class="lbl">Thu nhỏ xuống khay khi đóng</div><div class="inp">☑ Bật</div>'
               '<div class="grow"></div>'
               '<div class="r tb end"><div class="btn">Huỷ</div><div class="btn pri">Lưu</div></div>'
               '</div></div></div>'),
    },
    "dialog-task-editor": {
        "problems": [
            "<b>Năm group</b> dọc — form dài nhất app, không thấy đang ở bước nào.",
        ],
        "changes": ["Chia 3 bước có tab: <b>Nội dung → Lịch chạy → Liên kết</b>."],
        "wf": ('<div class="main dlg"><div class="ttl">Sửa task</div>'
               '<div class="r tb"><div class="tab on">① Nội dung</div>'
               '<div class="tab">② Lịch chạy</div><div class="tab">③ Liên kết</div></div>'
               '<div class="c grow"><div class="lbl">Tiêu đề</div>'
               '<div class="inp">Gửi báo cáo doanh thu hằng ngày 08:00</div>'
               '<div class="lbl">Mô tả</div>'
               '<div class="inp tall">Gom số liệu ngày hôm trước, dựng bảng và gửi email '
               'cho nhóm kế toán.</div>'
               '<div class="r"><div class="c grow"><div class="lbl">Project</div>'
               '<div class="inp">Báo cáo tài chính Q3</div></div>'
               '<div class="c grow"><div class="lbl">Chạy bằng</div>'
               '<div class="inp">Agent · qwen2.5-coder</div></div>'
               '<div class="c grow"><div class="lbl">Ưu tiên</div>'
               '<div class="inp">medium</div></div></div>'
               '<div class="grow"></div>'
               '<div class="r tb end"><div class="btn">Huỷ</div>'
               '<div class="btn pri">Lưu</div></div></div></div>'),
    },
}

# Screens with no bespoke analysis get this generic treatment.
GENERIC = {
    "problems": ["Bố cục hiện tại giữ nguyên; chưa phát hiện vấn đề sắp xếp nghiêm trọng."],
    "changes": ["Chỉ áp thanh menu phẳng mới; nội dung bên trong giữ nguyên."],
    "wf": "",
}

DEAD = [
    ("AccountsTab", "ui/accounts_tab.py:153", "Quản lý tài khoản/nhóm đầy đủ, nhưng không được gắn vào MonitoringTab."),
    ("LoginDialog", "ui/login_dialog.py:57", "Màn đăng nhập hoàn chỉnh; app.py:860 bỏ qua, hard-code user “local”."),
    ("FlowBuilderDialog", "ui/flow_dialog.py:34", "Bị Co4E thay thế; không nơi nào gọi."),
    ("AgentManagerTab", "ui/agent_manager_tab.py:28", "Chỉ dùng bởi FlowBuilderDialog → cũng không tới được."),
    ("SkillManagerTab", "ui/skill_manager_tab.py", "Chỉ dùng bởi FlowBuilderDialog → cũng không tới được."),
    ("McpServerEditDialog", "ui/mcp_servers_dialog.py:15", "Bị ExtConnectorEditDialog thay thế."),
]

FLOWS = [
    ("Khởi động → màn đầu",
     "python -m cowork_local → MainWindow → <b>Workspace ▸ Project</b><br><span class='mut'>Không có bước đăng nhập (LoginDialog bị bỏ qua)</span>",
     "Giữ nguyên đích đến. Sidebar phẳng nên Project là mục đầu, không còn nằm dưới nhánh Workspace."),
    ("Tạo project → chat",
     "Nav ▸ Workspace <i>(mở nhánh)</i> → Project → “+” → điền form → Lưu → <b>chọn project</b> → nav ▸ Cowork <i>(mục vừa mới xuất hiện)</i> → gõ",
     "Sidebar ▸ Project → “+” → Lưu → sidebar ▸ Cowork <i>(luôn nhìn thấy)</i> → gõ.<br><b>Bớt 1 bước mở nhánh</b>, và menu không đổi hình giữa chừng."),
    ("Co4E: tạo → chạy → xem run",
     "Nav ▸ Workspace ▸ Co4E → “＋” trên dải tab → kéo agent từ sidebar → chọn node → sửa ở panel phải → Lưu → Chạy → bấm tab <b>Flow Status</b> để xem",
     "Sidebar ▸ Co4E → “+ Workflow” trong danh sách trái → kéo → sửa phải → Lưu → Chạy.<br>Trạng thái run là <b>một mục trong danh sách trái</b>, không phải tab riêng."),
    ("Tạo &amp; chạy scheduled task",
     "Nav ▸ Schedule → “+ Task” → form 5 group → Lưu → <b>kéo thẻ vào lane Running</b> (chạy ngay, không hỏi)",
     "Sidebar ▸ Schedule Task → “+ Task” → form 3 tab → Lưu → kéo vào Running <i>(lane có viền cảnh báo)</i>."),
    ("Duyệt tệp → AI sửa",
     "Nav ▸ Workspace ▸ Folder → chọn tệp → bấm ✨ mở panel AI → gõ lệnh → xem plan → xem diff → <b>Apply</b>",
     "Sidebar ▸ Folder → chọn tệp → ✨ mở <b>lớp phủ AI</b> → gõ → plan → diff → Apply.<br>Luồng giữ nguyên; panel không còn chiếm chỗ cố định."),
]

# Which source files back each screen. A screen made of several widgets lists
# them all, so no control falls between two files.
SCREEN_FILES = {
    "dashboard": ["ui\\dashboard_tab.py", "ui\\widgets.py"],
    "schedule-kanban": ["ui\\schedule_task_tab.py"],
    "schedule-calendar": ["ui\\calendar_view.py"],
    "workspace-project": ["ui\\workspace_tab.py"],
    "workspace-cowork": ["ui\\cowork_tab.py", "ui\\chat_panel.py", "ui\\composer.py",
                         "ui\\sidebar.py", "ui\\chat_view.py", "ui\\routing_toggle.py"],
    "workspace-co4e": ["ui\\co4e_tab.py", "ui\\co4e_config_panel.py", "ui\\co4e_canvas.py"],
    "workspace-folder": ["ui\\folder_tab.py", "ui\\terminal_panel.py",
                         "ui\\libreoffice_view.py"],
    "workspace-graphrag": ["ui\\structure_graph_view.py"],
    "monitoring-tổng-quan": ["ui\\monitoring_tab.py"],
    "monitoring-agents-admin": ["ui\\agents_admin_tab.py"],
    "monitoring-công-cụ": ["ui\\tools_admin_tab.py", "ui\\connectors_panel.py"],
    "monitoring-icon": ["ui\\icons_admin_tab.py"],
    "dialog-settings": ["ui\\settings_dialog.py"],
    "dialog-task-editor": ["ui\\task_editor_dialog.py"],
    "dialog-skills": ["ui\\skills_dialog.py"],
    "dialog-file-edit": ["ui\\file_edit_dialog.py"],
    "dialog-co4e-agent": ["ui\\co4e_agent_dialog.py"],
    "dialog-ext-connector": ["ui\\ext_connector_dialog.py"],
    "dialog-permission": ["ui\\permission_dialog.py"],
    "dialog-login": ["ui\\login_dialog.py"],
    "overlay-help-panel": ["ui\\help_agent_widget.py"],
    # The shell is not a screen, but its controls are live and must be counted.
    "__shell__": ["app.py"],
}

# The ONLY controls that change place. Everything else stays where it is —
# keyed by the variable the AST found, so a rename breaks the link loudly.
MOVES = {
    "self._nav_toggle_btn": "Giữ — nút MENU gập sidebar (150↔54px)",
    "self.provider_combo": "→ menu tài khoản ở đáy sidebar",
    "self.language_combo": "→ menu tài khoản ở đáy sidebar",
    "self.theme_btn": "→ menu tài khoản ở đáy sidebar",
    "self.settings_btn": "→ menu tài khoản ở đáy sidebar",
    "self.project_list": "→ giữ ở màn Quản lý project + thêm thanh chọn đầu trang",
    "self.view_combo": "→ đổi thành cặp tab Kanban | Lịch",
    "self.flow_bar": "→ bỏ; chọn workflow từ danh sách trái",
    "self.flow_add_btn": "→ nút “+ Mới” cạnh tiêu đề WORKFLOWS "
                         "(chỗ cũ là dải tab, đã bỏ nên phải có chỗ mới)",
    "self.ag_new_btn": "→ nút “+ Mới” cạnh tiêu đề AGENTS",
    "self.sk_manage_btn": "→ nút “Quản lý…” cạnh tiêu đề SKILLS",
    "self._msg_btn": "→ đổi thành cặp tab Đồ thị | Tin nhắn",
    # The chevron beside the launcher is 18px wide and sits next to a 64px
    # badge; the action survives, it just moves to where the user already is.
    "self.collapse_btn": "→ mục “Ẩn trợ lý vào cạnh phải” trong menu ⋯ ở header panel",
    "self.edge_tab": "Giữ — tab mép mở lại trợ lý, nới 16px → 28px",
    "self.search_edit": "→ lên sidebar cùng RECENTS",
    "self.search_btn": "→ lên sidebar cùng RECENTS",
    "self.refresh_btn": "→ lên sidebar cùng RECENTS",
}

# One function traced end to end, because "does the new design match the old
# behaviour?" is only answerable at this level of detail.
NEWCHAT = [
    ("Số lối vào", "<b>1</b> — nút “Cuộc trò chuyện mới” trên toolbar Cowork "
     "(<code>cowork_tab.py:34</code>)",
     "<b>2</b> — nút sidebar + nút toolbar cũ giữ nguyên",
     "<span class='bad'>Tôi vẽ thêm nút sidebar mà chưa nói gì về nút cũ.</span> "
     "Giữ cả hai (bỏ nút cũ là xoá chức năng), cùng gọi một hàm."),
    ("Thấy được khi nào", "Chỉ khi đang ở tab Cowork — mà tab này "
     "<span class='bad'>tự ẩn khi chưa chọn project</span>",
     "Luôn thấy trên sidebar", "Mới dễ tới hơn. Chưa chọn project thì nút mờ đi."),
    ("Chat mới thuộc project nào", "Project đang mở, ngầm định — không hiển thị ở đâu",
     "Bộ chọn project <b>ngay trên nút</b>, trong sidebar",
     "<span class='ok'>Cùng hành vi</span> — vẫn là project đang mở "
     "(<code>ctx.active_project_id</code>), nhưng nay nhìn thấy và đổi được tại chỗ."),
    ("Đổi project trước khi tạo", "Phải rời Cowork → về tab Project → chọn dòng trong danh sách "
     "→ quay lại Cowork → bấm nút. <b>4 bước.</b>",
     "Bấm droplist ngay trên nút → chọn → bấm nút. <b>2 bước</b>, không rời màn.",
     "Ít bước hơn, không thêm chức năng — vẫn là chọn project rồi tạo chat."),
    ("Bấm từ màn khác", "Không xảy ra được — nút chỉ có trên Cowork",
     "Chuyển sang Cowork rồi tạo chat mới",
     "Hành vi mới, cần thiết vì nút giờ ở mọi màn."),
    ("Việc thực sự làm", "<code>new_session()</code> (<code>chat_panel.py:1653</code>): "
     "xoá messages · sinh session_id mới · dọn view, composer, plan, tệp vào/ra · "
     "<b>turn đang chạy vẫn chạy nền</b>",
     "Giữ y nguyên", "<span class='ok'>Không đổi.</span>"),
    ("Lưu chat cũ", "Tự lưu; History refresh qua <code>history_changed</code>",
     "Giữ y nguyên — RECENTS refresh", "<span class='ok'>Không đổi.</span>"),
]

# Surfaced by this audit, deliberately NOT done — each would add or change
# behaviour, which the redesign's scope forbids.
LATER = [
    ("Xuất log cho Nhật ký gần đây",
     "Hiện chỉ có “Xem tất cả” nhảy sang Action Logs (<code>monitoring_tab.py:586</code>). "
     "Xuất ra tệp là chức năng mới.",
     "chức năng mới"),
    ("Bỏ auto-refresh, thay bằng nút bấm",
     "Monitoring làm mới mỗi <b>3 giây</b> (<code>monitoring_tab.py:43</code>), "
     "Schedule <b>10 giây</b> (<code>schedule_task_tab.py:150</code>), "
     "Dashboard <b>30 giây</b> (<code>dashboard_tab.py:175</code>). "
     "Đề xuất: chỉ làm mới khi vào màn + một nút thủ công.",
     "đổi hành vi"),
    ("Nút tạo skill mới",
     "Cả <code>SkillsDialog</code> lẫn <code>SkillManagerTab</code> đều không có. "
     "Chỉ tạo được qua AI / template / nhập / nhân bản. "
     "<code>SkillEditDialog</code> đã làm được việc này, chỉ thiếu lối vào.",
     "chức năng mới"),
    ("Nút “chat mới” trong pane Lịch sử",
     "<code>sidebar.py:68</code> khai báo tín hiệu <code>new_chat</code>, "
     "<code>workspace_tab.py:241</code> đã nối — nhưng không nơi nào phát.",
     "hoàn thiện thứ đã dựng"),
    ("Gọi <code>ensure_starter_project()</code>",
     "Hàm có docstring “đảm bảo luôn có ít nhất một project” nhưng không ai gọi, "
     "trong khi <code>refresh()</code> lại ghi “no auto-seed”. Hai chỗ mâu thuẫn.",
     "đổi hành vi"),
    ("Mật khẩu Sandbox hard-code",
     "<code>settings_dialog.py:115</code> để mật khẩu mở khoá ngay trong mã nguồn.",
     "bảo mật"),
    ("Hai lớp trùng tên <code>CustomAgent</code>",
     "<code>core/custom_agents.py:23</code> và <code>core/co4e.py:117</code> — "
     "khác trường, khác thư mục lưu.",
     "dọn mã"),
    ("Sáu màn không có đường vào",
     "AccountsTab · LoginDialog · FlowBuilderDialog · AgentManagerTab · "
     "SkillManagerTab · McpServerEditDialog — tổng 64 control.",
     "quyết định giữ hay gỡ"),
]

# Old location → new location for EVERY screen, so "nothing was removed" is
# something the reader can check rather than take on trust.
MAPPING = [
    ("nhóm", "Màn hình làm việc", "", "", ""),
    ("", "Workspace ▸ Project", "Menu ▸ Workspace <i>(mở nhánh)</i> ▸ Project",
     "Sidebar ▸ <b>Project</b> — lên cấp 1, bớt 1 lần mở nhánh", "giữ nguyên"),
    ("", "Workspace ▸ Cowork", "Menu ▸ Workspace ▸ Cowork — <span class='bad'>biến mất nếu chưa chọn project</span>",
     "Sidebar ▸ <b>Cowork</b> — luôn thấy, mờ khi chưa chọn", "giữ nguyên"),
    ("", "Workspace ▸ Co4E", "Menu ▸ Workspace ▸ Co4E", "Sidebar ▸ <b>Co4E</b>", "giữ nguyên"),
    ("", "Workspace ▸ Folder <span class='mut'>(“Thư mục”)</span>",
     "Menu ▸ Workspace ▸ Thư mục", "Sidebar ▸ <b>Folder</b>", "giữ nguyên"),
    ("", "Workspace ▸ GraphRAG", "Menu ▸ Workspace ▸ GraphRAG — <span class='bad'>biến mất nếu chưa chọn project</span>",
     "Sidebar ▸ <b>GraphRAG</b> — luôn thấy", "giữ nguyên"),
    ("", "Schedule Task — Kanban", "Menu ▸ Schedule Task",
     "Sidebar ▸ <b>Schedule Task</b> ▸ tab <b>Kanban</b>", "giữ nguyên"),
    ("", "Schedule Task — Lịch", "Menu ▸ Schedule Task ▸ <i>combo</i> đổi sang “Lịch”",
     "Sidebar ▸ Schedule Task ▸ tab <b>Lịch</b> — combo thành tab, dễ thấy hơn", "giữ nguyên"),

    ("nhóm", "Giám sát &amp; vận hành <span class='mut'>— phần bạn hỏi</span>", "", "", ""),
    ("", "Dashboard", "Menu ▸ Dashboard <i>(cấp 1)</i>",
     "Sidebar ▸ <b>vùng đáy</b> — vẫn 1 cú nhấp", "giữ nguyên"),
    ("", "Monitoring ▸ Tổng quan", "Menu ▸ Monitoring <i>(mở nhánh)</i> ▸ Tổng quan",
     "Sidebar ▸ <b>Monitoring</b> ▸ tab <b>Tổng quan</b>", "giữ nguyên"),
    ("", "Monitoring ▸ Sự kiện bảo mật", "Menu ▸ Monitoring ▸ Sự kiện bảo mật",
     "Sidebar ▸ Monitoring ▸ tab <b>Sự kiện bảo mật</b>", "giữ nguyên"),
    ("", "Monitoring ▸ Lịch sử gọi MCP", "Menu ▸ Monitoring ▸ Lịch sử gọi MCP",
     "Sidebar ▸ Monitoring ▸ tab <b>Lịch sử gọi MCP</b>", "giữ nguyên"),
    ("", "Monitoring ▸ Nhật ký hành động", "Menu ▸ Monitoring ▸ Nhật ký hành động",
     "Sidebar ▸ Monitoring ▸ tab <b>Nhật ký hành động</b>", "giữ nguyên"),
    ("", "Monitoring ▸ Trạng thái Agent", "Menu ▸ Monitoring ▸ Trạng thái Agent",
     "Sidebar ▸ Monitoring ▸ tab <b>Trạng thái Agent</b>", "giữ nguyên"),
    ("", "Monitoring ▸ Agents Admin", "Menu ▸ Monitoring ▸ Agents Admin",
     "Sidebar ▸ Monitoring ▸ tab <b>Agents Admin</b>", "giữ nguyên"),
    ("", "Monitoring ▸ Công cụ", "Menu ▸ Monitoring ▸ Công cụ ▸ tab con Tool | Connector",
     "Sidebar ▸ Monitoring ▸ tab <b>Công cụ</b> ▸ Tool | Connector", "giữ nguyên"),
    ("", "Monitoring ▸ Icon", "Menu ▸ Monitoring ▸ Icon",
     "Sidebar ▸ Monitoring ▸ tab <b>Icon</b>", "giữ nguyên"),

    ("nhóm", "Thành phần bị dời chỗ", "", "", ""),
    ("", "History <span class='mut'>(lịch sử chat)</span>",
     "Pane giữa, <span class='bad'>chỉ ở tab Cowork</span>. Đã gom theo project.",
     "Sidebar ▸ <b>RECENTS</b> — <b>vẫn gom theo project</b> + “Tất cả project…”",
     "giữ, dễ tới hơn"),
    ("", "Bộ chọn project",
     "Pane trái, <span class='bad'>chỉ ở tab Project</span>",
     "Thanh chọn đầu trang, dùng chung mọi màn", "giữ, dễ tới hơn"),
    ("", "Provider · Ngôn ngữ · Giao diện", "Thanh trên cùng (topbar)",
     "Menu tài khoản ở đáy sidebar — gom cùng chỗ với Cài đặt", "giữ nguyên"),
    ("", "Nút Cài đặt", "Thanh trên cùng", "Menu tài khoản ở đáy sidebar", "giữ nguyên"),

    ("nhóm", "Hộp thoại &amp; lớp phủ", "", "", ""),
    ("", "11 hộp thoại", "Mở từ nút trên các màn tương ứng",
     "<b>Không đổi</b> — vẫn mở từ đúng những nút đó", "giữ nguyên"),
    ("", "Robot trợ giúp · Terminal · Composer", "Lớp phủ / panel thu gọn",
     "<b>Không đổi</b>", "giữ nguyên"),
]

# Every set of tabs / lanes / modes in the app, so nothing is hidden by a
# truncated wireframe. "Nhìn thấy" = does the strip appear on screen at all.
TAB_GROUPS = [
    ("Thanh menu trái", "4 mục", "Dashboard · Schedule Task · Workspace · Monitoring",
     "có", "<code>app.py:154</code>"),
    ("Workspace ▸ mục con", "5 mục",
     "Project · Cowork · Co4E · Folder · GraphRAG",
     "<b class='bad'>không</b> — <code>hide_tab_bar()</code>, và Cowork/GraphRAG "
     "còn tự ẩn khi chưa chọn project", "<code>workspace_tab.py:43</code>"),
    ("Monitoring ▸ mục con", "8 mục",
     "Tổng quan · Sự kiện bảo mật · Lịch sử gọi MCP · Nhật ký hành động · "
     "Trạng thái Agent · Agents Admin · Công cụ · Icon",
     "<b class='bad'>không</b> — <code>hide_tab_bar()</code>", "<code>monitoring_tab.py:215</code>"),
    ("Công cụ ▸ tab con", "2 tab", "Tool · Connector",
     "<b class='ok'>có</b> — màn <b>duy nhất</b> còn hiện dải tab", "<code>tools_admin_tab.py:91</code>"),
    ("Schedule ▸ chế độ xem", "2 chế độ", "Kanban · Lịch",
     "là <b>combo</b>, không phải tab", "<code>schedule_task_tab.py:171</code>"),
    ("Kanban ▸ lane trạng thái", "<b>7 lane</b>",
     "backlog · scheduled · running · waiting_input · done · failed · paused",
     "<b class='bad'>cắt ở mép phải</b>, phải cuộn ngang", "<code>tasks.py:24</code>"),
    ("Co4E ▸ sidebar", "3 tab icon", "Workflows · Agents · Skills",
     "chỉ có icon, tên nằm trong tooltip", "<code>co4e_tab.py:426</code>"),
    ("Co4E ▸ dải tab flow", "1 + N", "Flow Status (ghim) + mỗi workflow đang mở một tab",
     "có, kiểu trình duyệt", "<code>co4e_tab.py:556</code>"),
    ("Folder ▸ trình xem", "5 trang", "trống · mã nguồn · HTML · tài liệu · ảnh (+ bảng tính)",
     "tự đổi theo đuôi tệp, không có tab", "<code>folder_tab.py:322</code>"),
    ("GraphRAG ▸ khung trái", "2 trang", "Đồ thị · Tin nhắn",
     "là <b>nút bấm</b>, không phải tab", "<code>structure_graph_view.py:217</code>"),
    ("Dialog Tạo task bằng AI", "2 tab", "Sinh bằng AI · Nhập từ Excel",
     "có", "<code>schedule_task_tab.py:530</code>"),
    ("Dialog Kết nối ngoài", "2 chế độ", "MCP (stdio) · REST API",
     "là combo đổi trang", "<code>ext_connector_dialog.py:23</code>"),
    ("Dialog Đăng nhập <span class='mut'>(màn chết)</span>", "3 trang",
     "Khởi tạo lần đầu · Đăng nhập · Dự phòng offline",
     "<span class='mut'>không tới được</span>", "<code>login_dialog.py:74</code>"),
    ("Dialog Flow Builder <span class='mut'>(màn chết)</span>", "3 tab",
     "Flow · Agents · Skills", "<span class='mut'>không tới được</span>",
     "<code>flow_dialog.py:247</code>"),
]

# Every collapse / expand affordance the app ships. The redesign must keep all
# of them — folding a panel away is a feature users rely on, and dropping one
# would be removing functionality, not simplifying.
COLLAPSIBLES = [
    ("Thanh menu chính", "MENU ‹ ở đầu thanh — gập còn dải icon (150px → 54px)",
     "<code>app.py:409</code>", "giữ"),
    ("Pane Project", "chevron ‹ trên đầu danh sách project",
     "<code>workspace_tab.py:368</code>", "giữ"),
    ("Pane Lịch sử", "chevron trên đầu History, gập thành dải mỏng",
     "<code>sidebar.py:167</code> · <code>workspace_tab.py:247</code>", "giữ"),
    ("Pane Tệp trong chat", "chevron › — gập panel Files bên phải khung chat",
     "<code>chat_panel.py:709</code>", "giữ"),
    ("Panel Hỏi đáp GraphRAG", "chevron › — gập panel agent bên phải đồ thị",
     "<code>structure_graph_view.py:615</code>", "giữ"),
    ("Panel cấu hình bước Co4E", "nút gập panel phải của canvas",
     "<code>co4e_tab.py:767</code>", "giữ"),
    ("Panel Tin nhắn Co4E", "gập khung log dưới canvas — <b>mặc định đang gập</b>",
     "<code>co4e_tab.py:894</code>", "giữ"),
    ("Terminal trong Thư mục", "bấm thanh tiêu đề để mở/gập — <b>mặc định đang gập</b>",
     "<code>terminal_panel.py:156</code>", "giữ"),
    ("Panel AI sửa tệp", "nút ✨ bật/tắt panel — <b>mặc định đang ẩn</b>",
     "<code>folder_tab.py:777</code>", "giữ"),
    ("Đồ thị ⇄ Tin nhắn (GraphRAG)", "nút đổi nội dung pane trái",
     "<code>structure_graph_view.py:416</code>", "giữ — đổi thành cặp tab"),
    ("Khối kết quả công cụ trong chat", "bấm tiêu đề để mở/gập output dài",
     "<code>chat_view.py:253</code>", "giữ"),
]

NAV_BEFORE = """Dashboard
Schedule Task
Workspace  ▼          ← nhánh accordion, tab strip bên trong BỊ ẨN
   Project
   Cowork             ← TỰ ẨN khi chưa chọn project
   Co4E
   Folder
   GraphRAG           ← TỰ ẨN khi chưa chọn project
Monitoring ▼          ← nhánh accordion, tab strip BỊ ẨN
   Tổng quan
   Sự kiện bảo mật
   Lịch sử gọi MCP
   Nhật ký hành động
   Trạng thái Agent
   Agents Admin
   Công cụ
   Icon"""

NAV_AFTER = """[ + Đoạn chat mới ]     ← hành động chính, trên cùng
──────────────
Project                 ← màn đầu, giữ nguyên
Cowork                  ← luôn hiện (mờ đi nếu chưa chọn project)
Co4E
Folder
GraphRAG                ← luôn hiện (mờ đi nếu chưa chọn project)
Schedule Task
──────────────
RECENTS                 ← History dời từ pane giữa lên đây
  · thread gần nhất…
──────────────  (ghim đáy — nhóm phụ trợ)
Dashboard               ← vẫn 1 cú nhấp như cũ
Monitoring              ← BỎ ẨN dải tab, đủ 8 mục nằm ngang trong trang:
   [Tổng quan] [Sự kiện bảo mật] [Lịch sử gọi MCP]
   [Nhật ký hành động] [Trạng thái Agent]
   [Agents Admin] [Công cụ] [Icon]
👤 local · Provider ▾   ← gom Provider/Language/Theme/Settings"""

NAV_PROBLEMS = [
    ("Accordion 2 cấp, không phẳng",
     "<code>app.py:170</code> ghi là \“Claude-style\” nhưng là <code>QTreeWidget</code> "
     "accordion. Claude dùng danh sách phẳng."),
    ("Mục tự biến mất",
     "<code>workspace_tab.py:485</code> ẩn <b>Cowork</b> và <b>GraphRAG</b> khi chưa chọn project."),
    ("Tab strip bị ẩn",
     "<code>hide_tab_bar()</code> ẩn dải tab có sẵn → menu là đường duy nhất."),
    ("History chỉ có ở tab Cowork",
     "<code>workspace_tab.py:169</code>. <span class='ok'>Điểm làm tốt phải giữ:</span> lịch sử "
     "<b>đã gom theo project</b> — lưu trong <code>&lt;project&gt;/.cowork_history</code> "
     "(<code>config.py:590</code>), hiển thị gom nhóm ở <code>sidebar.py:193</code>."),
    ("Monitoring gom 5 việc rời rạc",
     "Chi phí · log bảo mật · quản trị agent · cấu hình tool · thư viện icon."),
    ("Dashboard trùng Monitoring ▸ Tổng quan", "Cùng bộ <code>StatCard</code> + <code>BudgetCard</code>."),
    ("Top bar giữ thiết lập", "Provider/Ngôn ngữ/Giao diện ở topbar, tách khỏi Cài đặt."),
    ("Header không đổi theo màn", "Mọi sub-tab đều hiện <i>\“Workspace — Projects\”</i>."),
    ("<span class='bad'>LỖI: bấm mục con Workspace, menu nhảy về mục cha</span>",
     "<code>_goto</code> gọi <code>refresh()</code> (<code>app.py:726</code>) → "
     "<code>subtabs_changed</code> vô điều kiện (<code>workspace_tab.py:497</code>) → "
     "<code>takeChildren()</code> (<code>app.py:691</code>) huỷ mục vừa bấm.<br>"
     "<b>Đo được:</b> 5/5 mục Workspace mất highlight, 0/8 mục Monitoring bị."),
]

CSS = """
:root{--bg:#FFFFFF;--sf:#F8F8F8;--rz:#FFFFFF;--bd:#E5E5E5;--bds:#CECECE;--tx:#3B3B3B;--mut:#616161;--fnt:#6E6E6E;--ac:#005FB8;--nav:#F8F8F8;--navb:#E5E5E5;--navs:#E4E6F1;--ok:#317A2D;--warn:#8F6500;--bad:#CD3131;--r:4px}
@media(prefers-color-scheme:dark){:root{--bg:#1F1F1F;--sf:#252526;--rz:#313131;--bd:#2B2B2B;--bds:#3C3C3C;--tx:#CCCCCC;--mut:#9D9D9D;--fnt:#9A9A9A;--ac:#4DAAFC;--nav:#181818;--navb:#2B2B2B;--navs:#04395E;--ok:#89D185;--warn:#CCA700;--bad:#F76464;--r:4px}}
:root[data-theme=dark]{--bg:#1F1F1F;--sf:#252526;--rz:#313131;--bd:#2B2B2B;--bds:#3C3C3C;--tx:#CCCCCC;--mut:#9D9D9D;--fnt:#9A9A9A;--ac:#4DAAFC;--nav:#181818;--navb:#2B2B2B;--navs:#04395E;--ok:#89D185;--warn:#CCA700;--bad:#F76464;--r:4px}
:root[data-theme=light]{--bg:#FFFFFF;--sf:#F8F8F8;--rz:#FFFFFF;--bd:#E5E5E5;--bds:#CECECE;--tx:#3B3B3B;--mut:#616161;--fnt:#6E6E6E;--ac:#005FB8;--nav:#F8F8F8;--navb:#E5E5E5;--navs:#E4E6F1;--ok:#317A2D;--warn:#8F6500;--bad:#CD3131;--r:4px}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);
font:14px/1.55 "Segoe UI Variable Text","Segoe UI",system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px 64px}
header{padding:34px 0 16px;border-bottom:1px solid var(--bd);margin-bottom:20px}
h1{font-size:25px;margin:0 0 8px;letter-spacing:-.02em}
h2{font-size:19px;margin:38px 0 6px;padding-top:16px;border-top:1px solid var(--bd)}
h3{font-size:15px;margin:20px 0 6px}
p{margin:8px 0}.mut{color:var(--mut)}.fnt{color:var(--fnt)}
code{font:13px "Cascadia Code",Consolas,monospace;background:var(--sf);
border:1px solid var(--bd);border-radius:4px;padding:1px 5px}
.note{background:var(--sf);border:1px solid var(--bd);border-left:3px solid var(--ac);
border-radius:var(--r);padding:9px 13px;margin:10px 0;font-size:13px}
.note.warn{border-left-color:var(--warn)}.note.bad{border-left-color:var(--bad)}
.toc{background:var(--sf);border:1px solid var(--bd);border-radius:var(--r);padding:18px 22px}
.toc ol{margin:6px 0;padding-left:22px;columns:2;column-gap:36px}
.toc a{color:var(--tx);text-decoration:none}.toc a:hover{color:var(--ac);text-decoration:underline}
.sec{border:1px solid var(--bd);border-radius:var(--r);margin:16px 0;overflow:hidden;background:var(--sf)}
.sec>.hd{padding:10px 16px;border-bottom:1px solid var(--bd);display:flex;
align-items:baseline;gap:10px;flex-wrap:wrap}
.sec>.hd b{font-size:15px}.sec>.bd{padding:14px 16px}
.tag{font-size:12px;padding:2px 8px;border-radius:4px;background:var(--bg);
border:1px solid var(--bd);color:var(--mut)}
.cap{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
color:var(--fnt);margin:12px 0 5px}
.shot{border:1px solid var(--bd);border-radius:var(--r);overflow:hidden;background:var(--bg)}
.shot img{display:block;width:100%;height:auto}
.miss{padding:26px;text-align:center;color:var(--bad);background:var(--bg);
border:1px dashed var(--bad);border-radius:var(--r);font-size:14px}
ul.pr{margin:4px 0;padding-left:18px;font-size:13px}ul.pr li{margin:3px 0}
.lead{font-size:14px;color:var(--tx);margin:0 0 6px;max-width:92ch}
p.rg{font-size:12.5px;color:var(--mut);margin:6px 0 0;line-height:1.55}
p.rg b{color:var(--tx)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.cols.pc{gap:16px;margin-top:10px}.cols.pc .cap{margin:0 0 4px}
details.ctl{margin-top:12px;border:1px solid var(--bd);border-radius:var(--r);
background:var(--bg)}
details.ctl summary{padding:7px 12px;cursor:pointer;font-size:12.5px;color:var(--tx)}
details.ctl[open] summary{border-bottom:1px solid var(--bd)}
details.ctl table{margin:0;font-size:12px}
details.ctl td,details.ctl th{padding:4px 10px}
td.mv{color:var(--ac)}
@media(max-width:900px){.cols{grid-template-columns:1fr}.toc ol{columns:1}}
pre.tree{background:var(--bg);border:1px solid var(--bd);border-radius:var(--r);
padding:16px;font:12.5px/1.65 "Cascadia Code",Consolas,monospace;overflow-x:auto;margin:0}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--bd);vertical-align:top}
th{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.05em}
/* ---- wireframe vocabulary ---- */
.wf{display:flex;height:570px;border:1px solid var(--bds);border-radius:var(--r);
overflow:hidden;background:var(--bg);font-size:11px;position:relative}
/* The rail must never crop: its bottom group is real navigation. */
.wf .rail{overflow:visible}
.wf .rail{width:150px;flex:none;background:var(--nav);border-right:1px solid var(--navb);
padding:8px;display:flex;flex-direction:column;gap:3px}
.wf .newbtn{background:var(--ac);color:#fff;border-radius:4px;padding:6px;text-align:center;
font-weight:600}
/* flex:none — inside the column rail this otherwise collapses to a sliver. */
.wf .rpick{flex:none;background:var(--rz);border:1px solid var(--bds);border-radius:4px;
padding:5px 7px;margin-bottom:5px;font-weight:600;display:flex;align-items:center;
justify-content:space-between;gap:4px;line-height:1.3}
.wf .rpick>span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.wf .rpick .cv{color:var(--mut);font-weight:400;flex:none}
.wf .rpick.empty{color:var(--fnt);font-weight:400;font-style:italic}
.wf .i.off,.wf .newbtn.off{opacity:.45}
.wf .newbtn.off{background:var(--bds);color:var(--tx)}
.wf .hint{font-size:9px;color:var(--fnt);text-align:center;padding:2px 0 6px;font-style:italic}
.wf .newbtn{flex:none}
.wf .i{padding:5px 7px;border-radius:4px;color:var(--tx)}
.wf .i.on{background:var(--navs);border-left:2px solid var(--ac);font-weight:600}
.wf .i.sm{color:var(--mut);font-size:10px;padding:3px 7px}
.wf .hd{font-size:9px;letter-spacing:.1em;color:var(--fnt);padding:4px 7px;font-weight:700}
.wf .scope{font-size:10px;font-weight:600;color:var(--tx);padding:2px 7px 4px}
.wf .i.allp{color:var(--ac);font-style:italic}
.wf .sep{height:1px;background:var(--navb);margin:5px 0}
.wf .acct{margin-top:6px;padding:6px 7px;border-top:1px solid var(--navb);
color:var(--mut);font-size:10px;display:flex;align-items:center;gap:5px}
.wf .acct .lang{margin-left:auto;background:var(--rz);border:1px solid var(--bds);
border-radius:3px;padding:1px 5px;color:var(--tx);font-weight:600}
.wf .acct .thm{font-size:11px}
.wf .main,.wf .c{display:flex;flex-direction:column;gap:6px;padding:10px;flex:1;min-width:0}
.wf .main.dlg{border:none}
.wf .ttl{font-weight:700;font-size:13px;white-space:nowrap}
/* Rows STRETCH by default so nested columns fill the height — `.tb` opts a
   toolbar row back into vertical centring. Getting this backwards is what
   collapsed every wireframe into a thin strip floating mid-panel. */
.wf .r{display:flex;gap:6px;align-items:stretch;min-height:0}
.wf .r.tb{align-items:center;flex:none}
.wf .r.end{justify-content:flex-end}
.wf .grow{flex:1;min-height:0}
.wf .b{background:var(--sf);border:1px solid var(--bd);border-radius:4px;padding:6px 8px;min-height:22px}
.wf .b.tall{min-height:70px}
/* nowrap: a wrapped node graph reads as a broken diagram, not a flow */
.wf .b.canvas{display:flex;align-items:center;justify-content:center;gap:5px;
background:var(--rz);flex-wrap:nowrap;padding:12px;overflow:hidden}
.wf .b.code{background:var(--rz);font-family:"Cascadia Code",Consolas,monospace;
font-size:10px;line-height:1.7;overflow:hidden}
.wf .b.chart{background:var(--rz);padding:8px;color:var(--ac);min-height:70px}
.wf .b.chart svg{width:100%;height:100%;display:block}
.wf .b.hero,.wf .b.kpi{display:flex;flex-direction:column;justify-content:center;
font-weight:700}
.wf .b.hero{flex:none;width:130px;font-size:20px;align-items:center;text-align:center}
.wf .b.kpi{flex:1;font-size:14px}
.wf .s{display:block;font-size:9.5px;font-weight:400;color:var(--fnt);margin-top:2px}
.wf .lbl{color:var(--mut);font-size:10px}
.wf .hd2{font-size:9px;letter-spacing:.09em;color:var(--fnt);font-weight:700;
margin-top:2px}
.wf .hd2.row{display:flex;align-items:center;justify-content:space-between}
.wf .pchev{color:var(--mut);font-size:12px;font-weight:400}
.wf .ghd{display:flex;align-items:center;gap:6px}
.wf .gact{color:var(--ac);font-weight:600;font-size:9.5px;letter-spacing:0}
.wf .b.tbl{padding:0;overflow:hidden}
.wf .tr{display:flex;padding:3px 8px;border-bottom:1px solid var(--bd);gap:6px}
.wf .tr:last-child{border-bottom:none}
.wf .tr span{flex:1}.wf .tr span:first-child{flex:2.4}
.wf .tr.th{color:var(--fnt);font-size:9px;letter-spacing:.05em;font-weight:700}
.wf .ctr2{display:flex;align-items:center;justify-content:center}
.wf .edge{background:var(--sf);border:1px solid var(--bds);border-right:none;
border-radius:5px 0 0 5px;padding:14px 5px;color:var(--mut)}
.wf .edge.wide{padding:14px 10px;font-weight:700;color:var(--tx)}
.wf .mnu{align-self:flex-end;background:var(--rz);border:1px solid var(--bds);
border-radius:5px;padding:3px;min-width:52%;box-shadow:0 3px 10px rgba(16,32,64,.14)}
.wf .mi{padding:4px 8px;border-radius:3px}
.wf .mi:nth-child(2){background:var(--navs);font-weight:600}
/* Sparkle badge — the teal-tinted "AI" chip, same convention as the app's
   existing ✨ AI buttons in Folder and Schedule. */
/* The dock is anchored to the window corner — its position is unchanged. */
.wf .main.anchor{position:relative}
.wf .dock{position:absolute;right:10px;bottom:10px}
.wf .dock.badgewrap{display:flex;align-items:center;gap:3px}
.wf .dock .badge,.wf .dock.badge{background:#E6F6F4;border:1px solid #7FD0C4;
border-radius:6px;padding:7px 11px;font-weight:700;color:#0F6E62;white-space:nowrap}
/* "Ẩn vào cạnh phải" — a real button in the app, next to the launcher. */
.wf .dock .chv{background:var(--sf);border:1px solid var(--bds);border-radius:4px;
padding:6px 3px;color:var(--mut);font-size:11px;line-height:1}
/* The proposed dot: 26px, no label, no neighbouring chevron. Drawn at the same
   scale as the wireframe around it so the size claim is visible, not asserted. */
.wf .dock.fab,.wf .fab{width:26px;height:26px;border-radius:50%;background:#E6F6F4;
border:1px solid #7FD0C4;display:flex;align-items:center;justify-content:center;
font-size:12px;box-shadow:0 2px 6px rgba(16,32,64,.14)}
/* Hover / keyboard focus only — the label is never on screen at rest. */
.wf .fabpill{display:inline-flex;align-items:center;gap:5px;background:#E6F6F4;
border:1px solid #7FD0C4;border-radius:13px;padding:4px 11px 4px 5px;
font-weight:700;color:#0F6E62;white-space:nowrap;box-shadow:0 2px 6px rgba(16,32,64,.14)}
.wf .fabpill .fab{box-shadow:none;width:18px;height:18px;font-size:10px}
/* Old vs new footprint, drawn to scale beside each other. */
.wf .oldbox{width:42px;height:32px;border:1px dashed var(--bds);border-radius:4px;
display:flex;align-items:center;justify-content:center;color:var(--fnt);font-size:9px}
.wf .dock.pnl{width:74%;height:76%;background:var(--sf);border:1px solid var(--bds);
border-radius:6px;box-shadow:0 3px 10px rgba(16,32,64,.13)}
.wf .phdr{border-bottom:1px solid var(--bd);padding-bottom:5px;gap:5px}
.wf .spark{color:#0F9B8A}
.wf .pnl{display:flex;flex-direction:column;gap:5px;padding:8px}
/* The rail's own MENU collapse control (150px <-> 54px in the app). */
.wf .menutog{display:flex;align-items:center;justify-content:space-between;
color:var(--fnt);font-size:9px;letter-spacing:.1em;font-weight:700;padding:2px 6px 6px}
.wf .menutog .chev{font-size:13px;font-weight:400}
.wf .rail.narrow{width:46px;align-items:center}
.wf .rail.narrow .menutog{justify-content:center;padding:2px 0 6px}
.wf .newbtn.ic,.wf .i.ic,.wf .acct.ic{text-align:center;padding:5px 0;width:100%}
.wf .acct.ic{border-top:1px solid var(--navb)}
.wf .w22{flex:none;width:22%}
.wf .inp{background:var(--rz);border:1px solid var(--bds);border-radius:4px;
padding:6px 8px;color:var(--tx);min-height:26px;overflow:hidden}
.wf .inp.tall{min-height:52px}
.wf .btn{background:var(--rz);border:1px solid var(--bds);border-radius:4px;
padding:4px 9px;white-space:nowrap;align-self:center}
.wf .btn.pri{background:var(--ac);color:#fff;border-color:transparent;font-weight:600}
.wf .tab{padding:4px 10px;border-bottom:2px solid transparent;color:var(--mut);white-space:nowrap}
.wf .tab.on{border-bottom-color:var(--ac);color:var(--tx);font-weight:600}
.wf .stat{border-top:1px solid var(--bd);padding-top:5px;color:var(--fnt);
font-size:10px;flex:none}
/* Shared project picker — same spot on every project-scoped screen. */
.wf .r.pb{border-bottom:1px solid var(--bd);padding-bottom:7px;margin-bottom:2px}
.wf .pick{background:var(--navs);border:1px solid var(--navb);border-radius:4px;
padding:4px 10px;font-weight:600;color:var(--tx)}
.wf .pane{background:var(--sf);border:1px solid var(--bd);border-radius:4px;gap:3px}
.wf .lane{background:var(--sf);border:1px solid var(--bd);border-radius:4px;padding:6px;gap:5px}
.wf .lane.warn{border-color:var(--warn)}
/* 7 lanes must fit without horizontal scrolling — that is the whole point. */
.wf .k7{gap:4px}
.wf .k7 .lane{padding:5px;gap:4px;min-width:0}
.wf .k7 .card{font-size:10px;padding:4px 6px}
.wf .k7 .hd2{font-size:8.5px}
.tag.ok{color:var(--ok);border-color:var(--ok)}
b.ok,span.ok{color:var(--ok)}b.bad,span.bad{color:var(--bad)}
td.ok{color:var(--ok);white-space:nowrap}
tr.grp td{background:var(--sf);font-weight:700;font-size:13px;
border-bottom:1px solid var(--bds);padding-top:14px}
.wf .li{padding:4px 7px;border-radius:4px;color:var(--tx);line-height:1.35}
.wf .li.on{background:var(--navs);font-weight:600}
.wf .card{background:var(--rz);border:1px solid var(--bd);border-radius:4px;
padding:5px 7px;line-height:1.35}
.wf .chat{gap:6px;padding:0}
.wf .msg{border-radius:5px;padding:6px 9px;line-height:1.45;max-width:88%}
.wf .msg.u{background:var(--navs);align-self:flex-end}
.wf .msg.a{background:var(--sf);border:1px solid var(--bd)}
.wf .node{background:var(--sf);border:1px solid var(--bds);border-radius:4px;
padding:6px 8px;white-space:nowrap;font-size:10px;flex:none}
.wf .node.ok{border-color:var(--ok);color:var(--ok)}
.wf .node.run{border-color:var(--ac);color:var(--ac);font-weight:600}
.wf .arw{color:var(--fnt)}
.wf .diff{font-family:"Cascadia Code",Consolas,monospace;font-size:9.5px;
line-height:1.7;background:var(--rz);border-radius:4px;padding:5px 7px}
.wf .add{color:var(--ok)}.wf .del{color:var(--bad)}
.wf .ok{color:var(--ok)}.wf .bad{color:var(--bad)}
.wf .cm{color:var(--fnt)}.wf .kw{color:var(--ac)}.wf .fn{color:var(--warn)}
.wf .w18{flex:none;width:18%}.wf .w24{flex:none;width:24%}
.wf .w26{flex:none;width:26%}.wf .w28{flex:none;width:28%}.wf .w32{flex:none;width:32%}
@media(max-width:760px){.wf{height:auto;flex-direction:column}.wf .rail{width:auto}}
.tgl{position:fixed;top:16px;right:16px;z-index:9;background:var(--sf);color:var(--tx);
border:1px solid var(--bds);border-radius:var(--r);padding:7px 13px;cursor:pointer;font-size:13px}
.sw{display:inline-flex;border:1px solid var(--bds);border-radius:4px;overflow:hidden;margin-left:auto}
.sw button{background:var(--bg);color:var(--mut);border:0;padding:3px 11px;cursor:pointer;font-size:12px}
.sw button.on{background:var(--ac);color:#fff;font-weight:600}
"""

JS = """
const root=document.documentElement;
function setTheme(t){root.setAttribute('data-theme',t);
 document.getElementById('tgl').textContent=t==='dark'?'☀ Sáng':'🌙 Tối';
 document.querySelectorAll('.sec').forEach(s=>swap(s,t));}
function swap(sec,t){const i=sec.querySelector('img.shotimg');if(!i)return;
 const src=t==='dark'?i.dataset.dark:i.dataset.light;if(src)i.src=src;
 sec.querySelectorAll('.sw button').forEach(b=>b.classList.toggle('on',b.dataset.t===t));}
document.getElementById('tgl').onclick=()=>setTheme(
 root.getAttribute('data-theme')==='dark'?'light':'dark');
document.querySelectorAll('.sw button').forEach(b=>b.onclick=()=>{
 swap(b.closest('.sec'),b.dataset.t);});
setTheme(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
"""


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_controls() -> dict:
    """file path -> {controls, menu_actions}, from tools/extract_controls.py."""
    src = DOCS / "screens" / "controls.json"
    if not src.exists():
        return {}
    return {f["file"]: f for f in json.loads(src.read_text(encoding="utf-8"))}


def controls_table(slug: str, index: dict) -> str:
    """A collapsed, exhaustive control list for one screen."""
    files = SCREEN_FILES.get(slug)
    if not files:
        return ""
    rows, n = [], 0
    for fname in files:
        rec = index.get(fname)
        if not rec:
            continue
        short = fname.split("\\\\")[-1]
        for c in rec["controls"]:
            label = c.get("label_vi") or c.get("label") or "—"
            label = label.replace("tr(", "").strip("'\")")[:60]
            act = "; ".join(h.split(" → ")[-1] for h in c["signals"])[:70] or "—"
            dest = MOVES.get(c["var"], "giữ nguyên tại chỗ")
            cls = "ok" if dest.startswith("giữ") else "mv"
            rows.append(f'<tr><td>{esc(label)}</td><td class="mut">{c["kind"]}</td>'
                        f'<td><code>{esc(act)}</code></td>'
                        f'<td class="mut">{short}:{c["line"]}</td>'
                        f'<td class="{cls}">{dest}</td></tr>')
            n += 1
        for a in rec["menu_actions"]:
            label = a.get("label_vi") or a.get("label") or "—"
            label = label.replace("tr(", "").strip("'\")")[:60]
            rows.append(f'<tr><td>{esc(label)}</td><td class="mut">menu chuột phải</td>'
                        f'<td class="mut">—</td>'
                        f'<td class="mut">{short}:{a["line"]}</td>'
                        f'<td class="ok">giữ nguyên tại chỗ</td></tr>')
            n += 1
    if not rows:
        return ""
    return (f'<details class="ctl"><summary>Kiểm kê control — <b>{n}</b> mục '
            f'<span class="mut">(trích bằng AST, không đọc tay)</span></summary>'
            f'<table><tr><th>Nhãn</th><th>Loại</th><th>Hàm xử lý</th><th>Nguồn</th>'
            f'<th>Sau khi sửa</th></tr>{"".join(rows)}</table></details>')


def embed(rel: str) -> str:
    """PNG at `rel` as a data: URI (standalone builds only)."""
    raw = (DOCS / rel.split("?")[0]).read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def bust(rel: str) -> str:
    """Append a content stamp to an image URL.

    Re-capturing overwrites the PNGs but keeps their names, so a browser (or the
    editor's HTML preview) happily serves the previous render from cache and the
    page looks stale even though it was just rebuilt. Stamping the URL with the
    file's mtime forces a fetch whenever the picture actually changed.
    """
    path = DOCS / rel
    try:
        return f"{rel}?v={int(path.stat().st_mtime)}"
    except OSError:
        return rel


def main() -> int:
    stamp = datetime.now().strftime("%H:%M %d/%m/%Y")
    cidx = load_controls()
    recs = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_slug: dict[str, dict] = {}
    for r in recs:
        by_slug.setdefault(r["slug"], {"title": r["title"], "note": r["note"], "shots": {}})
        by_slug[r["slug"]]["shots"][r["theme"]] = r
    order = list(by_slug)

    toc = "".join(
        f'<li><a href="#{s}">{esc(by_slug[s]["title"])}</a></li>' for s in order)

    secs = []
    for n, slug in enumerate(order, 1):
        info = by_slug[slug]
        a = ANALYSIS.get(slug, GENERIC)
        dark, light = info["shots"].get("dark"), info["shots"].get("light")

        if dark and dark["file"]:
            src = embed if STANDALONE else bust
            d_url, l_url = src(dark["file"]), src((light or dark)["file"])
            shot = (f'<div class="shot"><img class="shotimg" src="{d_url}" '
                    f'data-dark="{d_url}" data-light="{l_url}" '
                    f'alt="{esc(info["title"])}"></div>')
            sw = ('<span class="sw"><button data-t="dark" class="on">Tối</button>'
                  '<button data-t="light">Sáng</button></span>')
        else:
            err = esc((dark or {}).get("error", "không rõ"))
            shot = f'<div class="miss">Không chụp được màn này<br><code>{err}</code></div>'
            sw = ""

        # The dock floats over the MAIN WINDOW. Modal dialogs cover it, so they
        # get none; section 27 draws its own (badge + open panel).
        dock = "" if (slug.startswith("dialog-")
                      or slug == "overlay-help-panel") else DOCK_BADGE
        wf = (f'<div class="cap">Đề xuất — bố cục mới</div>'
              f'<div class="wf">{a["wf"]}{dock}</div>'
              if a["wf"] else
              '<div class="cap">Đề xuất — bố cục mới</div>'
              '<p class="mut">Giữ nguyên bố cục bên trong; chỉ đổi thanh menu sang danh sách phẳng.</p>')

        # What the screen is, plus a legend for the regions visible in the shot.
        de = DESCRIPTIONS.get(slug)
        intro = f'<p class="lead">{de["d"]}</p>' if de else ""
        legend = ""
        if de and de.get("r"):
            bits = " · ".join(
                f'<b>{lab}</b>{": " + txt if txt else ""}' for lab, txt in de["r"])
            legend = f'<p class="rg">{bits}</p>'

        # Eight sections were written by hand (tools/audit_handwritten.py). Use
        # that markup verbatim, but keep the screenshot and the AST control
        # inventory generated so neither goes stale.
        hand = HAND_SECTIONS.get(slug)
        if hand:
            body = (hand.replace("{{SHOT}}", shot)
                        .replace("{{CONTROLS}}", controls_table(slug, cidx)))
        else:
            body = f"""<div class="bd">
{intro}
<div class="cap">Hiện tại</div>{shot}
{legend}
{wf}
{controls_table(slug, cidx)}
<div class="cols pc">
<div><div class="cap">Vấn đề</div><ul class="pr">{''.join(f'<li>{p}</li>' for p in a['problems'])}</ul></div>
<div><div class="cap">Thay đổi</div><ul class="pr">{''.join(f'<li>{c}</li>' for c in a['changes'])}</ul></div>
</div></div>"""

        secs.append(f"""<section class="sec" id="{slug}">
<div class="hd"><b>{n}. {esc(info['title'])}</b><span class="tag">{esc(info['note'])}</span>{sw}</div>
{body}</section>""")

    flows = "".join(
        f'<tr><td><b>{t}</b></td><td class="mut">{b}</td><td>{af}</td></tr>'
        for t, b, af in FLOWS)
    navp = "".join(f'<tr><td><b>{t}</b></td><td>{d}</td></tr>' for t, d in NAV_PROBLEMS)
    tabs = "".join(
        f'<tr><td><b>{g}</b></td><td class="mut">{n}</td><td>{items}</td>'
        f'<td>{seen}</td><td class="mut">{src}</td></tr>'
        for g, n, items, seen, src in TAB_GROUPS)
    newchat = "".join(
        f'<tr><td><b>{a}</b></td><td class="mut">{o}</td><td>{n}</td><td>{v}</td></tr>'
        for a, o, n, v in NEWCHAT)
    later = "".join(f'<tr><td><b>{n}</b></td><td>{d}</td>'
                    f'<td class="mut">{k}</td></tr>' for n, d, k in LATER)
    rail_has = rail("Cowork") + ('<div class="main"><div class="ttl">Cowork</div>'
                                 '<div class="b grow"></div></div>')
    rail_none = rail("Project", empty=True) + (
        '<div class="main"><div class="ttl">Quản lý project</div>'
        '<div class="b grow"><span class="mut">Chưa có project — bấm “+ Project mới”</span>'
        '</div></div>')
    shell_ctl = controls_table("__shell__", cidx)
    colls = "".join(
        f'<tr><td><b>{n}</b></td><td>{how}</td><td class="mut">{src}</td>'
        f'<td class="ok">{keep}</td></tr>' for n, how, src, keep in COLLAPSIBLES)
    rail_open = rail("Cowork") + ('<div class="main"><div class="ttl">Nội dung</div>'
                                  '<div class="b grow"></div></div>')
    rail_shut = rail_collapsed() + ('<div class="main"><div class="ttl">Nội dung</div>'
                                    '<div class="b grow"></div></div>')
    mapping = "".join(
        (f'<tr class="grp"><td colspan="4">{name}</td></tr>' if kind == "nhóm"
         else f'<tr><td><b>{name}</b></td><td class="mut">{old}</td><td>{new}</td>'
              f'<td class="ok">{keep}</td></tr>')
        for kind, name, old, new, keep in MAPPING)
    dead = "".join(f'<tr><td><b>{n}</b></td><td><code>{f}</code></td><td class="mut">{d}</td></tr>'
                   for n, f, d in DEAD)

    html = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CoworkLocal — Audit UI/UX</title><style>{CSS}
{HAND_CSS}</style></head><body>
<button class="tgl" id="tgl">🌙 Tối</button>
<div class="wrap">
<header>
<h1>CoworkLocal — Audit UI/UX</h1>
<p class="mut">Hiện trạng {len(order)} màn hình · đề xuất sắp xếp lại theo UI/UX kiểu Claude ·
bảng màu Visual Studio Code · <b>dựng lúc {stamp}</b></p>
<div class="note warn"><b>Ràng buộc:</b> chỉ sắp xếp lại, <b>không xoá/thêm chức năng</b>.
Hai chỗ lệch được đánh dấu ở Phần 1.</div>
<div class="note"><b>Ảnh chụp:</b> render offscreen trên <b>bản sao</b> dữ liệu
(scheduler tắt, hash dữ liệu thật trước/sau giống hệt). Nạp dữ liệu mẫu: 3 project ·
6 chat · 10 task · 3 workflow · 45 ngày token. Ảnh đã chỉnh menu sáng đúng mục —
xem <b>lỗi #9</b>.</div>
</header>

<div class="toc"><b>Mục lục</b>
<p class="mut" style="margin:4px 0 8px">Phần 1 — Điều hướng · Phần 2 — Luồng người dùng ·
Phần 3 — {len(order)} màn hình · Phần 4 — Màn chết</p>
<ol>{toc}</ol></div>

<h2>Phần 1 — Điều hướng</h2>
<div class="cols">
<div><div class="cap">Hiện tại</div><pre class="tree">{esc(NAV_BEFORE)}</pre></div>
<div><div class="cap">Đề xuất</div><pre class="tree">{esc(NAV_AFTER)}</pre></div>
</div>
<h3>Chín điểm đã xác minh trong code</h3>
<table><tr><th style="width:32%">Vấn đề</th><th>Chi tiết</th></tr>{navp}</table>

<h3>Khung ứng dụng — thanh trên cùng &amp; thanh menu</h3>
<p class="mut">Không thuộc màn nào nên liệt kê riêng.</p>
{shell_ctl}

<h3>Các nút thu gọn / mở rộng — giữ nguyên toàn bộ</h3>
<p class="mut">App có <b>11 chỗ</b> gập được. Thiết kế mới giữ đủ cả 11.</p>
<div class="cols" style="align-items:start">
<div><div class="cap">Menu mở rộng</div><div class="wf demo" style="height:570px">{rail_open}</div></div>
<div><div class="cap">Menu đã gập (54px, chỉ còn icon)</div>
<div class="wf demo" style="height:570px">{rail_shut}</div></div>
</div>
<table><tr><th style="width:24%">Chỗ gập được</th><th style="width:40%">Cách dùng</th>
<th>Nguồn</th><th>Thiết kế mới</th></tr>{colls}</table>

<h3>Từng màn hình đi đâu sau khi sửa</h3>
<p class="mut">Không màn nào bị bỏ. Giám sát (Dashboard + 8 màn Monitoring) ở nhóm
phụ trợ đáy sidebar, mở ra thấy đủ 8 tab.</p>
<table><tr><th style="width:17%">Màn hình</th><th style="width:30%">Hiện tại ở đâu</th>
<th style="width:35%">Sau khi sửa ở đâu</th><th>Chức năng</th></tr>{mapping}</table>
<div class="note">Dashboard/Monitoring xuống đáy nhưng vẫn là mục cấp 1, vẫn
<b>một cú nhấp</b>. Sidebar chia theo tần suất: việc hằng ngày ở trên, quản trị ở dưới.</div>

<h3>Toàn bộ nhóm tab / lane / chế độ trong app</h3>
<p class="mut">Đầy đủ, kể cả nhóm không hiện ra màn hình.</p>
<table><tr><th style="width:20%">Nhóm</th><th>SL</th><th style="width:36%">Các mục</th>
<th style="width:22%">Nhìn thấy?</th><th>Nguồn</th></tr>{tabs}</table>
<div class="note warn"><b>14 nhóm</b> tab/lane, chỉ <b>4 nhóm</b> hiện ra màn hình.
Số còn lại bị ẩn, thành combo, thành nút, hoặc không tới được.</div>
<div class="note bad"><b>Hai chỗ lệch — cần bạn quyết:</b>
(1) Cowork/GraphRAG: <i>biến mất</i> → <b>hiện nhưng mờ</b>.
(2) Bỏ ẩn tab strip Monitoring (khôi phục thứ đã có).</div>

<h2>Phần 2 — Luồng người dùng</h2>
<table><tr><th style="width:20%">Luồng</th><th style="width:40%">Hiện tại</th><th>Sau khi sửa</th></tr>{flows}</table>

<h3>Truy vết chi tiết: “Đoạn chat mới”</h3>
<table><tr><th style="width:16%">Khía cạnh</th><th style="width:28%">Giao diện cũ</th>
<th style="width:24%">Giao diện mới</th><th>Có đồng bộ không</th></tr>{newchat}</table>
<div class="cols" style="align-items:start">
<div><div class="cap">Có project</div><div class="wf demo">{rail_has}</div></div>
<div><div class="cap">Chưa có project nào</div><div class="wf demo">{rail_none}</div></div>
</div>
<div class="note"><b>Khi chưa có project</b> (đã chạy thử app với 0 project):
hiện nay <b>Cowork và GraphRAG biến mất</b> khỏi menu nên không chat được, mà không nói vì sao.
Thiết kế mới <b>giữ nguyên cổng chặn đó</b> — vẫn không tạo chat được — nhưng hai mục vẫn nằm
đúng chỗ, chỉ mờ đi; droplist ghi “Chưa có project”; nút chat mới bị khoá kèm lý do
“Tạo project trước”.<br>
<span class="mut">Ghi nhận thêm: lúc đó <code>ctx.active_project_id</code> vẫn giữ
<code>'default'</code> — trỏ vào một project không tồn tại. Và
<code>projects.ensure_starter_project()</code> (“đảm bảo luôn có ít nhất một project”)
<b>không nơi nào gọi</b>.</span></div>

<div class="note bad"><b>Phát hiện:</b> <code>sidebar.py:68</code> khai báo tín hiệu
<code>new_chat</code> và <code>workspace_tab.py:241</code> đã nối nó vào
<code>_on_sidebar_new</code> — nhưng <b>không nơi nào phát tín hiệu này</b>
(<code>grep new_chat.emit</code> → rỗng). Tức pane Lịch sử vốn được thiết kế để có nút
“chat mới” nhưng nút đó chưa bao giờ được thêm. Đề xuất đưa nút lên sidebar chính là
<b>hoàn thiện ý định sẵn có</b> trong code, không phải thêm mới.</div>

<h2>Phần 3 — Từng màn hình</h2>
{''.join(secs)}

<h2>Phần 4 — Phát triển lần sau</h2>
<p class="mut">Những việc audit này phát hiện nhưng <b>cố ý không làm</b>, vì đều thêm
hoặc đổi chức năng — ngoài phạm vi “chỉ sắp xếp lại”.</p>
<table><tr><th style="width:26%">Việc</th><th>Chi tiết</th><th style="width:16%">Loại</th></tr>
{later}</table>

<h2>Phần 5 — Màn chết (chỉ ghi nhận)</h2>
<p class="mut">Sáu màn có trong code nhưng không tới được — tổng <b>64 control</b>
(accounts 18 · flow_dialog 28 · agent_manager 7 · skill_manager 7 · mcp_servers 4).
Không nằm trong kiểm kê phía trên vì không có đường nào tới; chỉ ghi nhận, không đề xuất gỡ.</p>
<table><tr><th>Thành phần</th><th>Vị trí</th><th>Tình trạng</th></tr>{dead}</table>
<div class="note warn">Ngoài phạm vi: <code>settings_dialog.py:115</code> hard-code mật khẩu
Sandbox; hai lớp cùng tên <code>CustomAgent</code>
(<code>custom_agents.py:23</code> · <code>co4e.py:117</code>).</div>
</div><script>{JS}</script>
{"".join(f"<script>{j}</script>" for j in HAND_JS)}
</body></html>"""

    dest = OUT
    dest.write_text(html, encoding="utf-8")
    missing = [r["slug"] for r in recs if not r["file"]]
    size = dest.stat().st_size
    unit = f"{size / 1024 / 1024:.1f} MB" if size > 1_000_000 else f"{size // 1024} KB"
    kind = ("MOT FILE DUY NHAT — anh da nhung san" if STANDALONE
            else "CAN kem thu muc screens/ moi co hinh")
    print(f"wrote {dest}  ({len(order)} screens, {unit}) — {kind}")
    if missing:
        print(f"placeholders for: {sorted(set(missing))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
