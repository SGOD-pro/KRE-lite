---
name: Cited or Silent
colors:
  surface: '#fcf9f6'
  surface-dim: '#dcd9d7'
  surface-bright: '#fcf9f6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f1'
  surface-container: '#f0edeb'
  surface-container-high: '#ebe8e5'
  surface-container-highest: '#e5e2e0'
  on-surface: '#1c1c1a'
  on-surface-variant: '#56423c'
  inverse-surface: '#31302f'
  inverse-on-surface: '#f3f0ee'
  outline: '#89726b'
  outline-variant: '#dcc1b8'
  surface-tint: '#9d4324'
  primary: '#9a4021'
  on-primary: '#ffffff'
  primary-container: '#b95837'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb59d'
  secondary: '#605f57'
  on-secondary: '#ffffff'
  secondary-container: '#e5e2d8'
  on-secondary-container: '#66655d'
  tertiary: '#96431e'
  on-tertiary: '#ffffff'
  tertiary-container: '#b55b34'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbd0'
  primary-fixed-dim: '#ffb59d'
  on-primary-fixed: '#390b00'
  on-primary-fixed-variant: '#7e2c0e'
  secondary-fixed: '#e5e2d8'
  secondary-fixed-dim: '#c9c6bd'
  on-secondary-fixed: '#1c1c16'
  on-secondary-fixed-variant: '#484740'
  tertiary-fixed: '#ffdbce'
  tertiary-fixed-dim: '#ffb598'
  on-tertiary-fixed: '#370e00'
  on-tertiary-fixed-variant: '#7a2f0a'
  background: '#fcf9f6'
  on-background: '#1c1c1a'
  surface-variant: '#e5e2e0'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 30px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  gap-xs: 4px
  gap-sm: 8px
  gap-md: 16px
  gap-lg: 24px
  margin-page: 32px
  sidebar-width: 280px
---

## Brand & Style
The design system is built upon the concept of **Calm Precision**. It serves researchers and analysts who require a focused, distraction-free environment for document interrogation. The aesthetic rejects the loud, saturated trends of typical SaaS products in favor of a "Research Tool" persona: grounded, authoritative, and intellectually honest.

The style is **Minimalist-Modern** with a focus on high-quality typography and tactile clarity. It avoids gradients, drop shadows, and decorative flourishes. Instead, it uses a sophisticated palette of warm neutrals and a single "Rust" accent to guide the eye. The interface should feel like a well-organized physical archive—stable, quiet, and reliable.

## Colors
This design system utilizes a "Warm Mono-Accent" strategy. The primary colors are anchored in bone, parchment, and charcoal tones to reduce eye strain during long reading sessions.

- **Primary Accent:** Used sparingly for critical actions (Submit, Cite, Primary Buttons). 
- **Neutral Palette:** Ranges from `#faf9f5` (Light) to `#262624` (Dark), providing a soft, non-clinical background that feels like high-quality paper.
- **Data Visualization:** A custom five-color sequence (`#b05730`, `#9c87f5`, `#ded8c4`, `#dbd3f0`, `#b4552d`) is used for document mapping and analytics, ensuring high contrast against the warm neutral backgrounds while maintaining the established professional tone.

## Typography
The system uses **Inter** for its neutral, systematic clarity. The hierarchy is intentionally "text-heavy," optimized for the consumption of long-form documents. 

Key constraints:
- **Body Text:** Always use the `body-lg` or `body-md` for document content to ensure readability. 
- **Line Height:** Set to a generous 1.6x multiplier for body copy to prevent "wall of text" fatigue.
- **Labels:** Use `label-md` for metadata, citations, and secondary UI cues. The uppercase styling adds a layer of formal structure to the research interface.

## Layout & Spacing
The layout follows a **Fixed-Fluid Hybrid** model. A fixed-width sidebar handles navigation and document history, while the main content area utilizes a fluid grid that caps at 1200px for optimal reading measure.

- **The Sidebar:** Occupies a 280px footprint with a distinct `#f5f4ee` background in light mode to visually separate tools from content.
- **Gutter Strategy:** 16px (2 units) is the standard gutter for internal card elements. 24px (3 units) is used for major section spacing.
- **Reading View:** When in "Analysis Mode," the UI should expand to a single-column view with 64px left/right margins to emulate the focus of a physical page.

## Elevation & Depth
In this design system, depth is achieved through **Tonal Layering** and **Low-Contrast Outlines** rather than shadows. 

- **Level 0 (Background):** Pure background color.
- **Level 1 (Cards/Surfaces):** Defined by a `1px` border of `#dad9d4` (Light) or `#3e3e38` (Dark). No shadow.
- **Level 2 (Active/Focus):** Elements in focus do not lift; they receive a primary accent border or a subtle color shift to the secondary surface color.
- **Modals/Overlays:** Use a subtle backdrop blur (8px) and a `1px` border. If a shadow is absolutely required for clarity, use a diffused, 10% opacity shadow without any vertical offset (ambient glow).

## Shapes
A consistent **0.5rem (8px)** radius is applied to all interactive and container elements. This "Soft" geometry provides a humanistic touch to an otherwise rigorous, technical tool. 

- **Buttons & Inputs:** Fixed at 8px.
- **Cards:** Fixed at 8px. 
- **Active States:** Tabs or highlighted list items use the same 8px radius for their background plates.
- **Exceptions:** Very small tags or badges may use a "Pill" (999px) shape if they represent dismissible entities, though 8px is preferred for consistency.

## Components

### Buttons
- **Primary:** Background `#c96442`, Text `#ffffff`, 8px radius. Heavy weight text.
- **Secondary:** Background `#e9e6dc`, Text `#28261b`, 1px border `#b4b2a7`. 
- **Ghost:** No background, Text `#535146`, primary accent color on hover.

### Input Fields
- Use `#faf9f5` (Light) or `#1b1b19` (Dark) for the fill. 
- The border is a crisp 1px `#b4b2a7`. 
- On focus, the border shifts to the primary accent color with a 2px outer ring of the same color at 20% opacity.

### Document Cards
- Flat surfaces with 1px border. 
- Titles use `headline-md`. 
- Metadata (Date, Source, Citation count) should use `label-md` in `muted-foreground`.

### Citations (Specific Component)
- High-contrast inline tags. 
- Background: `#e9e6dc`. 
- Text: `#c96442` (Bold). 
- Clicking a citation should highlight the corresponding source block with a 2px left-border of the primary accent color.

### Checkboxes & Radios
- Square 18px forms with 4px radius. 
- Selected state uses primary accent fill with a white check/dot.