import { z } from "zod";

export const profileSchema = z.object({
  age: z.coerce.number().int().min(18, "Bạn cần từ 18 tuổi").max(120),
  gender: z.string().min(1, "Hãy chọn giới tính"),
  heightCm: z.coerce.number().min(100, "Chiều cao chưa hợp lệ").max(250),
  weightKg: z.coerce.number().min(25, "Cân nặng chưa hợp lệ").max(400),
  hometown: z.string().min(1, "Hãy chọn quê quán"),
  allergies: z.array(z.string()),
  dislikes: z.array(z.string()),
  preferences: z.array(z.string()),
  notes: z.string().max(500, "Ghi chú tối đa 500 ký tự"),
});

export type ProfileInput = z.infer<typeof profileSchema>;

export const generationInputSchema = z.object({
  profile: profileSchema,
  ingredientIds: z.array(z.string()).min(1, "Hãy chọn ít nhất một nguyên liệu"),
  prompt: z.string().max(500, "Yêu cầu tối đa 500 ký tự").optional(),
});

export type GenerationInput = z.infer<typeof generationInputSchema>;

export type ApiProblem = {
  code: string;
  message: string;
  retryable: boolean;
  fields?: Record<string, string>;
};

export function isApiProblem(value: unknown): value is ApiProblem {
  return value !== null && typeof value === "object" && "code" in value && "message" in value;
}
