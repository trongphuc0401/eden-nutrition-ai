# AI dinh dưỡng tạo PDF 2 trang

Thư mục này là điểm bắt đầu cho người mới. MVP hiện tại là **workflow một lượt**, không phải chatbot: nhận hồ sơ và nguyên liệu đã chọn, tạo một report rồi kết thúc. Mỗi lần chạy vẫn có `thread_id`, `run_id` và `report_id` để sau này có thể bổ sung checkpoint/chat mà không đổi hợp đồng report.

## Nên đọc theo thứ tự

1. [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview): LangGraph điều phối các bước có state.
2. [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents): dự án hiện là workflow cố định, chưa phải agent tự quyết định công cụ.
3. [Thinking in LangGraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph): cách chia node, state và lỗi.
4. [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api): cách `StateGraph`, edge và conditional edge hoạt động.
5. [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [Application structure](https://docs.langchain.com/oss/python/langgraph/application-structure), [Streaming](https://docs.langchain.com/oss/python/langgraph/streaming) và [Testing](https://docs.langchain.com/oss/python/langgraph/test).

Sau đó đọc lần lượt [architecture.md](architecture.md), [example-state.md](example-state.md), [runbook.md](runbook.md), [zai-setup.md](zai-setup.md) và [troubleshooting.md](troubleshooting.md).

## Từ điển ngắn

- **State**: hồ sơ làm việc của một lần chạy; chứa request gốc, dữ liệu nguồn, công thức, phép tính, cảnh báo và metadata PDF.
- **Node**: một bước nghiệp vụ nhận state và chỉ trả về phần cần cập nhật.
- **Edge**: đường chạy cố định từ node này sang node khác.
- **Conditional edge**: rẽ nhánh theo `pass`, `review` hoặc `reject`.
- **Thread**: định danh chuỗi state có thể tiếp tục trong tương lai. MVP có một run/report trong mỗi thread.
- **Run**: một lần thực thi graph.
- **Checkpoint**: ảnh chụp state giữa các bước. Agent Server quản lý persistence; graph in-process của FastAPI hiện dùng job store bộ nhớ cho demo.

## Điểm vào mã nguồn

- Graph: `backend/app/agents/report_graph.py`
- State: `backend/app/agents/report_state.py`
- Contract: `backend/app/schemas/report_schema.py`
- Tính dinh dưỡng: `backend/app/services/report_calculation_service.py`
- Renderer: `backend/app/services/pdf_report_service.py`
- API/job/SSE: `backend/app/api/report_routes.py`, `backend/app/services/report_job_service.py`
- Agent Server config: `backend/langgraph.json`
- Frontend adapter: `frontend/src/lib/report-api.ts`

## Ranh giới MVP

Không có chat, chỉnh sửa đa lượt, `interrupt()`, đăng nhập thật, memory dài hạn, chia sẻ công khai hay LangSmith Cloud. Form yêu cầu bổ sung chỉ là input cho lần tạo report mới. Chẩn đoán y khoa không nằm trong phạm vi sản phẩm.
