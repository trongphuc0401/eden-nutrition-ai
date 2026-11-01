# Hướng dẫn chạy local

## 1. Cài dependency

Từ thư mục gốc dự án trên Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-report.txt
cd frontend
npm install
```

## 2. Chạy FastAPI gateway

Chạy migration report job trước khi bật persistence:

```powershell
Get-Content backend\migrations\0002_report_jobs.sql | psql $env:DATABASE_URL
```

Trong `backend/.env`, dùng `REPORT_RECIPE_MODE=mock` cho test local không gọi model. Để chạy Z.AI thật:

```text
REPORT_RECIPE_MODE=zai
ZAI_API_KEY=<đặt trong .env, không commit>
ZAI_MODEL=glm-4.7-flash
REPORT_JOB_PERSISTENCE_ENABLED=true
```

```powershell
$env:PYTHONPATH = "D:\Project\AI\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Swagger ở `http://localhost:8000/docs`. Luồng API:

1. `POST /v1/reports`
2. theo dõi `GET /v1/reports/{report_id}` hoặc SSE `/events`
3. nếu `awaiting_confirmation`, gọi `POST /v1/reports/{report_id}/confirmation`
4. tải `/pdf` khi trạng thái là `completed` hoặc `review`
5. `POST /cancel` để yêu cầu dừng run.

## 3. Chạy Agent Server và Studio

```powershell
cd backend
..\.venv\Scripts\langgraph.exe dev --config langgraph.json
```

Mở URL Studio do CLI in ra. Chọn graph `nutrition_report`, dán request/state mẫu trong [example-state.md](example-state.md), rồi xem `updates` của từng node. Agent Server quản lý thread/checkpoint cho chế độ này; FastAPI job store chỉ phục vụ demo local và sẽ mất khi restart.

## 4. Chạy frontend

Tạo `frontend/.env.local`:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Sau đó:

```powershell
cd frontend
npm run dev
```

## 5. Kiểm thử

```powershell
$env:PYTHONPATH = "D:\Project\AI\backend"
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
$env:PYTHONPATH = "D:\Project\AI\backend"
.\.venv\Scripts\python.exe backend\scripts\run_report_evals.py
cd frontend
npm run typecheck
npm run lint
npm test
```

PDF demo được ghi vào `output/pdf/`; ảnh QA nằm tạm ở `tmp/pdfs/`. Không dùng dữ liệu demo này như tư vấn y khoa.
