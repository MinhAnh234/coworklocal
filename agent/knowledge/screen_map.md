# Screen Map — Tra mô tả của người dùng về đúng file:line

Người dùng thường mô tả lỗi bằng ngôn ngữ tự nhiên, ví dụ:

> "Cái bảng bên phải của màn thống kê bị lệch."

Agent phải dùng file này để chuyển mô tả đó thành:

```text
Màn hình → Tab/View → Widget → File → Line → Control
```

Mục tiêu là tìm được **đúng widget và đúng vị trí code**, thay vì đoán file dựa trên tên.

---

## 1. Bốn màn hình chính trong Nav Rail

Các màn hình chính được định nghĩa tại:

```text
presentation/shell/main_window.py:151
```

Danh sách nằm trong `_nav_defs`.

**Thứ tự trong bảng chính là page index.**

| Row | i18n key             | Icon         | Cách tạo        | Widget                                                          |
| --: | -------------------- | ------------ | --------------- | --------------------------------------------------------------- |
|   0 | `app.tab.dashboard`  | `dashboard`  | Lazy            | `presentation/dashboard/dashboard_tab.py::DashboardTab`         |
|   1 | `app.tab.schedule`   | `schedule`   | Lazy            | `presentation/scheduling/schedule_task_tab.py::ScheduleTaskTab` |
|   2 | `app.tab.workspace`  | `workspaces` | Ngay khi mở app | `ui/workspace_tab.py::WorkspaceTab`                             |
|   3 | `app.tab.monitoring` | `monitoring` | Lazy            | `ui/monitoring_tab.py::MonitoringTab`                           |

### Màn hình mặc định

Khi mở app, người dùng bắt đầu tại:

```text
Workspace → Project
```

### Lưu ý về Lazy

`Dashboard`, `Schedule` và `Monitoring` được tạo **lazy** — chỉ được dựng khi người dùng mở màn hình.

Vì vậy, khi điều tra lỗi liên quan đến các màn hình này, phải kiểm tra cả **thời điểm widget được tạo** và **vòng đời của widget**.

---

## 2. Các tab bên trong Workspace

Các tab được định nghĩa trong:

```text
ui/workspace_tab.py:214-245
```

| Tab      | i18n key                 | Widget/File                                        |
| -------- | ------------------------ | -------------------------------------------------- |
| Project  | `workspace.tab_project`  | `_build_project_tab()` trong `ui/workspace_tab.py` |
| Cowork   | `workspace.tab_cowork`   | `ui/cowork_tab.py`                                 |
| Co4E     | `workspace.tab_co4e`     | `ui/co4e_tab.py` → `presentation/co4e/`            |
| Folder   | `workspace.tab_folder`   | `presentation/folder/folder_tab.py`                |
| GraphRAG | `workspace.tab_graphrag` | `presentation/graph/structure_graph_view.py`       |

### Monitoring có cấu trúc khác

Monitoring có **tab strip riêng**, gồm 8 sub-view:

1. Tổng quan.
2. Trạng thái Agent.
3. Công cụ.
4. Nhật ký hành động.
5. Lịch sử gọi MCP.
6. Sự kiện bảo mật.
7. Agents Admin.
8. Icon.

**Workspace là màn hình duy nhất không hiển thị tab strip theo cách này.**

Nếu người dùng nói:

> "Tab trạng thái agent trong màn Monitoring"

thì không được nhầm nó với một tab của Workspace.

---

## 3. Các thành phần luôn xuất hiện trên mọi màn hình

Một số thành phần nằm ngoài nội dung của từng màn hình.

| Thành phần                      | File                             | Cách người dùng thường mô tả                       |
| ------------------------------- | -------------------------------- | -------------------------------------------------- |
| Nav rail bên trái / nút thu gọn | `presentation/shell/nav_rail.py` | "Menu bị co lại", "Không thấy tên project"         |
| Top bar / theme / ngôn ngữ      | `presentation/shell/top_bar.py`  | "Đổi giao diện không ăn", "Đổi ngôn ngữ không đổi" |
| Toast góc trên trái             | `presentation/shell/toast.py`    | "Thông báo xong việc che mất nút"                  |
| Help Agent góc dưới phải        | `ui/help_agent_widget.py`        | "Con robot che nút gửi"                            |
| Status bar phía dưới            | `main_window.statusBar()`        | "Dòng chữ dưới đáy không đổi"                      |

### Quy tắc

Nếu người dùng mô tả một thành phần thuộc nhóm trên, **không cần tìm sub-tab trước**.

Hãy kiểm tra trực tiếp file tương ứng.

---

## 4. Các Dialog

Các dialog chính nằm trong `ui/`:

```text
ui/
├── login_dialog.py
├── permission_dialog.py
├── settings_dialog.py
├── skills_dialog.py
├── task_editor_dialog.py
├── file_edit_dialog.py
├── flow_dialog.py
├── mcp_servers_dialog.py
├── co4e_agent_dialog.py
└── ext_connector_dialog.py
```

Ví dụ:

> "Khi mở Permission thì nút Allow bị..."

→ kiểm tra trước:

```text
ui/permission_dialog.py
```

Không tự động tìm trong `presentation/` chỉ vì lỗi xảy ra trên UI.

---

# 5. Hai file tra cứu bắt buộc

Khi cần chuyển mô tả của người dùng thành `file:line`, phải ưu tiên sử dụng:

```text
docs/screens/manifest.json
docs/screens/controls.json
```

---

## 5.1. `docs/screens/manifest.json`

File này chứa thông tin về các màn hình đã được chụp screenshot.

Mỗi màn hình có các thông tin chính:

```text
slug
title
theme
note
file
nav
```

Trong đó:

* `slug` — tên định danh của màn hình.
* `title` — tên hiển thị.
* `theme` — Dark hoặc Light.
* `note` — **vị trí code dựng màn hình (`file.py:line`)**.
* `file` — đường dẫn đến screenshot.
* `nav` — màn hình thuộc nav nào.

### Ví dụ

Người dùng nói:

> "Màn Kanban lịch trình bị lỗi."

Có thể tìm màn hình liên quan bằng:

```bash
python -c "import json;print([e for e in json.load(open('docs/screens/manifest.json')) if 'schedule' in e['slug']])"
```

Sau đó lấy `note` để biết:

```text
file.py:line
```

### Screenshot Dark và Light

Mỗi màn hình thường có hai ảnh:

```text
<slug>-dark.png
<slug>-light.png
```

Dùng hai ảnh này để:

* So sánh trước/sau.
* Kiểm tra lỗi chỉ xảy ra ở một theme.
* Kiểm tra sự khác biệt giữa Dark Mode và Light Mode.

---

## 5.2. `docs/screens/controls.json`

Đây là danh sách các control được trích tự động từ source code.

Mỗi control có thông tin như:

```text
file
var
type
kind
label
line
signals
object_name
```

Trong đó:

* `file` — file chứa control.
* `var` — tên biến.
* `type` — loại widget, ví dụ `QLineEdit`.
* `kind` — mô tả dễ hiểu, ví dụ `"ô nhập"`, `"nút"`.
* `label` — text/label liên quan.
* `line` — dòng code.
* `signals` — signal liên quan.
* `object_name` — `objectName` của widget.

### Ví dụ

Người dùng nói:

> "Ô nhập email trong màn tài khoản bị lỗi."

Có thể tìm control bằng:

```bash
python - <<'PY'
import json

for f in json.load(open('docs/screens/controls.json')):
    for c in f['controls']:
        text = (c['var'] + c['label']).lower()
        if 'email' in text:
            print(
                f["file"],
                c["line"],
                c["var"],
                c["type"],
                c["object_name"]
            )
PY
```

Từ kết quả có thể xác định:

```text
file
line
variable
widget type
objectName
```

---

## 6. `object_name` đặc biệt quan trọng khi điều tra UI

Khi sửa lỗi màu hoặc style, phải chú ý đến:

```text
object_name
```

Nếu `object_name` đang rỗng, có nghĩa widget đó **chưa được gắn `objectName` để áp style theo cơ chế template/QSS**.

Khi đó widget có thể đang sử dụng style mặc định của class.

Đây thường là nguyên nhân khiến người dùng thấy:

> "Chỗ này nhìn khác chỗ kia."

Ví dụ:

```text
Widget A → objectName = "project_title"
             ↓
          QSS áp style riêng

Widget B → objectName = ""
             ↓
          dùng style mặc định
```

Vì vậy, khi gặp lỗi visual liên quan đến màu/style, hãy kiểm tra `object_name` trước khi tự thêm màu hoặc `setStyleSheet()`.

---

# 7. Quy trình 4 bước dành cho Triage

Khi người dùng báo lỗi bằng ngôn ngữ tự nhiên, thực hiện theo thứ tự sau:

### Bước 1 — Xác định màn hình chính

Xác định lỗi thuộc:

```text
Dashboard
Schedule
Workspace
Monitoring
```

Dựa trên mô tả của người dùng hoặc screenshot.

---

### Bước 2 — Xác định tab/view/dialog

Tiếp tục xác định:

```text
Sub-tab
→ View
→ Dialog
```

Ví dụ:

```text
Workspace
  → Co4E
      → Agent Dialog
```

hoặc:

```text
Monitoring
  → Security Events
```

---

### Bước 3 — Tra `manifest.json`

Mở:

```text
docs/screens/manifest.json
```

Tìm màn hình tương ứng và lấy:

```text
note → file.py:line
```

Đây là điểm bắt đầu để tìm code dựng màn hình.

---

### Bước 4 — Tra `controls.json`

Nếu lỗi liên quan đến một control cụ thể, tiếp tục tìm trong:

```text
docs/screens/controls.json
```

Lấy:

```text
var
line
type
object_name
```

Sau đó xác định chính xác widget bị lỗi.

---

# 8. Quy tắc về Confidence

Triage phải phản ánh đúng mức độ chắc chắn của kết quả.

Nếu chưa hoàn thành đủ 4 bước:

```text
1. Nav
2. Tab/View/Dialog
3. manifest.json
4. controls.json
```

thì:

```yaml
confidence: low
```

Không được tự nâng lên `medium` hoặc `high` chỉ vì file nhìn có vẻ đúng.

### Khi nào có thể tăng Confidence?

Chỉ tăng khi có bằng chứng cụ thể, ví dụ:

```text
User description
      ↓
Dashboard
      ↓
Statistics view
      ↓
manifest.json
      ↓
presentation/dashboard/dashboard_tab.py:123
      ↓
controls.json
      ↓
QTableView
      ↓
line 245
```

Khi đó mới có đủ cơ sở để ghi nhận `file:line` và đánh giá confidence cao hơn.

---

# 9. Nguyên tắc quan trọng

**Không đoán file từ tên.**

Không nên suy luận kiểu:

> "Lỗi ở Workspace nên chắc chắn nằm trong `workspace_tab.py`."

Thay vào đó:

```text
Mô tả của user
      ↓
Xác định màn hình
      ↓
Xác định tab/view/dialog
      ↓
Tra manifest.json
      ↓
Xác định file:line
      ↓
Tra controls.json
      ↓
Xác định widget/control
      ↓
Đánh giá confidence
```

Mục tiêu cuối cùng của Screen Map là biến một mô tả mơ hồ của người dùng thành một đầu vào có thể sử dụng được cho `defect_record`, đặc biệt là:

```text
screen
widget
file
line
object_name
confidence
```
