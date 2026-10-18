---
name: ai-agent-frontend-rules
description: Apply the project frontend rulebook for AI Agent web product UI. Use whenever Codex designs, builds, edits, reviews, refactors, or QA-checks frontend screens, components, layouts, styling, UX states, prompt inputs, AI workspace flows, responsive behavior, accessibility, or frontend code for this project.
---

# AI Agent Frontend Rules

## Required Reference

Before doing any frontend design or coding work, read `references/frontend-rulebook.md` in full. Treat it as the source of truth for product UX, design system, AI states, accessibility, performance, and QA expectations.

If the task is small, still check the relevant sections of the reference before editing. If the task touches layout, components, styling, AI interaction, state handling, or responsive behavior, read the full reference.

## Working Order

Follow this order for frontend tasks:

1. Identify whether the work is a public landing page, logged-in AI workspace, component update, styling fix, or QA/review task.
2. Convert any available brand guideline into design tokens before writing page code.
3. Define or reuse tokens for color, typography, spacing, radius, shadows, breakpoints, motion, and z-index.
4. Define or reuse the component system before duplicating UI patterns.
5. Define the page goal, primary action, secondary actions, content hierarchy, states, responsive behavior, and accessibility notes.
6. Implement with reusable components and tokenized styling.
7. Verify empty, loading, error, success, AI thinking, AI generating, tool activity, confirmation, and retry states where relevant.
8. Check responsive behavior on mobile, tablet, and desktop.
9. Run the final QA checklist from the rulebook before delivery.

Do not start by freely inventing a UI. Build from the rulebook, the project's existing design system, and the current codebase patterns.

## Product Direction

Design the product as a trustworthy AI workspace, not a generic chatbot, decorative landing page, or random SaaS template.

Prioritize:

- Clarity over decoration.
- Control over automation.
- Trust over magic.
- Consistency over novelty.
- Accessibility over visual tricks.
- Performance over heavy effects.
- Reusable system over one-off UI.
- Commercial usability over experimental visuals.

The UI should feel intelligent, calm, helpful, professional, fast, safe, modern, and trustworthy.

## Implementation Guardrails

Use these guardrails during code work:

- Use existing project patterns before introducing new abstractions.
- Avoid hardcoded random values; use tokens or existing variables.
- Create reusable components when a pattern appears more than once.
- Include meaningful component states, not only the happy path.
- Explain AI activity with specific state text; avoid generic spinners.
- Require confirmation for risky, destructive, public, financial, external, or irreversible actions.
- Keep prompt input behavior explicit, including submit, disabled, loading, error, and keyboard states.
- Structure long AI outputs with headings, sections, actions, and source/context details where relevant.
- Preserve keyboard navigation, visible focus states, semantic HTML, readable contrast, and mobile touch targets.
- Keep performance in mind: lazy load heavy previews/history, avoid heavy decorative animation, and prevent layout shift.

## Delivery Checklist

Before finalizing frontend work, confirm:

- The implementation follows `references/frontend-rulebook.md`.
- Tokens and reusable components are used instead of one-off styling.
- AI states and user control are visible.
- Empty, loading, error, success, and retry states are handled where relevant.
- Risky actions require review and confirmation.
- Mobile behavior is designed rather than merely shrunk.
- Accessibility and keyboard use are acceptable.
- The UI feels like a real commercial AI Agent product.
