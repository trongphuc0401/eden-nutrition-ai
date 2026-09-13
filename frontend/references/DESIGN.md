---
name: Fresh Citrus AI Wellness
colors:
  surface: '#fff8f5'
  surface-dim: '#fdd2b2'
  surface-bright: '#fff8f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fff1e9'
  surface-container: '#ffeadc'
  surface-container-high: '#ffe3d0'
  surface-container-highest: '#ffdcc3'
  on-surface: '#2c1604'
  on-surface-variant: '#584237'
  inverse-surface: '#442b15'
  inverse-on-surface: '#ffede3'
  outline: '#8c7164'
  outline-variant: '#e0c0b1'
  surface-tint: '#9d4300'
  primary: '#9d4300'
  on-primary: '#ffffff'
  primary-container: '#f97316'
  on-primary-container: '#582200'
  inverse-primary: '#ffb690'
  secondary: '#ac3400'
  on-secondary: '#ffffff'
  secondary-container: '#fd6b36'
  on-secondary-container: '#5d1900'
  tertiary: '#416900'
  on-tertiary: '#ffffff'
  tertiary-container: '#6cab00'
  on-tertiary-container: '#213800'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbca'
  primary-fixed-dim: '#ffb690'
  on-primary-fixed: '#341100'
  on-primary-fixed-variant: '#783200'
  secondary-fixed: '#ffdbd0'
  secondary-fixed-dim: '#ffb59d'
  on-secondary-fixed: '#390c00'
  on-secondary-fixed-variant: '#832600'
  tertiary-fixed: '#acf847'
  tertiary-fixed-dim: '#91db2a'
  on-tertiary-fixed: '#102000'
  on-tertiary-fixed-variant: '#304f00'
  background: '#fff8f5'
  on-background: '#2c1604'
  surface-variant: '#ffdcc3'
  surface-cream: '#FFFDF5'
  card-white: '#FFFFFF'
  border-beige: '#F1E7D8'
  hover-orange: '#9A3412'
  warning-yellow: '#FACC15'
  accent-coral: '#FB7185'
  error-red: '#E11D48'
typography:
  display-lg:
    fontFamily: Playfair Display
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Playfair Display
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-lg-mobile:
    fontFamily: Playfair Display
    fontSize: 28px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Poppins
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Poppins
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Poppins
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: Poppins
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Poppins
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Poppins
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 20px
  margin-mobile: 16px
  margin-desktop: 40px
---

## Brand & Style

The design system for this product is centered on a "Premium Wellness AI Agent" persona—avoiding the cold, clinical feel of medical apps or the aggressive energy of fitness trackers. The brand personality is **fresh, healthy, and approachable**, positioning itself as a high-performance workspace for nutritional intelligence.

### Design Style: Modern Tactile Minimalism
The system utilizes a refined **Minimalist** foundation with **Tactile** accents. It leverages heavy whitespace and a warm neutral base to ensure a "calm" environment, while using high-radius "soft" cards and subtle shadows to create a physical, approachable presence. 

- **Workspace Logic:** The UI is treated as a professional canvas, not a simple chatbot. It organizes complex AI processing steps into clean, scannable activity cards.
- **Visual Tone:** Sophisticated yet warm. The use of serif headlines adds a "boutique wellness" touch, while the sans-serif UI maintains functional clarity.
- **Vietnamese Optimization:** Typography is tuned for readability in Vietnamese, ensuring diacritics do not disrupt line-height or vertical rhythm.

## Colors

The palette is inspired by natural citrus and earthy elements. It uses a **60-15-10-7-5-3** distribution rule to maintain visual balance and prevent the vibrant orange from becoming overwhelming.

### Color Hierarchy
- **Primary Orange (#F97316):** Used for brand identity and core interactive elements.
- **Primary Action (#C2410C):** Reserved for high-priority calls to action and "Create" triggers.
- **Deep Brown (#3A220D):** Used for primary typography and deep shadows to provide grounding contrast without the harshness of pure black.
- **Surface Cream (#FFFDF5):** The primary background color to evoke a "paper-like" or "natural" feel.

### Themed Visual Modes
While maintaining the core palette, specific states shift the visual emphasis:
- **Core:** Balanced mix of Cream and Orange.
- **Green Wellness:** Increased use of Success Green (#84CC16) for nutrition targets and positive health feedback.
- **Berry Smoothie:** Subtle Coral (#FB7185) accents for favorites and specialized recipe categories.
- **Warm Energy:** Increased Yellow (#FACC15) for tips, warnings, and system confirmations.

## Typography

The system uses a pairing of **Playfair Display** and **Poppins**.

- **Playfair Display** is used exclusively for "emotional" headings—welcome messages, recipe titles, and major section breaks. It communicates the "Premium Wellness" aspect.
- **Poppins** handles all functional UI, prompt inputs, AI output, and data visualization. It is chosen for its geometric clarity and excellent support for Vietnamese character sets.

Line heights are slightly generous to ensure that complex nutritional data and recipe instructions remain readable and "airy."

## Layout & Spacing

This design system follows a **Fluid Grid** model designed for a high-performance workspace.

### Workspace Architecture
- **Sidebar (Left):** 280px fixed width on desktop. Contains history, saved recipes, and profile templates. Collapses into a Hamburger/Drawer on mobile.
- **Main Canvas (Center):** Fluid width. This is the primary area for AI process visualization and recipe generation.
- **Context Panel (Right):** 320px fixed width. Houses secondary data like ingredient breakdowns and nutrition targets. Converts to a Bottom Sheet on mobile.
- **Prompt Bar (Bottom):** Centered, floating-style input that remains accessible at all times.

### Spacing Rhythm
A 4px baseline grid ensures alignment across all components. Content groups use 24px (lg) spacing, while internal card elements use 16px (md).

## Elevation & Depth

Hierarchy is established through **Tonal Layers** and **Ambient Shadows**.

- **Base Layer:** The Surface Cream (#FFFDF5) acts as the canvas.
- **Secondary Layer:** White Cards (#FFFFFF) sit on top of the cream background.
- **Shadows:** A distinctive deep brown tint shadow (`0 12px 32px rgba(58, 34, 13, 0.08)`) is used for primary cards. This shadow is softer and warmer than standard grey shadows, reinforcing the organic brand feel.
- **Outlines:** Low-contrast borders using Border Beige (#F1E7D8) define boundaries for input fields and nested cards without adding visual noise.

## Shapes

The shape language is "Soft and Organic." 

- **Main Cards:** Utilize a 20-28px radius (`rounded-xl` and above) to evoke a friendly, non-corporate feeling.
- **Input Fields:** Use a 12-16px radius to maintain a modern, approachable aesthetic.
- **Buttons:** Use a 14px radius for standard actions or full Pill shapes for primary brand calls to action.
- **Interactive Elements:** Checkboxes and radio buttons should be slightly rounded (4px) to match the overall softness.

## Components

### Buttons
- **Primary:** Background #C2410C, Text #FFFFFF. Pill-shaped. Subtle hover state at #9A3412.
- **Secondary:** Transparent background, #3A220D border, 14px radius.
- **Ghost:** Text only (#F97316), used for less critical actions like "Edit Prompt."

### AI Workspace Elements
- **Prompt Input:** A large, soft-edged container (16px radius) with an elevated shadow. Should include a distinct "Thinking" state.
- **Thinking Indicator:** Uses a subtle pulse animation in #F97316 rather than a standard spinner.
- **Tool Activity Cards:** Used to show the AI's "Research" or "Formulate" steps. These use the Border Beige and White Card structure to separate process from final result.

### Cards & Feedback
- **Recipe Card:** The hero component. Uses the maximum 28px radius, heavy brown shadow, and Playfair Display for the title.
- **Nutrition Facts Card:** Uses a structured grid with #84CC16 (Success Green) for positive daily value progress.
- **Allergy Warning:** High-contrast background using #FB7185 (Coral) with a clear warning icon.

### Feedback Systems
- **Toasts:** Floating at the top-center, using 12px radius and themed background colors (Green for success, Red for errors).
- **Empty States:** Illustrations should use the Deep Brown line art style with Cream fills to stay consistent with the brand.