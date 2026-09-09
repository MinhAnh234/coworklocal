"""Kiến thức về chính ứng dụng, nạp cho Trợ lý Hỗ trợ trong app.

Trước khi có file này, prompt hệ thống của agent ``help``
(``core/admin_agents.py::_KIND_PROMPTS``) chỉ là một đoạn văn liệt kê tên các
màn hình. Model không có cách nào biết trên mỗi màn có gì, nên nó lấp khoảng
trống bằng thứ nghe hợp lý: người dùng thật đã được hướng dẫn vào
"Dashboard → Add Project" và "Settings → Project Settings → New Project" — cả
hai đều không tồn tại. Câu trả lời trôi chảy mà sai còn tệ hơn câu "tôi không
biết", vì người dùng đi tìm rồi mới phát hiện ra.

Ba thứ được ghép thêm vào prompt:

* **Sổ tay** (``docs/help/app_guide.md``) — viết tay, bám theo mã nguồn thật, và
  có test chốt rằng danh sách màn hình trong đó khớp ``docs/screens/manifest.json``.
* **Luật chống bịa**, kèm ví dụ chính câu trả lời sai đã xảy ra.
* **Ngữ cảnh sống** — màn hình đang mở và các nút/tab ĐANG hiện trên đó, đọc từ
  cây widget thật (``PageRegistryMixin.help_context``).

Vì sao ngữ cảnh sống đọc từ widget chứ không từ ``docs/screens/controls.json``:
file đó được trích tự động nhưng đã cũ — 5/41 file trong đó không còn tồn tại,
và nó không có file nào trong ``presentation/`` (chưa sinh lại sau refactor R08).
Nạp nó vào prompt là dạy trợ lý về nút của những file đã bị xoá. Cây widget thật
thì không bao giờ cũ được.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

#: docs/help/app_guide.md — core/ nằm sâu 1 cấp so với gốc gói.
_GUIDE = Path(__file__).resolve().parent.parent / "docs" / "help" / "app_guide.md"

#: Trần số nhãn thao tác đưa vào prompt. Một màn đông như Co4E có thể có hàng
#: chục nút; dồn hết vào chỉ làm loãng phần còn lại của prompt mà không thêm
#: thông tin — những nút đầu tiên là những nút người dùng nhìn thấy trước.
_MAX_ACTIONS = 24

#: Luật chống bịa. Đặt SAU sổ tay trong prompt vì đây là thứ cuối cùng model đọc
#: trước khi trả lời, và nó phải thắng mọi phỏng đoán.
_GROUNDING = """
LUẬT TRẢ LỜI VỀ ỨNG DỤNG NÀY — ưu tiên cao hơn mọi kiến thức có sẵn của bạn:

- CHỈ mô tả màn hình, nút và menu có trong sổ tay ở trên, hoặc trong danh sách
  nút đang hiện ở phần ngữ cảnh phía dưới. Hai nguồn đó là nguồn duy nhất.
- KHÔNG suy ra tên nút hay đường dẫn menu từ các phần mềm khác bạn từng biết.
  Ứng dụng này không có "Add Project", không có "Project Settings", và Cài đặt
  không quản lý project.
- Không có trong hai nguồn trên thì trả lời thẳng là bạn không chắc, rồi chỉ
  người dùng tới màn hình gần nhất có liên quan. Đoán một đường dẫn menu là câu
  trả lời tệ hơn "tôi không biết".
- Khi hướng dẫn thao tác, nêu đúng đường đi: màn hình -> sub-tab -> tên nút y
  như trong sổ tay.
- Trả lời ngắn. Ba bước đúng hơn mười bước trong đó có hai bước bịa.

VÍ DỤ — lỗi dưới đây ĐÃ xảy ra với người dùng thật, đừng lặp lại:

  Hỏi: "Tôi tạo dự án mới thế nào?"
  SAI: "Vào Dashboard, nhấn Add Project, hoặc Settings -> Project Settings ->
        New Project. Điền Tên, Owner, Ngày bắt đầu/Kết thúc, Màu nhãn."
        Không một thứ nào trong câu đó tồn tại. Người dùng đã đi tìm và không thấy.
  ĐÚNG: "Vào Workspace ▸ Project, bấm Project mới ở hàng tiêu đề. Điền Tên, Mô
         tả, Hướng dẫn rồi bấm Lưu project. Tên phải khác các project đã có."

  Hỏi: "Đổi API key ở đâu?"
  ĐÚNG: "Nút Cài đặt ở thanh trên, rồi vào mục Nhà cung cấp AI."

  Hỏi: "Có xuất báo cáo PDF được không?"
  ĐÚNG: "Sổ tay không nói tới chỗ nào xuất PDF nên tôi không chắc app có chức
         năng đó. Gần nhất là Workspace ▸ Thư mục, nó xem được tệp PDF sẵn có."
        Nói không biết là câu trả lời đúng ở đây. Đoán một đường dẫn menu thì không.
"""


@lru_cache(maxsize=1)
def app_guide() -> str:
    """Nội dung sổ tay. Thiếu file thì trả chuỗi rỗng, không ném lỗi.

    Trợ lý thiếu sổ tay vẫn phải mở được — nó chỉ kém hữu ích đi, còn ném lỗi ở
    đây thì hỏng luôn cả khung chat.
    """
    try:
        return _GUIDE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def screen_context(screen: str = "", actions=()) -> str:
    """Ngữ cảnh sống: màn hình đang mở, và những gì bấm được trên đó.

    ``actions`` là nhãn của các nút và tab ĐANG hiện. Model không nhìn được màn
    hình, nên không có phần này thì "ở đây làm được gì" là câu nó buộc phải
    đoán — và đoán chính là cách nó bịa ra nút "Add Project".
    """
    screen = (screen or "").strip()
    # ``a is not None`` phải kiểm TRƯỚC khi str(): ``str(None)`` ra chuỗi "None",
    # khác rỗng, nên nó lọt qua bộ lọc và thành một "nút" tên None trong prompt.
    labels = [str(a).strip() for a in (actions or ())
              if a is not None and str(a).strip()]
    if not screen and not labels:
        return ""

    parts = []
    if screen:
        parts.append("MÀN HÌNH NGƯỜI DÙNG ĐANG MỞ: " + screen)
    if labels:
        danh_sach = "\n".join("- " + label for label in labels[:_MAX_ACTIONS])
        parts.append(
            "NÚT VÀ TAB ĐANG HIỆN TRÊN MÀN ĐÓ (đọc từ giao diện đang chạy, nên "
            "đây là danh sách CHÍNH XÁC — người dùng hỏi về một nút không có "
            "trong danh sách này thì nói thẳng là màn này không có nút đó):\n"
            + danh_sach)
    parts.append("Câu hỏi kiểu 'tôi đang ở đâu' hay 'ở đây làm được gì' là hỏi "
                 "về chính màn hình này.")
    return "\n".join(parts)


def build_prompt(base_prompt: str, context: str = "") -> str:
    """Prompt hệ thống đầy đủ cho Trợ lý Hỗ trợ.

    Thứ tự có chủ ý: vai trò -> sổ tay -> luật chống bịa -> ngữ cảnh sống. Luật
    đứng sau sổ tay để nó là thứ cuối cùng model đọc về cách dùng sổ tay, còn
    ngữ cảnh đứng cuối vì nó đổi theo từng lượt hỏi và phải nằm sát câu hỏi nhất.

    ``context`` là khối đã được :func:`screen_context` định dạng sẵn — chỗ gọi
    nằm ở tầng Qt và nó dựng khối này qua ``PageRegistryMixin.help_context``.
    """
    guide = app_guide()
    parts = [(base_prompt or "").strip()]
    if guide:
        parts += ["=== SỔ TAY ỨNG DỤNG ===", guide, _GROUNDING.strip()]
    ctx = (context or "").strip()
    if ctx:
        parts.append(ctx)
    return "\n\n".join(p for p in parts if p)


def greeting(user_name: str = "") -> str:
    """Câu chào mở đầu của khung trợ lý, có tên người dùng nếu biết."""
    from ..i18n import tr

    name = (user_name or "").strip() or tr("help_agent.default_user")
    return tr("help_agent.greeting", name=name)
