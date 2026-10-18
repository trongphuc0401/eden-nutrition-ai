# Cấu hình Z.AI cho report

Z.AI chỉ tạo nội dung tiếng Việt của report: tên sinh tố, các bước, cách dùng, thay thế và phần diễn giải. Định lượng, thành phần hiển thị, phép tính macro, ngưỡng và safety gate vẫn do workflow local quyết định.

Tạo hoặc cập nhật `backend/.env` — không đặt key trong `.env.example` hay frontend:

```env
LLM_PROVIDER=zai
ZAI_API_KEY=<API-key-của-bạn>
ZAI_MODEL=glm-4.7-flash
ZAI_BASE_URL=https://api.z.ai/api/paas/v4
```

Khởi động lại FastAPI sau khi đổi `.env`. Nếu dùng Z.AI Coding Plan thay vì API resource package/balance, đổi `ZAI_BASE_URL` thành `https://api.z.ai/api/coding/paas/v4`; với API tổng quát, dùng endpoint `/api/paas/v4`. Đây là hai endpoint OpenAI-compatible được Z.AI công bố. [Z.AI endpoint guide](https://zcode.z.ai/en/docs/configuration)

Nếu Z.AI timeout, trả JSON sai hoặc không có key, node vẫn dùng nội dung deterministic local và không bịa số dinh dưỡng. Kiểm tra bằng:

```powershell
$env:PYTHONPATH = "D:\Project\AI\backend"
.\.venv\Scripts\python.exe -m unittest backend.tests.test_zai_report_service -v
```
