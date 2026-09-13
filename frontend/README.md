# Front End — Fresh Citrus AI Wellness

## Chạy local

```powershell
cd D:\Project\AI\frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Mặc định `NEXT_PUBLIC_APP_MODE=demo`, vì vậy toàn bộ hành trình có thể thử mà không cần Google, Geoapify hoặc khóa AI.

## Chế độ live

Đặt `NEXT_PUBLIC_APP_MODE=live` và `NEXT_PUBLIC_API_URL` trỏ về FastAPI. API `/v1/generations` cần được bật cùng Google OAuth, tài khoản và worker theo cấu hình backend trước khi dùng dữ liệu người thật.

Không đặt khóa Google, Geoapify hoặc AI trong biến `NEXT_PUBLIC_*`.
