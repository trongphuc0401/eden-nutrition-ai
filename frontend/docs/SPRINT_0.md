# Sprint 0 — Nền tảng kiểm thử frontend

Sprint 0 thiết lập cấu trúc và hợp đồng để các sprint sau thêm tính năng mà không trộn dữ liệu demo, logic giao diện và dữ liệu server vào cùng một component.

## Đã hoàn thành

- App Next.js 16, React 19, TypeScript strict và Tailwind CSS 4 trong `frontend/`.
- Tài liệu/ảnh tham chiếu được lưu trong `frontend/references/` để không phụ thuộc vào thư mục tạm.
- Token giao diện, focus state, reduced motion và khung responsive hiện có.
- Chế độ demo có nhãn rõ; `lib/api.ts` chọn demo hoặc API thật qua `NEXT_PUBLIC_APP_MODE`.
- Hợp đồng nhập hồ sơ/yêu cầu tạo tại `src/lib/contracts.ts`; lỗi API có cấu trúc `ApiProblem`.
- State machine cho vòng đời tạo công thức ở `src/features/generation/generation-machine.ts`.
- `Providers` dành cho TanStack Query đã có trong root layout, sẵn sàng cho truy vấn hồ sơ, nguyên liệu và lịch sử ở Sprint 1.
- Vitest kiểm thử các trạng thái chạy, review, chặn, dừng và lỗi của state machine.

## Hợp đồng đang đóng băng cho Sprint 1

`POST /v1/generations` nhận `{ profile, ingredientIds, prompt? }`. Ở chế độ live, UI chỉ gọi API qua adapter. Adapter không đặt quy tắc dinh dưỡng, không chuyển lỗi kỹ thuật thô ra người dùng.

`GET /v1/ingredients?month=…` trả `{ items }`. Sprint 1 sẽ thay emoji mặc định bằng media có nguồn và đưa khu vực/tháng từ trạng thái người dùng vào truy vấn.

## Chưa thuộc Sprint 0

- Google OAuth, cookie server-side, quyền sở hữu và lưu bản nháp.
- Geoapify/GPS, danh mục tỉnh thành đầy đủ và dữ liệu mùa vụ thật trong giao diện.
- Worker, polling tác vụ bền vững, hủy tác vụ thật, lịch sử/lưu công thức bền vững.
- Đối chiếu pixel screenshot tự động và Playwright end-to-end.

## Kiểm tra local

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

Chạy demo: `npm run dev`, sau đó mở `http://localhost:3000`. Dùng `.env.example` để chuyển sang live; không bật live trước khi API triển khai session và ownership ở Sprint 1.
