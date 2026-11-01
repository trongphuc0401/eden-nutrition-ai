import type { Profile } from "./types";

// Overweight starts at BMI 23 for Vietnamese adults (QĐ 2892/BYT), matching the backend classification rules.
export const BMI_SCOPE_MIN = 23;

/** Nothing pre-filled: every value comes from the user during onboarding. */
export const emptyProfile: Profile = {
  age: 0, gender: "", heightCm: 0, weightKg: 0, hometown: "", activityLevel: "light",
  allergies: [], dislikes: [], preferences: [], notes: "", healthRestrictionStatus: "unknown",
};

export function bmi(profile: Pick<Profile, "heightCm" | "weightKg">) {
  return profile.heightCm > 0 && profile.weightKg > 0 ? profile.weightKg / ((profile.heightCm / 100) ** 2) : 0;
}

export function isProfileFilled(profile: Profile) { return profile.age >= 18 && profile.heightCm >= 100 && profile.weightKg > 25 && Boolean(profile.gender) && Boolean(profile.hometown); }

export function inScope(profile: Profile) { return bmi(profile) >= BMI_SCOPE_MIN; }

export function profileSummary(profile: Profile) {
  if (!isProfileFilled(profile)) return "Chưa hoàn tất hồ sơ.";
  return `${profile.gender}, ${profile.age} tuổi · ${profile.heightCm} cm · ${profile.weightKg} kg · BMI ${bmi(profile).toFixed(1)}`;
}
