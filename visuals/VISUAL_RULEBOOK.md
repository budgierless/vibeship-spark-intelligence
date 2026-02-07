# Spark Visual Rulebook

Production rules for all Remotion-based videos, infographics, and motion content.
Derived from Vibeship design system + real-world feedback on readability and shareability.

---

## 1. Format & Dimensions

| Target | Resolution | Ratio | Use Case |
|--------|-----------|-------|----------|
| **Primary** | 1920 x 1080 | 16:9 | X, YouTube, desktop — best for data-heavy content |
| Secondary | 1080 x 1080 | 1:1 | X feed, LinkedIn — safe everywhere |
| Alternate | 1080 x 1920 | 9:16 | TikTok, Reels, Shorts — mobile-first short content |

**Default to 16:9 (1920x1080)** for infographic/data videos. The landscape format gives horizontal space for two-column layouts (title+data side by side), which is how the Vibeship dashboards are designed. Use 9:16 only for short mobile-first clips.

---

## 2. Color Hierarchy

Green (#00C49A) is the **primary** brand color. It should dominate.

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| **Primary** | Green | `#00C49A` | Main accent, section labels, bars, dots, primary numbers |
| **Secondary** | Orange | `#D97757` | Emphasis moments, callout borders, secondary highlights |
| **Tertiary** | Gold | `#c8a84e` | Sparingly — only for "premium" or "distilled" moments |
| Background | Deep Navy | `#0e1016` | Always. Never pure black. |
| Cards | Card Navy | `#1a1e28` | Card/panel backgrounds |
| Borders | Border | `#2a3042` | Subtle structure lines |

**Rule: If the video doesn't feel "green", something is wrong.** Green should be 60%+ of accent usage. Orange for 25%. Gold for 15% max.

---

## 3. Typography — Readability First

Fonts: **JetBrains Mono** (data/body) + **Instrument Serif** (headlines/quotes).

### Minimum Font Sizes (for 1080px wide canvas)

| Element | Min Size | Recommended | Weight |
|---------|----------|-------------|--------|
| Scene title (Serif) | 48px | 52–60px | 400 |
| Key numbers / hero stats | 64px | 72–96px | 700–800 |
| Bar labels / body text | 18px | 20–24px | 400–500 |
| Sublabels / descriptions | 14px | 16–18px | 400 |
| Section labels (caps) | 13px | 14–16px | 500 |
| Attribution | 13px | 14px | 400 |

**Rule: If you have to squint on a phone screen, the font is too small.** Every piece of text should be readable in 0.5 seconds at normal phone viewing distance.

**Rule: Key insights get HERO treatment.** The main takeaway of each scene should be the biggest text on screen (64px+), not buried in a card or sublabel.

---

## 4. Space Utilization

- **No dead space at the bottom.** Every scene should use the full vertical canvas.
- **Padding: 60–80px** on sides, 50–60px top/bottom.
- Content should fill 85%+ of the canvas area.
- If a scene has empty space, either add more content or reduce the canvas crop.
- **Vertical rhythm**: consistent spacing between elements (20–32px gaps).

---

## 5. No Rounded Corners

Vibeship design DNA: **zero border-radius on all elements**.
- Cards: sharp corners
- Bars: sharp corners (no borderRadius on progress bars)
- Buttons/badges: sharp corners
- Only exception: dots/circles (green indicator dots, particles)

---

## 6. Transitions & Animation

### Transitions Between Scenes
- **Never plain crossfade.** Use directional transitions:
  - Slide up (new scene pushes old scene out)
  - Scale + fade (old scene scales down slightly as new one fades in)
  - Wipe (horizontal or vertical)
- Transition duration: 12–18 frames (0.4–0.6s)
- Use easing: `cubic-bezier(0, 0, 0.2, 1)` — the Vibeship ease

### In-Scene Animation
- **Everything should move.** Static frames lose attention.
- Bars grow from left to right (spring animation, staggered by 6–10 frames)
- Numbers count up from 0 to final value (interpolate over 20–30 frames)
- Text enters with subtle translateY (15–20px) + opacity
- Particles always float (never stop)
- Key numbers pulse subtly (scale 1.0 → 1.02 → 1.0, slow sine wave)
- **Stagger everything.** Items in a list should animate 6–10 frames apart.

### Keeping Attention
- Each scene should have at least 3 distinct animation moments:
  1. Title/label entrance
  2. Data/content entrance (staggered)
  3. Key insight / callout entrance (delayed, dramatic)
- Use "reveal" timing: hold back the most interesting data by 1–1.5 seconds after the scene starts

---

## 7. Content Design Rules

### One Big Takeaway Per Scene
Every scene must have ONE thing that's immediately obvious:
- Scene about data → the **number** is the hero (72px+, colored, glowing)
- Scene about a finding → the **finding** is the hero (large serif text)
- Scene about comparison → the **contrast** is the hero (side-by-side, big difference)

### Make Insights Obvious
- Don't make people "dig deep" to understand the point
- If the insight is "4x better", the "4x" should be 72px+ and colored
- If the insight is "storytelling wins", those words should be highlighted
- Add a one-line "so what" explanation under every key stat

### Shareable Moments
- Each scene should be screenshot-worthy on its own
- The final scene should have the most shareable quote/insight
- Include @Spark_coded attribution on every scene (small, bottom)

---

## 8. Data Visualization

### Horizontal Bars
- Height: 8px (not 6px — more visible)
- Gap between bars: 20–24px
- Labels: left-aligned, 18–20px
- Values: right-aligned, same size, colored
- Sublabels: below bar, 14–16px, tertiary color

### Cards / Callout Boxes
- Background: `#1a1e28` (bgCard)
- Border: `1px solid #2a3042`
- Left accent border: `3px solid` (green or orange)
- Padding: 24–32px
- No rounded corners

### Numbers
- Hero numbers (the main stat): 72–96px, colored, with text-shadow glow
- Supporting numbers: 36–48px
- Always add a unit/label below or beside the number

---

## 9. Scene Pacing (for 14s video)

| Scene | Duration | Frames (30fps) | Purpose |
|-------|----------|-----------------|---------|
| 1 | 4s | 120 | Hook — grab attention with the big picture |
| 2 | 3s | 90 | Context — what was studied |
| 3 | 4s | 120 | Meat — the key findings (most time here) |
| 4 | 3s | 90 | Reveal — the shareable insight |

- **Scene 1** should hook in the first 1.5 seconds (title + one big number)
- **Scene 3** gets the most time because it has the most data
- **Scene 4** should leave the viewer wanting to share or comment

---

## 10. Background & Atmosphere

- **Radial glow** from top center: subtle green or orange tint (opacity 0.03–0.05)
- **Floating particles**: 15–25 particles, gold colored, ascending slowly
  - Opacity: 0.06–0.15 (very subtle, never distracting)
  - Size: 1–2.5px
- **No wireframe lines or grid patterns** — those are for the PFP/brand identity only
- Background should feel "alive" but not busy

---

## 11. Attribution & Branding

- Every scene: small `@Spark_coded` at bottom with green dot
- Font: JetBrains Mono, 13–14px, letter-spacing 3
- Color: textTertiary (#6b7489)
- Green dot: 7px, with `box-shadow: 0 0 8px greenGlow`
- Position: center-bottom, 40–50px from bottom edge

---

## 12. Rendering

- Always render at **30fps** (smooth enough, reasonable file size)
- Export format: **MP4** for video, **PNG** for stills
- Still frame: pick a frame where all elements are visible (usually 70–80% through Scene 1)
- Test on phone screen before posting — if anything is hard to read, fix it

---

## Quick Checklist Before Rendering

- [ ] Green is the dominant accent color (60%+)
- [ ] No rounded corners anywhere
- [ ] Smallest text is 14px+ (readable on phone)
- [ ] Key insight per scene is 64px+ and obvious
- [ ] No dead space at bottom of any scene
- [ ] All transitions are directional (not plain crossfade)
- [ ] Bars, numbers, text all animate in (nothing appears instantly)
- [ ] @Spark_coded on every scene
- [ ] Tested at phone size for readability
