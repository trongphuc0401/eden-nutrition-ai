import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings
from app.schemas.api_schema import (
    DemoProfileResponse,
    FrontendBootstrapResponse,
    FrontendEndpointResponse,
)
from app.schemas.profile_schema import NutritionGoal


def _demo_profiles_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "demo_profiles_seed.json"


@lru_cache(maxsize=1)
def load_demo_profiles() -> list[DemoProfileResponse]:
    path = _demo_profiles_path()
    with path.open(encoding="utf-8") as file:
        rows: list[dict[str, Any]] = json.load(file)
    return [DemoProfileResponse.model_validate(row) for row in rows]


def build_frontend_bootstrap() -> FrontendBootstrapResponse:
    return FrontendBootstrapResponse(
        app_name=settings.app_name,
        research_goal="overweight_obesity_weight_management",
        goal_options=list(NutritionGoal.__args__),
        gender_options=["nữ", "nam", "khác"],
        sample_profiles=load_demo_profiles(),
        endpoints=[
            FrontendEndpointResponse(
                method="GET",
                path="/system-status",
                purpose="Kiểm tra trạng thái AI, database, vector search, dữ liệu fallback và guardrail.",
            ),
            FrontendEndpointResponse(
                method="POST",
                path="/profiles/analyze",
                purpose="Phân tích BMI, phạm vi nghiên cứu và các ràng buộc trước khi tạo sinh tố.",
            ),
            FrontendEndpointResponse(
                method="POST",
                path="/knowledge/search-preview",
                purpose="Xem trước tri thức RAG hoặc dữ liệu mẫu được dùng để tạo công thức.",
            ),
            FrontendEndpointResponse(
                method="POST",
                path="/smoothies/generate-and-evaluate",
                purpose="Tạo một công thức sinh tố và đánh giá ngay dinh dưỡng/an toàn.",
            ),
            FrontendEndpointResponse(
                method="POST",
                path="/smoothies/evaluate",
                purpose="Đánh giá một công thức có sẵn mà không cần gọi AI tạo mới.",
            ),
        ],
        recommended_flow=[
            "Gọi /frontend/bootstrap để lấy cấu hình form và hồ sơ mẫu.",
            "Gọi /system-status để hiển thị trạng thái sẵn sàng của hệ thống.",
            "Cho người dùng chọn hoặc chỉnh sửa một hồ sơ mẫu.",
            "Gọi /profiles/analyze trước khi bật nút tạo sinh tố.",
            "Gọi /smoothies/generate-and-evaluate nếu hồ sơ nằm trong phạm vi nghiên cứu.",
            "Hiển thị quyết định đánh giá, điểm, vấn đề, khuyến nghị và cảnh báo an toàn.",
        ],
        notes=[
            "Hệ thống cố ý chặn tạo sinh tố khi BMI dưới 25 vì phạm vi nghiên cứu là thừa cân/béo phì.",
            "Nếu vector_search là fallback_only, backend vẫn chạy bằng dữ liệu mẫu nội bộ.",
            "Ghi chú sức khỏe chỉ là bối cảnh cần xem xét, không phải chẩn đoán y khoa.",
        ],
    )
