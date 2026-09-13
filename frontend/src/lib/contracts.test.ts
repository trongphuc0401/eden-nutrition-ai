import { describe, expect, it } from "vitest";
import { generationInputSchema, profileSchema } from "./contracts";

const profile = {
  age: 28, gender: "Nữ", heightCm: 162, weightKg: 76, hometown: "TP. Hồ Chí Minh",
  allergies: [], dislikes: [], preferences: [], notes: "",
};

describe("frontend contracts", () => {
  it("accepts the generation payload shared by demo and live adapters", () => {
    expect(generationInputSchema.safeParse({ profile, ingredientIds: ["oi"], prompt: "Ít đường" }).success).toBe(true);
  });

  it("rejects incomplete body data and an empty ingredient list", () => {
    expect(profileSchema.safeParse({ ...profile, age: 16 }).success).toBe(false);
    expect(generationInputSchema.safeParse({ profile, ingredientIds: [] }).success).toBe(false);
  });
});
