import type { Ingredient } from "@/lib/types";

// Tints come from the brand palette; the pick is a stable hash of the id, so any new item from the API gets a look without code changes.
const FRUIT_TINTS = ["bg-orange-soft text-action", "bg-yellow-soft text-yellow-text", "bg-coral-soft text-coral-strong", "bg-green-soft text-green-text"];
const SUPPORT_TINT = "bg-neutral-soft text-muted";

function hash(text: string) { let value = 0; for (const char of text) value = (value * 31 + char.charCodeAt(0)) >>> 0; return value; }

/** Visual marker built only from API data (name, kind), so the catalog stays fully dynamic. */
export function IngredientAvatar({ ingredient, size = "md" }: { ingredient: Pick<Ingredient, "id" | "name" | "kind">; size?: "sm" | "md" }) {
  const tint = ingredient.kind === "fruit" ? FRUIT_TINTS[hash(ingredient.id) % FRUIT_TINTS.length] : SUPPORT_TINT;
  const dimensions = size === "sm" ? "size-5 text-[0.65rem]" : "size-10 text-base";
  return <span aria-hidden="true" className={`grid shrink-0 place-items-center rounded-full font-semibold ${dimensions} ${tint}`}>{ingredient.name.trim().charAt(0).toUpperCase()}</span>;
}
