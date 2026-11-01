import type { Ingredient, Profile, Report } from "./types";

export const defaultProfile: Profile = {
  age: 28, gender: "Nữ", heightCm: 162, weightKg: 76, hometown: "TP. Hồ Chí Minh", activityLevel: "light",
  allergies: [], dislikes: [], preferences: [], notes: "",
  healthRestrictionStatus: "no",
};

export const ingredients: Ingredient[] = [
  { id: "oi", name: "Ổi", emoji: "🍐", seasonal: "in", region: "Đồng bằng sông Cửu Long", kind: "fruit" },
  { id: "buoi", name: "Bưởi", emoji: "🍊", seasonal: "in", region: "Đồng bằng sông Cửu Long", kind: "fruit" },
  { id: "chom-chom", name: "Chôm chôm", emoji: "🍒", seasonal: "in", region: "Đồng bằng sông Cửu Long", kind: "fruit" },
  { id: "dua-hau", name: "Dưa hấu", emoji: "🍉", seasonal: "out", region: "Đồng bằng sông Cửu Long", kind: "fruit" },
  { id: "dua", name: "Dứa", emoji: "🍍", seasonal: "unknown", region: "Nhiều vùng", kind: "fruit" },
  { id: "mang-cau", name: "Mãng cầu xiêm", emoji: "🥭", seasonal: "unknown", region: "Nam Bộ", kind: "fruit" },
  { id: "sua-dau-nanh", name: "Sữa đậu nành không đường", emoji: "🥛", seasonal: "unknown", region: "Nguyên liệu phụ", kind: "support" },
  { id: "yen-mach", name: "Yến mạch", emoji: "🌾", seasonal: "unknown", region: "Nguyên liệu phụ", kind: "support" },
  { id: "hat-chia", name: "Hạt chia", emoji: "🫘", seasonal: "unknown", region: "Nguyên liệu phụ", kind: "support" },
];

export const demoReport: Report = {
  id: "demo-oi-xanh", name: "Sinh tố ổi xanh giàu chất xơ", createdAt: "Hôm nay, 10:24", saved: false, decision: "review", version: 1,
  ingredients: [
    { name: "Ổi", amount: "120 g", purpose: "Bổ sung chất xơ và vitamin C", used: true },
    { name: "Sữa đậu nành không đường", amount: "200 ml", purpose: "Tăng protein thực vật, không chứa sữa", used: true },
    { name: "Yến mạch", amount: "20 g", purpose: "Tạo độ no và kết cấu", used: true },
    { name: "Hạt chia", amount: "5 g", purpose: "Bổ sung chất xơ", used: true },
    { name: "Bưởi", amount: "—", purpose: "Đã chọn nhưng không dùng để giữ vị dễ uống", used: false },
  ],
  nutrition: { calories: 253, protein: 12.4, carbs: 36.8, fat: 6.2, fiber: 9.6, sugar: 12.1 },
  tools: ["Máy xay sinh tố", "Ly định lượng", "Dao và thớt"],
  steps: ["Rửa sạch ổi, bỏ hạt cứng rồi cắt nhỏ.", "Cho sữa đậu nành, ổi, yến mạch và hạt chia vào máy xay.", "Xay 45–60 giây đến khi mịn. Thêm đá hoặc nước lạnh theo khẩu vị.", "Dùng ngay sau khi xay để giữ hương vị tươi."],
  reason: "Công thức ưu tiên ổi và yến mạch để tăng chất xơ, kết hợp protein thực vật. Không thêm đường, sữa bò hoặc chuối theo hồ sơ của bạn.",
  warning: "Cần xem xét: bạn có ghi chú về đường huyết. Không thêm đường, siro hoặc sữa đặc. Đây là gợi ý dinh dưỡng, không thay thế tư vấn y tế.",
  sources: ["Dữ liệu thành phần dinh dưỡng trái cây Việt Nam", "WHO — Healthy diet (2026)"],
  qualityLabel: "Bản thử nghiệm nội bộ – chưa được chuyên gia dinh dưỡng thẩm định.", aiProvider: "mock", aiModel: "demo",
};
