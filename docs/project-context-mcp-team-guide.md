# Project Context MCP — hướng dẫn làm song song

Mục tiêu: hoàn thiện ba tool trên **cùng một server** `project_context`. Không tạo server, registry,
policy hay error envelope mới. Shared skeleton đã khóa sẵn thứ tự an toàn:

```text
validate input → policy ALLOW → resolve provider → gọi upstream → validate output
```

## Chia việc

| Người | Tool | Chỉ sửa | Branch đề xuất |
|---|---|---|---|
| Member A | `get_project_issue_context` | `tools/issue_context.py`, `providers/issue.py`, test riêng | `feat/mcp-issue-context` |
| Member B | `search_project_knowledge` | `tools/knowledge_search.py`, `providers/knowledge.py`, test riêng | `feat/mcp-knowledge-search` |
| Member C | `get_project_change_context` | `tools/change_context.py`, `providers/change.py`, test riêng | `feat/mcp-change-context` |

Trước khi gửi task, thay `Member A/B/C` bằng username thật trên ba issue. Mỗi người **không sửa**
`foundation.py`, `registry.py`, `runtime.py`, `server.py` hoặc file của người khác. Nếu shared contract
cần đổi, mở một PR nhỏ riêng và để cả ba người rebase sau khi PR đó merge.

## Bắt đầu trong 5 phút

1. Chạy `python --version` và xác nhận Python 3.11+ như baseline trong `requirements.txt`.
2. Tạo branch từ commit template chứa tài liệu này sau khi PR template merge.
3. Đọc input/output model trong module tool được giao; không thêm field riêng của Gitea/Jira/Redmine.
4. Implement provider read-only trong module `providers/<tool>.py`; credential chỉ lấy sau policy ALLOW.
5. Thêm test happy, invalid, not-found, timeout, DENIED với `resolver.calls == 0`, output sai schema,
   truncation/cursor và source mở được có `revision`.
6. Chạy:

   ```bash
   python -m pytest tests/test_project_context_mcp_template.py tests/test_project_context_<tool>.py -q
   ```

   Lệnh trên chạy trực tiếp từ root repo `cowork_local`; `tests/conftest.py` đã thiết lập import path.

## Definition of Done của từng người

- Tool trả đúng schema, có `project_id` và source gồm `system`, `url`, `revision`, `retrieved_at`.
- Provider-neutral: đổi Gitea sang GitHub/Jira/Redmine không đổi schema hay tool name.
- Sai project bị `DENIED` trước khi resolve credential và trước mọi upstream call.
- Không log/return token; lỗi ngoài dự kiến không lộ exception; read không có side effect.
- Output lớn có `truncated`, `returned`, `remaining`, `next_cursor`; không cắt im lặng.
- Test riêng pass, test shared pass, PR chỉ chạm đúng vùng sở hữu trong bảng trên.

## Chạy server sau khi provider đã cấu hình

```bash
COWORK_MCP_ACTOR_ID=<actor> \
COWORK_MCP_ORG_UNIT=<org> \
COWORK_MCP_CUSTOMER=<customer> \
COWORK_MCP_PROJECT=<project> \
GITEA_BASE_URL=<https://gitea.example> \
GITEA_TOKEN=<service-account-token> \
PROJECT_CONTEXT_REPO_MAP='{"<org>/<customer>/<project>":"<owner>/<repo>"}' \
PROJECT_CONTEXT_KNOWLEDGE_ROOT=<path chứa 1 thư mục con cho mỗi project> \
python -m cowork_local.mcp_servers.project_context_server
```

Target map ưu tiên key đủ `org_unit/customer/project`; key `project` chỉ là legacy fallback cho pilot
env cũ. Không commit giá trị môi trường hoặc credential. Cowork kết nối bằng stdio với command Python
và args `-m cowork_local.mcp_servers.project_context_server`.

## Knowledge search (`search_project_knowledge`)

Corpus là workspace của chính project: `PROJECT_CONTEXT_KNOWLEDGE_ROOT/<identity.project>` — cùng
định nghĩa "knowledge" mà `core/projects.py` đã dùng (file ở workspace root), và tái sử dụng
`core/doc_extract.py` để đọc docx/pptx/xlsx/pdf/text. Không thêm vector DB, embedding pipeline hay
RAG framework mới.

- Thư mục được resolve từ **identity**, không bao giờ từ `project_id` trong request; `project_id`
  chỉ dùng để verify scope. Symlink trỏ ra ngoài workspace bị loại.
- `score` là term-coverage (lexical), không phải similarity giả. Upgrade path: thay riêng
  `_score_chunk` bằng semantic ranker khi corpus đủ lớn.
- Bound theo `detail`: `summary` 3 kết quả / 200 ký tự, `standard` 5 / 600, `full` 10 / 1200.
  `top_k` chỉ thu hẹp, không nới rộng. Không có unlimited mode.
