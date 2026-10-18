# Lỗi thường gặp và cách kiểm tra

## Report bị `review`

Mở state ở node `safety_and_quality_gate`. Kiểm tra `missing_data`, `data_coverage` và `thresholds`. `review` không phải lỗi hệ thống; PDF vẫn được tạo kèm cảnh báo.

## Report bị `reject` và không có PDF

Xem `errors` sau `validate_request`/`analyze_profile`. Dị ứng trùng nguyên liệu và hồ sơ rủi ro cao không retry. Đây là hành vi mong muốn.

## UI không tiến bước

Kiểm tra `GET /v1/reports/{id}` có thay đổi `current_node` hay không, rồi mở `/events`. Frontend live dùng node thực để ánh xạ bảy bước, không có timer tăng giả. Nếu backend restart, job store demo mất và trả 404.

## Agent Server không tìm thấy graph

Chạy lệnh trong thư mục `backend`, bảo đảm đã cài `requirements-report.txt`, và kiểm tra `langgraph.json` trỏ đến `./app/agents/report_graph.py:report_graph`.

## PDF có hơn hai trang hoặc lỗi glyph

Renderer dùng canvas cố định hai trang, giới hạn 8 nguyên liệu/6 bước/6 nguồn. Chạy test page count, trích text bằng `pypdf`, render PNG bằng Poppler rồi xem cả hai trang. Font ưu tiên Poppins/Playfair nếu máy có; fallback Arial/Georgia trên Windows vẫn hỗ trợ tiếng Việt.

## Số liệu không khớp

So sánh lần lượt `source_per_100g`, định lượng, số khẩu phần và bảng `ingredient_nutrition`. Không sửa số trực tiếp trong PDF. Golden test trong `backend/tests/test_report_graph.py` sẽ bắt sai lệch phép tính.

## Cách đọc trace trong Studio

1. Chọn đúng thread/run.
2. Xem output từng node, không chỉ state cuối.
3. Xác nhận ingredient IDs từ request còn nguyên tới `recipe_draft` và `report_document`.
4. Với lỗi provider có retry, xem số lần chạy node. Với validation/allergy, phải chỉ chạy một lần và rẽ `finalize_error`.
5. Nếu node trả quá nhiều state, sửa node để chỉ trả các key nó cập nhật.
