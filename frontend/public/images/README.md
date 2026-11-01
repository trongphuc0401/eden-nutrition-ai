# Ảnh nội dung

Các file `.svg` ở đây là ảnh tạm. Để thay bằng ảnh chụp thật:

1. Đặt ảnh vào thư mục này, ví dụ `report-cover.jpg`.
2. Đổi `src` tương ứng trong `src/lib/images.ts`.
3. Giữ đúng tỉ lệ khung để bố cục không bị lệch.

| Khung | File tạm | Tỉ lệ | Hiển thị ở |
|---|---|---|---|
| `reportCover` | `report-cover.svg` | 12:5 (1200×500) | Đầu báo cáo công thức |
| `emptyHistory` | `empty-history.svg` | 3:2 (480×320) | Trang Lịch sử khi chưa có dữ liệu |
| `emptySaved` | `empty-saved.svg` | 3:2 (480×320) | Trang Công thức đã lưu khi chưa có dữ liệu |
| `processing` | `processing.svg` | 3:2 (480×320) | Khung AI đang tạo báo cáo |

Ảnh chụp nên nén dưới 300 KB (JPG/WebP). `next/image` sẽ tự tối ưu kích thước.
