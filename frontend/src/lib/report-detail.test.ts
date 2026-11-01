import { describe, expect, it } from "vitest";
import { buildReportDetail, nutrientKey, rangeStatus, referenceShare, type DocumentDetail } from "./report-detail";

// The smoothie from the design mock-up, with totals recalculated from its ingredient table.
const sampleDocument: DocumentDetail = {
  created_at: "2026-09-20T03:00:00Z",
  servings: 1,
  totals: { calories: 299, protein: 10.9, carbohydrate: 52.4, fat: 6.7, fiber: 13.6, sugar: 23.1, sodium: 60 },
  ingredients: [
    { name: "Ổi", amount: 120, unit: "g", season: { status: "in_season", months: [8, 9, 10, 11] } },
    { name: "Thanh long ruột đỏ", amount: 100, unit: "g", season: { status: "in_season", months: [6, 7, 8, 9] } },
    { name: "Cải bó xôi", amount: 30, unit: "g", season: { status: "out_of_season", months: [1, 2, 3, 11, 12] } },
    { name: "Yến mạch", amount: 20, unit: "g", season: { status: "not_seasonal", months: [] } },
    { name: "Sữa yến mạch không đường", amount: 150, unit: "ml", season: { status: "not_seasonal", months: [] }, substitution_for: "sữa bò" },
    { name: "Hạt chia", amount: 5, unit: "g", season: { status: "not_seasonal", months: [] } },
  ],
  ingredient_nutrition: [{ ingredient_id: "oi", name: "Ổi", nutrition: { calories: 81.6 } }],
  thresholds: [
    { nutrient: "Năng lượng", value: 299, unit: "kcal", minimum: 120, maximum: 420, status: "pass" },
    { nutrient: "Protein", value: 10.9, unit: "g", minimum: 5, maximum: null, status: "pass" },
    { nutrient: "Đường tổng", value: 23.1, unit: "g", minimum: null, maximum: 28, status: "pass" },
    { nutrient: "Natri", value: 60, unit: "mg", minimum: null, maximum: 500, status: "pass" },
  ],
  reference_ranges: [
    { nutrient: "calories", unit: "kcal", minimum: 165, maximum: 248, basis: "Mục tiêu cá nhân" },
    { nutrient: "carbohydrate", unit: "g", minimum: 33.6, maximum: 48.6, basis: "AMDR" },
    { nutrient: "fat", unit: "g", minimum: 6.6, maximum: 11.6, basis: "AMDR" },
  ],
  profile_snapshot: { gender: "Nữ", age: 34, bmi: 35, bmi_category: "Béo phì độ II (ngưỡng châu Á)", allergies: ["đậu phộng", "sữa bò"], preferences: ["chua ngọt"] },
  scores: { personal_fit: { value: 75, breakdown: [{ label: "Năng lượng ngoài mục tiêu cá nhân", points: -10 }] }, seasonal: 90, season_month: 9 },
  allergen_check: { checked: ["đậu phộng", "sữa bò"], conflicts: [], checked_ingredients: 6 },
  steps: [{ title: "Xay nhuyễn", detail: "Xay 45–60 giây đến khi mịn.", minutes: 1, kind: "blend" }],
  prep_minutes: 7,
  serving_ml: 430,
  meal_context: "Bữa phụ",
};

describe("report detail", () => {
  it("maps threshold labels to nutrient keys", () => {
    expect(nutrientKey("Đường tổng")).toBe("sugar");
    expect(nutrientKey("Năng lượng")).toBe("calories");
    expect(nutrientKey("Chất xơ")).toBe("fiber");
    expect(nutrientKey("carbohydrate")).toBe("carbohydrate");
  });

  it("grades a value against its range", () => {
    expect(rangeStatus(10, 5, null)).toBe("in");
    expect(rangeStatus(30, null, 28)).toBe("slightly_high");
    expect(rangeStatus(40, null, 28)).toBe("high");
    expect(rangeStatus(2, 3, null)).toBe("low");
    expect(rangeStatus(null, 3, null)).toBe("unknown");
  });

  it("prefers the personal range and keeps research thresholds for the rest", () => {
    const detail = buildReportDetail(sampleDocument)!;
    const byKey = Object.fromEntries(detail.nutrients.map((row) => [row.key, row]));
    expect(byKey.calories).toMatchObject({ min: 165, max: 248, status: "high" });
    expect(byKey.carbohydrate.status).toBe("slightly_high");
    expect(byKey.sugar).toMatchObject({ max: 28, status: "in" });
    expect(byKey.fiber.status).toBe("unknown");
    expect(referenceShare(byKey.sodium)).toBe(12);
  });

  it("carries scores, seasons and substitutions", () => {
    const detail = buildReportDetail(sampleDocument)!;
    expect(detail.month).toBe(9);
    expect(detail.seasonalScore).toBe(90);
    expect(detail.ingredients[0].kcal).toBe(82);
    expect(detail.ingredients[4].substitutionFor).toBe("sữa bò");
  });

  it("returns null for reports made before the personalised fields existed", () => {
    expect(buildReportDetail({ created_at: "2026-01-01", totals: {}, ingredients: [] })).toBeNull();
  });
});
