"""Danh sách project và việc sửa một project — bóc khỏi ``ui/workspace_tab.py``.

Bóc ra vì ``ui/workspace_tab.py`` đã chạm đúng trần bánh cóc của nó trong
``scripts/check_loc.py::LEGACY_ALLOWANCE`` (566 dòng mã): file đó chỉ được co
lại, không được phình thêm. Bốn tính năng dưới đây đều thêm mã vào cùng một chỗ,
nên chúng đi cùng nhau sang đây thay vì bị nhét vào một file đã đầy.

Gộp bốn thứ vào một module không phải để lách trần — chúng là một khối:

* **Chế độ chỉ-xem.** Project đã có mở ra ở dạng chỉ đọc; phải bấm "Sửa project"
  mới gõ được. Trước đây form luôn mở, nên chỉ cần lỡ tay là sửa mất nội dung của
  một project đang dùng mà không có gì cảnh báo.
* **Chặn trùng tên.** Hai project cùng tên thì danh sách bên trái không còn phân
  biệt được, mà tên lại là thứ duy nhất dòng đó hiển thị.
* **Menu chuột phải.** Bấm phải vào một project trước đây không làm gì cả.
* **Dựng lại nhãn số liệu khi đổi ngôn ngữ.** ``workspace.counts`` được format
  một lần lúc dựng dòng, nên đổi ngôn ngữ xong nó vẫn nằm ở ngôn ngữ cũ.

Ba việc đầu phải nằm chung: "Sửa" trong menu chuột phải bật đúng chế độ mà nút
"Sửa project" bật, và việc chặn trùng tên chỉ có nghĩa khi biết form đang sửa
project nào.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QLayout, QMenu, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from ...i18n import tr
from ...ui.dialog_buttons import confirm

#: Ten project mac dinh. Co y KHONG dich — xem ghi chu trong ``_create``.
_DEFAULT_PROJECT_NAME = "Project"


class ProjectRow(QWidget):
    """A project in the list: its name, and under it how much is in it.

    The drawing gives every row a second line — "2 đoạn chat · 3 task" — which
    is the only thing on this screen that says a project holds anything at all.

    Số liệu được giữ lại dưới dạng SỐ (``chats``/``tasks``) chứ không chỉ chuỗi
    đã format, để đổi ngôn ngữ còn dựng lại được câu mà không phải đọc lại đĩa.
    """

    def __init__(self, name: str, chats: int, tasks: int) -> None:
        """Một dòng dự án trong danh sách: tên ở trên, số liệu tóm tắt ở dưới."""
        super().__init__()
        self.chats = chats
        self.tasks = tasks

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(3)
        self.title_label = QLabel(name)
        self.counts_label = QLabel()
        self.counts_label.setObjectName("hint")
        lay.addWidget(self.title_label)
        lay.addWidget(self.counts_label)
        self.retranslate()

    def retranslate(self) -> None:
        """Dựng lại dòng số liệu theo ngôn ngữ đang chọn."""
        self.counts_label.setText(
            tr("workspace.counts", chats=self.chats, tasks=self.tasks))


def _row_layout_of(widget: QWidget) -> QLayout | None:
    """Layout đang trực tiếp chứa ``widget``.

    Qt không cho hỏi ngược "ai đang giữ tôi", nên phải duyệt cây layout của
    widget cha. Dùng để chèn nút "Sửa project" ngay cạnh nút Lưu mà không phải
    thêm dòng nào vào ``_build_project_tab`` (xem docstring đầu file).
    """
    parent = widget.parentWidget()
    if parent is None:
        return None
    stack = [parent.layout()]
    while stack:
        layout = stack.pop()
        if layout is None:
            continue
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget() is widget:
                return layout
            if item.layout() is not None:
                stack.append(item.layout())
    return None



class ProjectEditingMixin:
    """Danh sách project + CRUD + chế độ sửa. Trộn vào ``WorkspaceTab``.

    Cùng kiểu mixin với ``presentation/shell/`` (``NavRailMixin``,
    ``RailProjectMixin``, …): lớp này đọc thẳng các thuộc tính mà
    ``WorkspaceTab`` dựng (``project_list``, ``name_edit``, ``_save_btn``, …)
    nên nó không dùng lại được ở nơi khác — mục đích là chia file, không phải
    dựng một lớp trừu tượng.
    """

    # ---- lắp đặt ---------------------------------------------------------

    def install_project_editing(self) -> None:
        """Dựng nút "Sửa project", nối menu chuột phải, và khoá form lại.

        Gọi một lần, sau khi ``_build_project_tab`` đã dựng xong các widget.
        """
        self._project_editable = False

        self._edit_btn = QPushButton()
        self._edit_btn.setObjectName("warning")
        self._edit_btn.clicked.connect(self.enter_project_edit_mode)

        # Ba nut cua man quan ly project ve chung MOT hang, canh "Project moi" o
        # hang tieu de. Truoc do "Luu project" nam duoi cung khung ben phai, cach
        # "Project moi" gan het chieu cao man hinh, nen ba viec cung mot nhom lai
        # o ba cho khac nhau. Hang tieu de vat ngang ca man Workspace va da chi
        # hien tren sub-tab Project (xem _new_btn.setVisible(on_project)).
        title_row = _row_layout_of(self._new_btn)
        if title_row is not None:
            at = title_row.indexOf(self._new_btn) + 1
            title_row.insertWidget(at, self._edit_btn)
            title_row.insertWidget(at + 1, self._save_btn)
        else:
            save_row = _row_layout_of(self._save_btn)
            if save_row is not None:
                save_row.insertWidget(save_row.count() - 1, self._edit_btn)

        # Hang tieu de vat ngang CA man Workspace, nen thu gi dat len do cung
        # hien o Cowork, Co4E, Thu muc va GraphRAG neu khong tu an di. Do la
        # dung luat ma _new_btn da theo (_new_btn.setVisible(on_project) trong
        # WorkspaceTab._apply_pane_visibility) — hai nut nay phai theo y nhu vay.
        self.tabs.currentChanged.connect(self._sync_project_buttons)
        # Đổi project cũng phải đồng bộ lại: ``_load_current`` nạp form và đặt
        # ``_current_id`` rồi phát tín hiệu này, nhưng không đụng tới ba nút.
        self.project_selected.connect(self._sync_project_buttons)

        self.project_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self._show_project_menu)

        self.set_project_editable(False)

    # ---- chế độ chỉ-xem / sửa -------------------------------------------

    def _editable_fields(self) -> list:
        """Các ô mà chế độ sửa mở khoá. ``folder_lbl`` không có ở đây: nó vốn
        chỉ đọc, đường dẫn đổi qua nút Chọn thư mục."""
        return [self.name_edit, self.desc_edit, self.instr_edit]

    def set_project_editable(self, on: bool) -> None:
        """Bật/tắt chế độ sửa của form project.

        Tắt: các ô thành chỉ đọc, nút Lưu và Chọn thư mục mờ đi, nút Sửa hiện ra.
        Bật: ngược lại, và nút Lưu chuyển sang màu xác nhận (token ``success``).
        """
        self._project_editable = on

        for field in self._editable_fields():
            # setReadOnly thay vì setEnabled: ô mờ đi thì không bôi đen copy
            # được nữa, mà đọc và copy chính là việc của chế độ chỉ-xem.
            field.setReadOnly(not on)
        # Ba nút không tự bật/tắt ở đây: ``_sync_project_buttons`` mới là nơi
        # duy nhất tính trạng thái của chúng, vì nó còn chạy cả khi người dùng
        # đổi project — lúc đó ``set_project_editable`` không được gọi.
        self._sync_project_buttons()

        # Nút Lưu xanh lá khi đang sửa (hành động xác nhận), về màu nhấn mặc
        # định khi chỉ xem. Màu lấy từ token trong theme/ — xem theme/__init__.py.
        self._save_btn.setObjectName("success" if on else "primary")
        self._repolish(self._save_btn)
        self._repolish(self._edit_btn)

    def _sync_project_buttons(self, *_a) -> None:
        """Đồng bộ CẢ hiện/ẩn LẪN bật/mờ của ba nút theo trạng thái hiện tại.

        Ẩn ngoài sub-tab Project: chúng nằm trên hàng tiêu đề dùng chung, nên
        không tự ẩn là chúng hiện cả ở Cowork — nơi không có biểu mẫu project
        nào để sửa hay lưu.

        Bật/mờ cũng tính ở đây chứ không ở ``set_project_editable``: đổi
        project KHÔNG đi qua hàm đó (``_load_current`` chỉ nạp lại form), nên
        để ở đó thì "Sửa project" giữ nguyên trạng thái tính từ lúc dựng —
        lúc chưa project nào được chọn — và cứ mờ mãi dù project đã mở.
        """
        on_project = self.tabs.currentIndex() == self._project_tab_idx
        has_project = bool(getattr(self, "_current_id", ""))
        dang_sua = bool(getattr(self, "_project_editable", False))
        self._edit_btn.setVisible(on_project and has_project)
        self._save_btn.setVisible(on_project and has_project)
        self._edit_btn.setEnabled(not dang_sua and has_project)
        self._save_btn.setEnabled(dang_sua and has_project)
        self._browse_btn.setEnabled(dang_sua and has_project)

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        """Ép Qt đánh giá lại style sau khi đổi ``objectName``.

        Không có bước này thì QSS đã khớp lúc dựng vẫn giữ nguyên — đổi
        objectName một mình không kích hoạt tính lại (bẫy P08).
        """
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def enter_project_edit_mode(self) -> None:
        """Mở khoá form và đưa con trỏ vào ô Tên."""
        if not getattr(self, "_current_id", ""):
            return
        self.set_project_editable(True)
        self.name_edit.setFocus()

    # ---- menu chuột phải -------------------------------------------------

    def _show_project_menu(self, pos) -> None:
        """Menu chuột phải trên một dòng project: Mở / Sửa / Xoá.

        Bấm phải vào một dòng trước đây không làm gì cả — ba việc này đều đã
        có sẵn ở nơi khác trên màn hình, menu chỉ là đường vào thứ hai.
        """
        item = self.project_list.itemAt(pos)
        if item is None:
            return
        # Bấm phải cũng chọn dòng đó, để menu thao tác lên đúng thứ vừa bấm
        # chứ không lên dòng đang được chọn từ trước.
        self.project_list.setCurrentItem(item)

        menu = QMenu(self.project_list)
        open_act = menu.addAction(tr("workspace.menu_open"))
        edit_act = menu.addAction(tr("workspace.menu_edit"))
        menu.addSeparator()
        del_act = menu.addAction(tr("workspace.menu_delete"))

        chosen = menu.exec(self.project_list.viewport().mapToGlobal(pos))
        if chosen is open_act:
            self.open_selected_project()
        elif chosen is edit_act:
            self.enter_project_edit_mode()
        elif chosen is del_act:
            self._delete()

    def open_selected_project(self) -> None:
        """Mở project đang chọn: sang sub-tab Cowork của chính nó."""
        self._load_current()
        self._show_cowork_tab()

    # ---- trùng tên -------------------------------------------------------

    def _name_taken(self, name: str, *, ignore_id: str = "") -> bool:
        """Đã có project khác mang tên này chưa.

        So không phân biệt hoa thường và bỏ khoảng trắng hai đầu: với người
        dùng thì "Báo cáo" và "báo cáo " là cùng một cái tên, mà tên lại là thứ
        duy nhất dòng trong danh sách hiển thị.
        """
        from ...core.projects import list_projects

        wanted = (name or "").strip().casefold()
        if not wanted:
            return False
        return any(p.name.strip().casefold() == wanted and p.project_id != ignore_id
                   for p in list_projects())

    def _warn_duplicate_name(self, name: str) -> None:
        """Báo cho người dùng biết tên đã có, và nói rõ tên nào."""
        QMessageBox.warning(self, tr("workspace.name_taken_title"),
                            tr("workspace.name_taken_body", name=name.strip()))
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    # ---- CRUD (chuyển từ ui/workspace_tab.py sang) -----------------------

    def _create(self) -> None:
        """Tạo project mới với tên mặc định rồi chọn nó.

        Tên mặc định phải là tên CHƯA có: người dùng bấm "Project mới" hai lần
        liên tiếp thì lần thứ hai sẽ trùng lần thứ nhất.
        """
        from ...core.projects import new_project

        # KHONG dung tr() cho ten mac dinh: ten project duoc GHI XUONG DIA. Tao
        # project luc dang o tieng Nhat thi ten no thanh "新規プロジェクト" vinh
        # vien, va doi ngon ngu ve tieng Viet khong sua duoc — do la du lieu, khong
        # phai chu giao dien. Nguoi dung nhin thay chu Nhat tren man hinh tieng
        # Viet va tuong la loi hien thi. Mot ten trung tinh khong bao gio noi doi.
        base = _DEFAULT_PROJECT_NAME
        name, n = base, 2
        while self._name_taken(name):
            name, n = f"{base} ({n})", n + 1

        project = new_project(name)
        self._current_id = project.project_id
        self.refresh()
        self.projects_changed.emit()
        # Project vừa tạo thì mở sẵn chế độ sửa: chưa đặt tên thì chưa dùng được.
        self.set_project_editable(True)
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def _delete(self) -> None:
        """Xoá project đang chọn sau khi hỏi xác nhận."""
        from ...core.projects import delete_project, load_project

        pid = self._selected_id()
        project = load_project(pid) if pid else None
        if project is None:
            return
        if not confirm(self, tr("workspace.delete"),
                       tr("workspace.delete_confirm", name=project.name)):
            return
        delete_project(pid)
        self._current_id = ""
        self.refresh()   # empty workspace → Cowork/GraphRAG hidden until a new project
        self.projects_changed.emit()
        self.status_message.emit(tr("workspace.deleted", name=project.name))

    def _save(self) -> None:
        """Lưu tên, mô tả và chỉ dẫn chung của project đang mở."""
        from ...core.projects import load_project, save_project

        pid = self._current_id
        project = load_project(pid) if pid else None
        if project is None:
            return
        new_name = self.name_edit.text().strip()
        # Chặn TRƯỚC khi ghi: ghi xong rồi mới báo là đã hỏng dữ liệu trên đĩa.
        if new_name and self._name_taken(new_name, ignore_id=pid):
            self._warn_duplicate_name(new_name)
            return
        project.name = new_name or project.name
        project.description = self.desc_edit.text().strip()
        project.instructions = self.instr_edit.toPlainText().strip()
        save_project(project)
        self.refresh()
        self.projects_changed.emit()
        self.status_message.emit(tr("workspace.saved", name=project.name))
        # Lưu xong thì khoá lại: chế độ sửa là một lần sửa, không phải trạng
        # thái dính cho tới khi người dùng nhớ ra phải tắt.
        self.set_project_editable(False)

    # ---- i18n ------------------------------------------------------------

    def retranslate_project_rows(self) -> None:
        """Dựng lại nhãn số liệu của mọi dòng project theo ngôn ngữ mới.

        KHÔNG gọi ``refresh()`` ở đây: ``refresh()`` kết thúc bằng
        ``_load_current()``, nạp lại form từ đĩa — đổi ngôn ngữ giữa chừng sẽ
        xoá mất nội dung người dùng đang gõ dở.
        """
        for i in range(self.project_list.count()):
            row = self.project_list.itemWidget(self.project_list.item(i))
            if isinstance(row, ProjectRow):
                row.retranslate()
        if hasattr(self, "_edit_btn"):
            self._edit_btn.setText(tr("workspace.edit_project"))
