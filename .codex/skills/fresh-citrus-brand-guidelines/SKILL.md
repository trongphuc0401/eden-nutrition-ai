---
name: fresh-citrus-brand-guidelines
description: Apply the Fresh Citrus AI Wellness brand guideline for the nutrition and wellness AI agent product. Use whenever Codex designs, builds, edits, reviews, refactors, or QA-checks branded frontend UI, landing pages, dashboards, AI workspace screens, nutrition components, color tokens, typography, imagery, microcopy, responsive layouts, or design-system decisions for this project.
---

# Fresh Citrus Brand Guidelines

## Required Reference

Before doing branded frontend design or coding work, read `references/brand-guideline.md` in full. Treat it as the source of truth for the product's visual identity, color system, typography, imagery, tone, nutrition-specific UI, and brand QA.

Use this skill together with `ai-agent-frontend-rules` for frontend tasks. This skill defines the brand identity; `ai-agent-frontend-rules` defines the AI workspace structure, state handling, accessibility, performance, and implementation workflow.

## Brand Direction

Design the product as a Fresh Citrus AI Wellness experience: fresh, energetic, youthful, healthy, friendly, nutritious, trustworthy, and intelligent.

The product is an AI-powered nutrition and wellness agent for meal plans, smoothie recipes, nutrition plans, calorie and macro guidance, ingredient suggestions, and personalized wellness recommendations.

It must not feel medical, clinical, dark, gym-focused, luxury, overly futuristic, or like a generic SaaS/chatbot template.

## Working Order

Follow this order before writing UI code:

1. Read `references/brand-guideline.md`.
2. Extract or reuse the exact brand tokens from the guideline.
3. Map tokens into the project's design system variables.
4. Decide whether the surface is landing, app workspace, dashboard, prompt flow, nutrition output, or reusable component.
5. Apply the correct color meanings, typography, card style, image direction, icon style, and microcopy tone.
6. Build or update reusable components instead of creating one-off branded patterns.
7. Check responsive behavior and accessibility against the brand rules.
8. Run the brand QA checklist before delivery.

## Token Rules

Use the exact palette from the guideline as the foundation:

- Brand primary orange: `#F97316`.
- Accessible primary action: `#C2410C`.
- Primary hover: `#9A3412`.
- Deep brown: `#3A220D`.
- Surface cream: `#FFFDF5`.
- Card white: `#FFFFFF`.
- Border soft: `#F1E7D8`.
- Fresh green: `#84CC16`.
- Lemon yellow: `#FACC15`.
- Coral pink: `#FB7185`.
- Error coral: `#E11D48`.

Keep screens mostly cream, white, and warm neutral. Use citrus colors as meaningful signals, not decoration. Follow the guideline's recommended ratio: 60% cream/white/warm neutrals, 15% orange accents, 10% deep brown text, 7% green, 5% yellow, 3% coral.

Use Playfair Display mainly for landing hero and emotional marketing headings. Use Poppins for app UI, body text, buttons, form fields, dashboards, and AI responses.

## UI Guardrails

Follow these guardrails:

- Use accessible dark orange for primary buttons with white text.
- Do not overuse orange; use it to guide attention.
- Use green for healthy, positive, completed, or nutrition-success states.
- Use yellow for tips, energy, waiting, and confirmation states.
- Use coral sparingly for favorites, warmth, errors, or destructive moments.
- Do not use lemon yellow as the main CTA or primary text color.
- Use rounded, soft cards with warm borders and soft shadows.
- Use fresh fruit, smoothie, healthy bowl, ingredient, and warm lifestyle imagery.
- Avoid hospital, gym-only, dark luxury, robotic AI, cold clinical, or generic corporate imagery.
- Keep AI output structured into cards, nutrition facts, ingredient lists, macro breakdowns, recipes, plans, assumptions, and next actions.
- Use friendly, encouraging, practical microcopy. Avoid fear-based, medical, extreme fitness, or overhyped AI language.

## Brand QA Checklist

Before finalizing branded frontend work, confirm:

- The work follows `references/brand-guideline.md`.
- The UI feels like Fresh Citrus AI Wellness, not a generic SaaS/chatbot UI.
- Color use follows semantic meaning and accessible contrast.
- Typography uses Playfair Display and Poppins in the right contexts.
- Landing pages feel fresh, visual, editorial, and nutrition-oriented.
- App pages feel focused, useful, readable, and controlled.
- AI states are brand-colored and human-readable.
- Nutrition outputs are structured, scannable, and actionable.
- Imagery and icons support food, wellness, freshness, and friendly AI guidance.
- Mobile layout is intentionally designed and easy to tap.
- The final experience feels fresh, helpful, positive, trustworthy, and commercially usable.
