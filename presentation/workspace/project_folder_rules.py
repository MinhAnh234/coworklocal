"""Luật "mỗi thư mục làm việc chỉ thuộc về MỘT project".

Tách khỏi ``project_editing.py`` chứ không nhét thêm vào đó: file kia đã gom
bốn tính năng và thêm luật này là chạm trần 400 dòng của
``scripts/check_loc.py``. Đây cũng là một mối quan tâm riêng — nó không nói về
việc *sửa* một project mà về việc hai project không được giẫm lên nhau.

Luật có hai nửa, cố ý không đối xứng:

* **Chặn lúc CHỌN.** Ba nơi đặt được thư mục làm việc (nút "Đổi" ở màn Project,
  thư mục cloud, nút chọn thư mục trong tab Cowork) đều đi qua
  :func:`folder_taken_blocked`, để cả ba chặn giống hệt nhau. Không chặn ở
  "Lưu project": nút đó chỉ ghi tên/mô tả/chỉ dẫn, chặn ở đó sẽ khoá luôn việc
  đổi tên một project lỡ đang trùng thư mục.
* **Cảnh báo cho cái ĐANG sai.** Dữ liệu cũ có thể đã có hai project trỏ vào
  cùng một thư mục, mà nửa trên chỉ chặn từ nay trở đi. Nhãn dưới ô "Thư mục
  làm việc" nói ra điều đó và để người dùng tự đổi — sửa hộ là tự ý đụng vào
  dữ liệu của họ.

Phép so trùng nằm ở ``core/projects.py::folder_conflict`` (thuần, không Qt).
"""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLayout, QMessageBox, QWidget

from ...i18n import tr
from .project_editing import _row_layout_of


def _layout_chua(layout: QLayout, con: QLayout) -> "tuple | None":
    """``(layout_cha, vị_trí)`` của ``con`` bên trong ``layout``, duyệt đệ quy."""
    for i in range(layout.count()):
        item = layout.itemAt(i)
        ben_trong = item.layout()
        if ben_trong is con:
            return layout, i
        if ben_trong is not None:
            tim = _layout_chua(ben_trong, con)
            if tim is not None:
                return tim
    return None


def folder_taken_blocked(parent: QWidget, path: str, ignore_id: str) -> bool:
    """``True`` nếu ``path`` đã thuộc project khác — và đã báo cho người dùng.

    Dùng chung cho cả ba nơi đặt được thư mục làm việc (nút "Đổi" ở màn
    Project, thư mục cloud, và nút chọn thư mục trong tab Cowork), để cả ba
    chặn giống hệt nhau thay vì mỗi nơi tự nghĩ ra một luật.

    Chặn ở lúc CHỌN chứ không ở lúc Lưu: "Lưu project" chỉ ghi tên, mô tả và
    chỉ dẫn — chặn ở đó sẽ khoá luôn việc đổi tên một project lỡ đang trùng
    thư mục, tức phạt người dùng vì một trạng thái họ chưa kịp sửa.
    """
    from ...core.projects import folder_conflict

    khac = folder_conflict(path, ignore_id=ignore_id)
    if khac is None:
        return False
    QMessageBox.warning(parent, tr("workspace.folder_taken_title"),
                        tr("workspace.folder_taken_body", name=khac.name,
                           folder=str(khac.workspace_dir())))
    return True



class ProjectFolderRuleMixin:
    """Nửa giao diện của luật. Trộn vào ``WorkspaceTab``."""

    def install_project_folder_rule(self) -> None:
        """Dựng nhãn cảnh báo và nối nó vào việc đổi project.

        Gọi từ ``install_project_editing``, tức sau khi form đã dựng xong.
        """
        self._folder_warn_lbl = QLabel()
        self._folder_warn_lbl.setObjectName("warning")   # màu lấy từ theme/
        self._folder_warn_lbl.setWordWrap(True)
        self._folder_warn_lbl.hide()
        self._gan_nhan_canh_bao_thu_muc()
        self.project_selected.connect(self._sync_folder_warning)

    def rebind_workspace_folder(self) -> None:
        """Thư mục làm việc vừa đổi — trỏ lại những màn đang bám vào nó.

        Đổi thư mục KHÔNG làm project id đổi, nên không có gì trong luồng
        chọn project chạy lại: ``_pick_folder`` ghi ``output_dir`` rồi dừng.
        Tab Thư mục và màn GraphRAG vì thế giữ nguyên đường dẫn cũ — tên
        project vẫn đúng nên nhìn qua tưởng ổn, nhưng GraphRAG quét nhầm
        thư mục.

        Cố ý KHÔNG gọi ``_load_current``: hàm đó nạp lại cả biểu mẫu từ đĩa,
        nên gọi nó lúc người dùng đang sửa dở Tên/Mô tả là xoá mất phần chưa
        lưu.
        """
        from ...core.projects import load_project

        pid = getattr(self, "_current_id", "")
        project = load_project(pid) if pid else None
        if project is None:
            return
        if getattr(self, "_folder", None) is not None:
            self._folder.set_project_root(str(project.workspace_dir()))
        if getattr(self, "_structure", None) is not None:
            self._structure.set_workspace_project(pid)
        # Thư mục mới có thể vừa gỡ bỏ (hoặc tạo ra) một cảnh báo dùng chung.
        self._sync_folder_warning()

    def _gan_nhan_canh_bao_thu_muc(self) -> None:
        """Chèn nhãn cảnh báo ngay DƯỚI hàng chứa ô Thư mục làm việc.

        Chèn từ đây thay vì thêm dòng vào ``_build_project_tab``: file
        ``ui/workspace_tab.py`` đang vượt trần của ``scripts/check_loc.py``,
        nên mọi dòng mới đều phải tránh nó (cùng lý do nút "Sửa project" được
        chèn bằng ``_row_layout_of``).
        """
        hang = _row_layout_of(self.folder_lbl)
        cha = self.folder_lbl.parentWidget()
        if hang is None or cha is None or cha.layout() is None:
            return
        tim = _layout_chua(cha.layout(), hang)
        if tim is None:
            return
        layout, vi_tri = tim
        layout.insertWidget(vi_tri + 1, self._folder_warn_lbl)

    def _sync_folder_warning(self, *_a) -> None:
        """Hiện/ẩn cảnh báo "thư mục đang dùng chung" theo project đang mở."""
        from ...core.projects import folder_conflict, load_project

        pid = getattr(self, "_current_id", "")
        project = load_project(pid) if pid else None
        khac = (folder_conflict(project.workspace_dir(), ignore_id=pid)
                if project is not None else None)
        if khac is None:
            self._folder_warn_lbl.hide()
            return
        self._folder_warn_lbl.setText(
            tr("workspace.folder_shared_warning", name=khac.name))
        self._folder_warn_lbl.show()
