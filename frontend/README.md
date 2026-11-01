# Front End — Fresh Citrus AI Wellness

## Chạy local

```powershell
cd D:\Project\AI\frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Ứng dụng luôn gọi FastAPI qua `/api`: danh mục nguyên liệu, dị ứng, chat và báo cáo đều lấy từ API, không có dữ liệu mẫu trong frontend. Cần chạy backend và đăng nhập Google để vào khung làm việc.

## Kết nối backend

Đặt `BACKEND_URL` trỏ về FastAPI (giữ `NEXT_PUBLIC_API_URL=/api` để cookie đăng nhập đi qua proxy). API `/v1/generations` cần được bật cùng Google OAuth, tài khoản và worker theo cấu hình backend trước khi dùng dữ liệu người thật.

Không đặt khóa Google, Geoapify hoặc AI trong biến `NEXT_PUBLIC_*`.
