# Cowork-Local BamBOO — sổ tay màn hình và thao tác

Tài liệu này được nạp thẳng vào prompt hệ thống của **Trợ lý Hỗ trợ trong ứng dụng**
(`core/admin_agents.py`, agent `help`). Nó là nguồn sự thật duy nhất mà trợ lý được phép
dựa vào khi trả lời "màn này là gì / tôi làm được gì ở đây".

**Luật khi sửa file này:** chỉ ghi những gì THẬT SỰ có trong ứng dụng. Một nút không tồn
tại ở đây sẽ trở thành một nút không tồn tại mà trợ lý bảo người dùng đi tìm. Danh sách
màn hình phải khớp `docs/screens/manifest.json` — có test chốt việc đó
(`tests/ui/test_help_knowledge.py`).

---

## 1. Bố cục chung

| Vùng | Có gì |
|---|---|
| **Thanh menu trái** | 4 màn chính; bộ chọn project; mục **GẦN ĐÂY** với link **Tất cả project…**; nút thu gọn menu. Kéo cạnh phải để đổi bề rộng (tối thiểu 132px, không kéo mất được) |
| **Thanh trên** | Đổi giao diện Sáng/Tối, đổi ngôn ngữ (EN / JP / VN), nút Cài đặt |
| **Thanh dưới** | Dòng trạng thái |
| **Góc dưới phải** | Trợ lý Hỗ trợ (biểu tượng robot) — chính là tôi |

Bốn màn chính trên thanh menu: **Dashboard**, **Schedule Task**, **Workspace**, **Monitoring**.

⚠️ Ứng dụng **không có** màn "Project Settings", **không có** nút "Add Project" ở Dashboard.
Mọi việc quản lý project nằm ở **Workspace ▸ Project**.

---

## 2. Workspace — màn chính, nơi app mở lên

Workspace có 5 sub-tab, chọn ở thanh menu trái: **Project**, **Cowork**, **Co4E**,
**Thư mục**, **GraphRAG**.

⚠️ Cowork và GraphRAG **chỉ hiện khi đã chọn một project**. Chưa có project nào thì chỉ
thấy sub-tab Project.

### 2.1 Workspace ▸ Project — quản lý project

Bên trái là danh sách project, mỗi dòng hiện tên và số liệu ("2 đoạn chat · 3 task").
Bên phải là biểu mẫu của project đang chọn.

**Tạo project mới:** nút **Project mới** ở hàng tiêu đề, phía trên danh sách project.

**Sửa project đang có:** biểu mẫu mở ra ở chế độ **chỉ xem**. Bấm **Sửa project** (nút
vàng) mới gõ được; nút **Lưu project** chuyển sang xanh lá. Lưu xong tự khoá lại.

**Bấm chuột phải vào một project** trong danh sách: **Mở** / **Sửa** / **Xoá**.

Các ô trong biểu mẫu:

| Ô | Ý nghĩa |
|---|---|
| Tên | Bắt buộc khác nhau giữa các project — trùng tên sẽ bị báo lỗi và không lưu |
| Mô tả | Chú thích ngắn, hiện làm tooltip trong danh sách |
| Hướng dẫn | Chỉ dẫn chung áp cho MỌI đoạn chat trong project này |
| Thư mục làm việc | Thư mục sandbox của project. Nút Chọn thư mục để đổi, nút Mở thư mục để mở trong Explorer |

**Xoá project:** nút Xoá dưới danh sách, hoặc chuột phải ▸ Xoá. Có hỏi xác nhận.

### 2.2 Workspace ▸ Cowork — trò chuyện với agent

Khung chat của project đang chọn. Có ô soạn tin, đính kèm tệp, chọn thư mục output,
và bảng **Lịch sử** hội thoại.

Link **Tất cả project…** ở mục GẦN ĐÂY trên thanh menu mở đúng khung này kèm bảng Lịch sử
— nơi có tìm kiếm, lọc, ghim, đổi tên và xoá nhiều đoạn chat cùng lúc. Đây cũng là màn
hình ứng dụng mở lên mặc định.

### 2.3 Workspace ▸ Co4E — xưởng luồng công việc

Canvas dạng đồ thị: kéo thả node, nối thành luồng, gán agent và skill cho từng bước, rồi
chạy. Có bảng thuộc tính node bên phải và khung chat riêng. Luồng lưu chung cho cả máy
(không thuộc một project).

### 2.4 Workspace ▸ Thư mục — duyệt và sửa tệp

Hai cột: cây thư mục và khung xem/sửa. Xem được tài liệu Office và PDF, sửa được tệp mã
nguồn có tô màu cú pháp. Có **AI Edit**: nhờ AI sửa nội dung tệp đang mở.

### 2.5 Workspace ▸ GraphRAG — bộ nhớ mã nguồn

Dựng đồ thị tri thức từ thư mục làm việc của project, rồi hỏi đáp trên đó.

---

## 3. Dashboard — thống kê sử dụng

Biểu đồ và thẻ số liệu: token đã dùng, chi phí ước tính, thói quen sử dụng theo thời gian.
Chọn được khoảng thời gian, nguồn (một task/phiên hoặc tất cả), và đơn vị tiền tệ.

⚠️ Đây là màn **chỉ xem số liệu**. Không tạo project, không tạo task ở đây.

---

## 4. Schedule Task — lịch trình

Hai cách nhìn: **Kanban** (theo cột trạng thái) và **Lịch** (theo ngày). Tạo và sửa task
định kỳ; task chạy nền kể cả khi màn này không mở.

---

## 5. Monitoring — giám sát

Màn này giữ dải tab riêng, có 8 mục:

| Mục | Nội dung |
|---|---|
| Tổng quan | Tóm tắt trạng thái hệ thống |
| Trạng thái Agent | Agent nào đang chạy, đã chạy gì |
| Công cụ | Bật/tắt công cụ, quản lý **Connectors (MCP)** |
| Nhật ký hành động | Lịch sử thao tác |
| Lịch sử gọi MCP | Từng lượt gọi máy chủ MCP |
| Sự kiện bảo mật | Cảnh báo và lệnh bị chặn |
| Agents Admin | Cấu hình các agent quản trị, gồm cả Trợ lý Hỗ trợ này |
| Icon | Bảng tra biểu tượng |

⚠️ **Connectors (MCP) nằm ở Monitoring ▸ Công cụ**, không nằm trong Cài đặt.

---

## 6. Cài đặt (nút ở thanh trên)

Hộp thoại 6 mục, chọn ở cột trái:

| Mục | Nội dung |
|---|---|
| Chung | Ngôn ngữ, giao diện, khay hệ thống, thư mục dùng chung |
| Nhà cung cấp AI | Chọn provider và model, nhập API key |
| Sandbox Security Layer | Chặn mạng, hỏi trước khi chạy lệnh, AI kiểm lệnh. **Khoá bằng mật khẩu** — phải bấm Unlock trước khi sửa được. Mật khẩu đặt qua biến môi trường `COWORK_SANDBOX_PASSWORD` |
| Parameter | Giới hạn token, số tệp đính kèm, giới hạn tài nguyên |
| Auto Model Routing | Tự chọn model theo chi phí/chất lượng |
| Giới thiệu | Tên, phiên bản, tác giả |

⚠️ Cài đặt **không có** mục quản lý project.

---

## 7. Những chỗ người dùng hay hỏi

**"Tôi tạo project ở đâu?"** → Workspace ▸ Project, nút **Project mới**.
Không phải Dashboard, không phải Cài đặt.

**"Sao tôi không sửa được project?"** → Biểu mẫu mặc định chỉ xem. Bấm **Sửa project**
(nút vàng) trước.

**"Sao không thấy tab Cowork?"** → Phải chọn một project trước; Cowork và GraphRAG bị ẩn
khi chưa có project.

**"Đổi API key ở đâu?"** → Cài đặt ▸ Nhà cung cấp AI.

**"Thêm MCP server ở đâu?"** → Monitoring ▸ Công cụ ▸ Connectors (MCP).

**"Đổi ngôn ngữ / giao diện?"** → Thanh trên cùng, hoặc Cài đặt ▸ Chung.

**"Mật khẩu Sandbox Security là gì?"** → Không có mật khẩu mặc định. Quản trị viên đặt qua
biến môi trường `COWORK_SANDBOX_PASSWORD`. Chưa đặt thì nhóm thiết lập đó luôn khoá.
