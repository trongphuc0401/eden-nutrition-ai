# Ví dụ request và state

## Request

```json
{
  "profile": {
    "age": 32,
    "gender": "Nữ",
    "height_cm": 165,
    "weight_kg": 75,
    "goal": "overweight_obesity_weight_management",
    "allergies": [],
    "preferred_food_types": ["Nhiều chất xơ"],
    "disliked_ingredients": [],
    "medical_notes": ""
  },
  "ingredientIds": ["cam", "sua-dau-nanh", "yen-mach", "hat-chia"],
  "servings": 1,
  "prompt": "Bữa phụ no lâu",
  "locale": "vi-VN"
}
```

## State tăng dần

1. Khởi tạo: có request, `report_id`, `thread_id`, `run_id`.
2. Sau validate: `selected_ingredients` chứa đúng bốn ID cùng nguồn; `errors=[]`.
3. Sau retrieve: `ingredient_data` có calories/protein/carb/fat/fiber/sugar/sodium trên 100 g. Giá trị không biết là `null`.
4. Sau recipe: `recipe_draft` có định lượng và tối đa sáu bước.
5. Sau calculate: `nutrition_calculation` có tổng mỗi khẩu phần, bảng đóng góp, coverage và ngưỡng.
6. Sau gate: `decision` là `pass`, `review` hoặc `reject`. `reject` đi thẳng tới `finalize_error` và không có file.
7. Sau compose: `report_document` là contract renderer-independent.
8. Sau render: `pdf_metadata` có đường dẫn tuyệt đối, SHA-256, kích thước và `page_count=2`.

Với dữ liệu demo hiện tại, request trên cho khoảng `264.67 kcal`, `11.96 g protein`, `35.34 g carbohydrate`, `8.62 g fat`, `9.13 g fiber`, `12.27 g sugar` và `72.22 mg sodium` mỗi khẩu phần. Golden test khóa các giá trị quan trọng này.

## Ba nhánh kết quả

- `pass`: đủ dữ liệu và đạt toàn bộ ngưỡng demo; tạo PDF.
- `review`: thiếu dữ liệu hoặc có ngưỡng cần xem lại; vẫn tạo PDF, warning/assumption hiển thị rõ.
- `reject`: validation, xung đột dị ứng hoặc hồ sơ rủi ro cao; không tạo PDF.
