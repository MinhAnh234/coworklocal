# Project Map — Cowork Local (dành cho agent sửa bug UI/UX)

Nguồn sự thật: `README.md`, `docs/architecture/ADR-001-layered-architecture.md`,
`docs/governance/contributor-recipes.md`. File này chỉ tóm tắt phần **một người sửa bug
UI cần biết**.

---

## 1. Bốn tầng

```text
presentation/  PySide6 UI — Shell, NavRail, Chat, Scheduling, Settings, Dashboard
      ↓
application/   Orchestration thuần Python — Conversations, Scheduling, Workspaces, Monitoring, Routing
      ↓
domain/        Entity, ExecutionRequest bất biến, AgentEvent, Descriptor (thuần Python)
      ↑
infrastructure/  Adapter — LLM provider, persistence atomic JSON, Keyring SecretStore, MCP
```

- `domain/` và `application/` **không được** import PySide6/PyQt/`ui`/`app`
  (`scripts/check_imports.py::FORBIDDEN_MODULE_PREFIXES`).
- Widget chỉ gọi xuống service của `application/`, không chạm SQLite/JSON/LLM trực tiếp.
- Mọi module production `<= 400 LOC`.

## 2. ⚠️ Hai thư mục UI cùng tồn tại — điểm dễ sửa nhầm file nhất

| Thư mục | Vai trò hiện tại | Sửa bug ở đây khi |
|---|---|---|
| `presentation/` | Kết quả refactor R08 — các màn đã tách module | Bug thuộc Chat, Co4E, Dashboard, Folder, Graph, Scheduling, Settings, Shell |
| `ui/` | **Vẫn đang chạy**, không phải code chết | Bug thuộc Monitoring, Workspace, các dialog, icon, widget dùng chung |

`presentation/` vẫn import ngược sang `ui/` cho phần dùng chung, ví dụ:

```text
presentation/shell/page_registry.py:14   from ...ui.monitoring_tab import MonitoringTab
presentation/shell/main_window.py:38     from ...ui.workspace_tab import WorkspaceTab
presentation/dashboard/dashboard_tab.py:24  from cowork_local.ui.icons import icon
```

**Luật:** trước khi sửa, `grep` tên class/hàm trên **cả hai** thư mục. Sửa bản không được
import vào runtime là lỗi "đã fix nhưng user vẫn thấy lỗi" phổ biến nhất của repo này.

```bash
grep -rn "class DashboardTab" ui/ presentation/
```

## 3. Điểm vào & trạng thái

| File | Vai trò |
|---|---|
| `app.py`, `__main__.py` | Bootstrap `QApplication`, dựng `MainWindow` |
| `presentation/shell/main_window.py` | Cửa sổ chính, `_nav_defs`, top bar, toast, help agent |
| `presentation/shell/page_registry.py` | Chuyển trang; Dashboard/Schedule/Monitoring **dựng lười** |
| `presentation/shell/nav_rail.py` | Nav rail trái, thu gọn/mở rộng, cây project & recents |
| `presentation/shell/top_bar.py` | Thanh trên: theme switch, language switch |
| `presentation/shell/toast.py` | Popup "task xong" góc trên trái |
| `state.py` | `AppContext` — cầu nối UI ↔ service |
| `config.py` | Đọc/ghi cấu hình người dùng (theme, ngôn ngữ, provider...) |
| `paths.py` | Vị trí dữ liệu runtime (`%USERPROFILE%\.cowork_local`) |
| `theme/` | Toàn bộ màu sắc & stylesheet (xem `theme_tokens.md`) |
| `i18n/` | Toàn bộ chuỗi hiển thị (xem `i18n_rules.md`) |

### Hệ quả của "dựng lười" khi debug

Dashboard, Schedule và Monitoring **chưa tồn tại** cho tới lần đầu người dùng bấm vào.
Nghĩa là:

- Bug "lần đầu mở màn X bị nhấp nháy / sai theme / sai ngôn ngữ" gần như luôn nằm ở
  `_ensure_page` / `_goto` chứ không nằm trong widget của màn đó.
- Widget dựng lười **bỏ lỡ** các sự kiện đã phát trước đó (đổi theme, đổi ngôn ngữ).
  Xem `qt_pitfalls.md` P07.

## 4. Bảng đối chiếu tính năng → file

| Khu vực | File chính |
|---|---|
| Chat / composer / bubble | `presentation/chat/` (`chat_panel.py`, `composer_widget.py`, `chat_bubble_style.py`) |
| Co4E canvas & node | `presentation/co4e/` (`co4e_canvas_widget.py`, `node_property_panel.py`, `canvas_geometry.py`) |
| Dashboard & biểu đồ | `presentation/dashboard/` + `ui/spline_chart.py`, `ui/widgets.py` |
| Folder / preview tài liệu | `presentation/folder/` (`folder_tab.py`, `code_editor.py`, `office_document_renderer.py`) |
| GraphRAG | `presentation/graph/` |
| Lịch / Kanban | `presentation/scheduling/` |
| Settings | `presentation/settings/` + `ui/settings_dialog.py` |
| Monitoring (8 sub-view) | `ui/monitoring_tab.py` + `presentation/monitoring/` |
| Workspace + sub-tab | `ui/workspace_tab.py`, `ui/cowork_tab.py`, `ui/co4e_tab.py` |
| Dialog (login, permission, skill, task...) | `ui/*_dialog.py` |
| Icon | `ui/icons.py` |
| Widget dùng chung (StatCard, BudgetCard...) | `ui/widgets.py` |

## 5. Test

| Đường dẫn | Nội dung |
|---|---|
| `tests/ui/` | Test widget, có `conftest.py` riêng |
| `tests/integration/` | Test ghép nhiều thành phần |
| `tests/e2e/test_smoke.py` | Smoke test bản release |
| `tests/characterization/` | Chốt hành vi hiện tại trước khi refactor |

Chạy headless: `QT_QPA_PLATFORM=offscreen pytest tests/ui -q`.
64/108 module test dựng widget thật, nên môi trường phải có PySide6.
