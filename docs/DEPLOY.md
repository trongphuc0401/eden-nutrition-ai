# Deploy production: Vercel (frontend) + Render (backend + Postgres)

```
Trình duyệt ──► https://<app>.vercel.app          (Next.js, Vercel)
                   └─ /api/*  ──proxy──►  https://fresh-citrus-api.onrender.com   (FastAPI, Docker)
                                              ├─ Postgres + pgvector (Render)
                                              └─ Disk /var/data/pdf (PDF report)
```

Frontend gọi backend qua `/api` trên cùng domain Vercel (cấu hình `rewrites` trong `frontend/next.config.ts`).
Cookie đăng nhập vì vậy là first-party, không bị trình duyệt chặn.

## Chạy frontend Vercel với backend local qua ngrok

Phù hợp để demo hoặc phát triển khi backend chưa được deploy. Vercel proxy `/api/*` tới URL HTTPS của ngrok, do đó frontend vẫn dùng cùng-origin `/api` và không đưa URL tunnel vào mã nguồn.

1. Chạy backend local trên cổng 8000, rồi mở tunnel: `ngrok http 8000`.
2. Sao chép URL `https://...ngrok-free.app` mà ngrok cấp.
3. Trong Vercel, đặt biến **Production** cho project (Root Directory: `frontend`):

| Biến | Giá trị |
| --- | --- |
| `BACKEND_URL` | URL HTTPS của ngrok, không có dấu `/` cuối |
| `NEXT_PUBLIC_APP_MODE` | `live` |
| `NEXT_PUBLIC_API_URL` | `/api` |

4. Redeploy frontend sau khi đổi biến; `BACKEND_URL` được Next.js đọc khi build để tạo rewrite.

Nếu dùng Google sign-in, trong `backend/.env` đặt `FRONTEND_URL` và `GOOGLE_REDIRECT_URI` theo URL Vercel (`https://<app>.vercel.app` và `https://<app>.vercel.app/api/v1/auth/google/callback`), đồng thời thêm URL đó vào Google OAuth. Khi FastAPI chạy local nhưng được Vercel gọi qua tunnel, đặt thêm `SESSION_COOKIE_SECURE=true` để cookie đăng nhập chỉ đi qua HTTPS. Để demo không cần đăng nhập, đặt `NEXT_PUBLIC_APP_MODE=demo` và không cần tunnel.

> URL ngrok miễn phí thường thay đổi khi khởi động lại. Sau mỗi lần URL đổi, cập nhật `BACKEND_URL` trên Vercel và redeploy. Không gửi `backend/.env` hay token ngrok lên Git.

## 1. Google OAuth client

Google Cloud Console → APIs & Services → Credentials → *Create OAuth client ID* (Web application):

- Authorized JavaScript origins: `https://<app>.vercel.app`, `http://localhost:3000`
- Authorized redirect URIs:
  - `https://<app>.vercel.app/api/v1/auth/google/callback`
  - `http://localhost:3000/api/v1/auth/google/callback`
- OAuth consent screen: chọn *External*, thêm scope `openid`, `email`, `profile`. Khi còn ở chế độ *Testing* chỉ test users đăng nhập được — bấm *Publish app* trước khi mở cho mọi người.

## 2. Backend trên Render

1. Push branch lên GitHub.
2. Render → *New* → *Blueprint* → chọn repo. Render đọc `render.yaml`, tạo `fresh-citrus-api` + `fresh-citrus-db`.
3. Điền các biến `sync: false`:

| Biến | Giá trị |
| --- | --- |
| `ZAI_API_KEY` | key Z.ai (key mới, đã rotate) |
| `LLM_API_KEY` | key cho endpoint smoothie cũ (có thể dùng lại key Z.ai) |
| `EMBEDDING_API_KEY` | key Gemini cho embedding/RAG |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | từ bước 1 |
| `GOOGLE_REDIRECT_URI` | `https://<app>.vercel.app/api/v1/auth/google/callback` |
| `FRONTEND_URL` | `https://<app>.vercel.app` |
| `CORS_ALLOW_ORIGINS` | `https://<app>.vercel.app` |

`SESSION_SECRET` được Render tự sinh. Mỗi lần deploy, `python scripts/migrate.py` chạy trước (tạo extension `vector`, bảng, áp `migrations/*.sql`).

4. Seed dữ liệu trái cây + embedding một lần (Render → service → *Shell*):

```bash
python scripts/import_vietnamese_fruit_data.py
```

5. Kiểm tra: `https://fresh-citrus-api.onrender.com/health` và `/system-status`.

> Nếu muốn dùng Supabase (DB đang dùng ở local) thay cho Render Postgres: xoá khối `databases` và `fromDatabase` trong `render.yaml`, đặt `DATABASE_URL` là connection string Supabase.

Backend từ chối khởi động khi `APP_ENV=production` mà thiếu `SESSION_SECRET` / Google / `ZAI_API_KEY`, hoặc còn `REPORT_RECIPE_MODE=mock`.

## 3. Frontend trên Vercel

Vercel → *Add New Project* → chọn repo → **Root Directory: `frontend`**. Environment Variables:

| Biến | Giá trị |
| --- | --- |
| `BACKEND_URL` | `https://fresh-citrus-api.onrender.com` |
| `NEXT_PUBLIC_APP_MODE` | `live` |
| `NEXT_PUBLIC_API_URL` | `/api` |

`NEXT_PUBLIC_*` được gắn lúc build, nên sau khi đổi giá trị cần *Redeploy*.

## 4. Kiểm tra sau deploy

- Mở `https://<app>.vercel.app` → *Tiếp tục với Google* → quay lại workspace với avatar Google.
- Tạo report → theo dõi các bước → *Tải PDF 2 trang* (kiểm tra dấu tiếng Việt).
- `https://<app>.vercel.app/api/v1/auth/me` khi chưa đăng nhập → 401.
- Mở report bằng tài khoản khác → 404.
- Restart service trên Render → report cũ vẫn mở và tải PDF được.

## Ghi chú

- Build local trên Git Bash (Windows): đừng truyền `NEXT_PUBLIC_API_URL=/api` trên dòng lệnh vì MSYS đổi nó thành `C:/Program Files/Git/api`. Bỏ trống thì mặc định đã là `/api`.
- Giới hạn tạo report: `REPORT_RATE_LIMIT_PER_HOUR` (mặc định 10/người/giờ).
- Backend chạy 1 worker vì hàng đợi report nằm trong process; trạng thái job được lưu vào Postgres.
