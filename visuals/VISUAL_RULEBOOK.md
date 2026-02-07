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
| **Secondary** | Orange | `#D97757` | Emphasis moments, callout borders, punchlines, contrast highlights |
| **Tertiary** | Gold | `#c8a84e` | Sparingly — only for "premium" or "distilled" moments |
| Background | Deep Navy | `#0e1016` | Always. Never pure black. |
| Cards | Card Navy | `#1a1e28` | Card/panel backgrounds |
| Borders | Border | `#2a3042` | Subtle structure lines |

**Rule: If the video doesn't feel "green", something is wrong.** Green should be 60%+ of accent usage. Orange for 25%. Gold for 15% max.

**Orange for punchlines**: Use orange to highlight the surprise/comedy/contrast element of each video. Green = data, Orange = emotion.

---

## 3. Typography — Readability First

Fonts: **JetBrains Mono** (data/body) + **Instrument Serif** (headlines/quotes).

Loaded via Google Fonts in `fonts.ts`. Both must be loaded before render.

### Minimum Font Sizes (for 1920x1080 canvas)

| Element | Min Size | Recommended | Weight |
|---------|----------|-------------|--------|
| Scene title (Serif) | 56px | 60–78px | 400 |
| Key numbers / hero stats | 80px | 96–140px | 700–800 |
| Bar labels / body text | 22px | 24–30px | 400–500 |
| Sublabels / descriptions | 18px | 20–24px | 400 |
| Section labels (caps) | 18px | 20–22px | 500, letter-spacing 3–5 |
| Attribution | 18px | 20–22px | 400 |
| Insight card text | 22px | 24–28px | 400–500 |

**Rule: If you have to squint on a phone screen, the font is too small.** Every piece of text should be readable in 0.5 seconds at normal phone viewing distance.

**Rule: Key insights get HERO treatment.** The main takeaway of each scene should be the biggest text on screen (80px+), not buried in a card or sublabel.

**Rule: When in doubt, go bigger.** Our first video required a 75% font increase across the board. Default sizes always feel too small when rendered on mobile.

---

## 4. Layout — Two-Column is Default

16:9 gives horizontal space. Use it.

- **Default layout**: Two-column (flex row, gap 50–60px)
  - Left: title + context + primary data
  - Right: supporting data, insight cards, hero numbers
- **Centered layout**: Only for the final reveal scene or single-stat moments
- **Padding**: 45–80px on sides, 45–60px top/bottom
- Content should fill 85%+ of the canvas area
- **No dead space at the bottom.** Every scene should use the full vertical canvas.
- **Vertical rhythm**: consistent spacing between elements (18–32px gaps)

### Column Ratios
- Equal split: `flex: 1` + `flex: 1` (data-heavy scenes)
- Weighted: `flex: 1.1` + `flex: 0.9` (when one side has more content)
- The heavier content goes on the left (reading direction)

---

## 5. No Rounded Corners

Vibeship design DNA: **zero border-radius on all elements**.
- Cards: sharp corners
- Bars: sharp corners (no borderRadius on progress bars)
- Buttons/badges: sharp corners
- Highlight boxes: sharp corners
- Only exception: dots/circles (green indicator dots, particles)

---

## 6. Transitions & Animation

### Cross-Dissolve Between Scenes (Preferred)

Use **overlapping Sequences** with a `SceneWrap` component:
- Each scene fades out over its last 15 frames
- The next scene fades in over its first 15 frames
- Scenes overlap by 15 frames, creating a smooth cross-dissolve
- First scene: `fadeIn={0}` (starts visible), Last scene: `fadeOut={0}` (stays visible)

```tsx
// SceneWrap handles fade-in/out per scene
// Uses separate interpolations (NOT a single 4-point array)
// to avoid the monotonically-increasing bug when fadeIn=0 or fadeOut=0
```

**Never use black-curtain wipes** (sliding a black div across). They feel jarring.
**Never use plain opacity crossfades** without the overlap — they create a "flash to black" gap.

### Transition Timing
- Overlap duration: 15 frames (0.5s)
- Use easing: `cubic-bezier(0, 0, 0.2, 1)` — the Vibeship ease

### In-Scene Animation
- **Everything should move.** Static frames lose attention.
- Bars grow from left to right (spring animation, staggered by 6–10 frames)
- Numbers count up from 0 to final value (interpolate over 18–25 frames)
- Text enters with subtle translateY (15–20px) + opacity
- Cards slide in from left/right with translateX (25–30px) + opacity
- Particles always float (never stop)
- Key numbers pulse subtly (scale 1.0 → 1.02 → 1.0, slow sine wave)
- Punchline elements pulse with glow (box-shadow oscillation via `Math.sin`)
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
- Scene about data → the **number** is the hero (96px+, colored, glowing)
- Scene about a finding → the **finding** is the hero (large serif text)
- Scene about comparison → the **contrast** is the hero (side-by-side, big difference)
- Scene about a story → the **punchline** is the hero (orange accent, delayed reveal)

### Make Insights Obvious
- Don't make people "dig deep" to understand the point
- If the insight is "4x better", the "4x" should be 120px+ and colored
- If the insight is "storytelling wins", those words should be highlighted
- Add a one-line "so what" explanation under every key stat
- **Explain jargon**: If you use terms like "curiosity gap" or "social proof", add a plain-language subtitle explaining what it means

### Comedy & Surprise Win
- The most viral content in our research was humor, not education
- If the data reveals something funny or ironic, make that the hero of the reveal scene
- Use orange for comedy/surprise elements — it stands out against the green data
- "Make them laugh, not learn" — entertainment > information for shareability

### Shareable Moments
- Each scene should be screenshot-worthy on its own
- The final scene should have the most shareable quote/insight
- Include @Spark_coded attribution on every scene (small, bottom)
- The ~~strikethrough~~ → highlight pattern works well for punchy takeaways

---

## 8. Data Visualization

### Horizontal Bars
- Height: 8–10px (not 6px — more visible)
- Gap between bars: 18–24px
- Labels: left-aligned, 24–28px
- Values: right-aligned, same size, colored
- Sublabels: below bar, 18–22px, tertiary color

### Cards / Callout Boxes
- Background: `#1a1e28` (bgCard)
- Border: `1px solid #2a3042`
- Left accent border: `3–4px solid` (green for data, orange for punchlines)
- Padding: 22–32px
- No rounded corners

### Numbers
- Hero numbers (the main stat): 96–140px, colored, with text-shadow glow
- Supporting numbers: 36–64px
- Always add a unit/label below or beside the number
- Counter animation: interpolate from 0 to value over 18–25 frames

### Quote-Style Tweet Cards
- bgCard background with orange left border
- Content in monospace, 26–30px
- Highlighted words in orange (bold)
- Punchline in a subtle tinted box (rgba of accent color, 0.08 opacity bg)
- Attribution note below in tertiary color

---

## 9. Scene Pacing (for 14s video)

| Scene | Duration | Frames (30fps) | Purpose |
|-------|----------|-----------------|---------|
| 1 | 4.5s | 135 | Hook — grab attention with the big picture |
| 2 | 3.8s | 115 | Deep dive — the key data patterns |
| 3 | 3.3s | 100 | Meat — the headline findings |
| 4 | 3.3s | 100 | Reveal — the shareable surprise |

With 15-frame overlaps:
- Scene 1: from=0, dur=135
- Scene 2: from=120, dur=115
- Scene 3: from=220, dur=115
- Scene 4: from=320, dur=100
- Total: 420 frames = 14s @ 30fps

**Rule: The reveal scene should get AT LEAST 3 seconds.** It's the payoff — don't rush it. Compress the middle scenes before shortening the reveal.

- **Scene 1** should hook in the first 1.5 seconds (title + one big number)
- **Scene 2–3** carry the data — stagger information for discovery
- **Scene 4** should leave the viewer wanting to share or comment

---

## 10. Background & Atmosphere

- **Radial glow** from center: subtle green tint (opacity 0.03–0.05)
- **Floating particles**: 15–25 particles, gold colored, ascending slowly
  - Opacity: 0.05–0.15 (very subtle, never distracting)
  - Size: 1–2.5px
  - Use sine-wave oscillation on opacity for "breathing" effect
- **No wireframe lines or grid patterns** — those are for the PFP/brand identity only
- Background should feel "alive" but not busy

---

## 11. Attribution & Branding

- Every scene: small `@Spark_coded` at bottom with green dot
- Font: JetBrains Mono, 18–22px, letter-spacing 3–4
- Color: textTertiary (#6b7489)
- Green dot: 7–9px, with `box-shadow: 0 0 10px greenGlow`
- Position: center-bottom, 28–40px from bottom edge
- Fades in with the scene (delay 40–50 frames from scene start)

---

## 12. Rendering & Export

### Render Command
```bash
# Full video (H.264, high quality)
npx remotion render IntelligenceFunnel --codec h264 --crf 18

# Still frame (for thumbnail)
npx remotion still FunnelStill --frame 90 --image-format png
```

### Codec & Quality
- **Codec**: H.264 (MP4) — universal, X/Twitter native
- **CRF**: 18 (near-lossless, ~2–5MB for 14s) — default 23 is too soft for data text
- **FPS**: 30 — smooth enough, reasonable file size
- **Never use**: WebM (X doesn't accept), ProRes (too large), H.265 (compatibility issues)

### Export Checklist
- [ ] Rendered at 1920x1080
- [ ] File size under 15MB (ideal for X upload)
- [ ] Test playback on phone before posting
- [ ] Pick a still frame where all elements are visible (70–80% through Scene 1)

---

## 13. Production Workflow

### Step 1: Data Extraction
Pull real data from the Spark research system. Never use placeholder stats.

| Data Source | Path | What It Contains |
|-------------|------|-----------------|
| Research state | `~/.spark/x_research_state.json` | Session count, tweets scanned, topic performance |
| Social-convo chip | `~/.spark/chip_insights/social-convo.jsonl` | Pattern analysis: trigger rankings, strategy rankings |
| Engagement-pulse chip | `~/.spark/chip_insights/engagement-pulse.jsonl` | Per-tweet LLM analysis: triggers, hooks, why_it_works |
| Evolution engine | Dashboard `/api/evolution` | Trigger weights, strategy weights, voice shifts |
| Filter funnel | Dashboard `/api/filter-funnel` | Stage-by-stage filtering stats |

### Step 2: Story Structure
Every infographic video follows: **Hook → Data → Findings → Reveal**

1. **Hook** (Scene 1): What did we study? How much data? What survived? Show the funnel/scale.
2. **Data** (Scene 2): The patterns. Bars, percentages, comparisons. Explain what each metric means.
3. **Findings** (Scene 3): The headline numbers. The "4x" moments. Side-by-side comparisons.
4. **Reveal** (Scene 4): The surprise. The most shareable, unexpected finding. Comedy > education.

### Step 3: Build in Remotion
- One component per scene (SceneFunnel, SceneTriggers, etc.)
- Shared helpers: `Counter`, `Bar`, `Label`, `Attribution`, `Particles`, `SceneWrap`
- All data as const arrays at the top of the file
- Theme from `theme.ts` — never hardcode colors

### Step 4: Iterate
1. Preview in Remotion Studio (`npm run dev` → localhost:3000)
2. Check readability at phone size
3. Verify green dominance
4. Test transitions frame-by-frame
5. Render with `--crf 18`
6. Watch on phone before posting

---

## 14. Reusable Components

### Available in `IntelligenceFunnel.tsx` (extract to shared lib as needed):

| Component | Purpose | Key Props |
|-----------|---------|-----------|
| `Counter` | Animated number count-up | `to`, `delay`, `duration`, `style` |
| `Bar` | Horizontal bar with label + value | `label`, `value`, `pct`, `color`, `delay`, `sub` |
| `Label` | Section label with green dot | `text`, `delay` |
| `Attribution` | @Spark_coded branding | `delay` |
| `Particles` | Floating gold particles | `count`, `seed` |
| `SceneWrap` | Cross-dissolve fade wrapper | `durationInFrames`, `fadeIn`, `fadeOut` |

---

## 15. Content Strategy Insights (from Research)

These findings should inform what content we create and how we present it:

- **Curiosity gaps** appeared in 87% of viral tweets — open a question before answering it
- **Surprise** triggers get 5% more engagement than validation — defy expectations
- **Long-form** gets 4x more engagement than short (2,299 vs 560 avg likes)
- **Announcement + storytelling** is the winning format (6,086 avg)
- **Comedy beats education** — the single most viral tweet was a joke (12,706 likes)
- **Authenticity is unfakeable** — polished content underperforms raw/real content

Apply these to the videos themselves: open with a question, reveal surprising data, tell a story, end with humor.

---

## Quick Checklist Before Rendering

- [ ] Green is the dominant accent color (60%+)
- [ ] No rounded corners anywhere
- [ ] Smallest text is 18px+ (readable on phone)
- [ ] Key insight per scene is 80px+ and obvious
- [ ] No dead space at bottom of any scene
- [ ] Transitions are cross-dissolve (overlapping sequences, not black wipes)
- [ ] Bars, numbers, text all animate in (nothing appears instantly)
- [ ] @Spark_coded on every scene
- [ ] Jargon terms have plain-language explanations
- [ ] Data is real (from chip_insights/research_state), not placeholder
- [ ] Render at CRF 18 (not default 23)
- [ ] Tested at phone size for readability
- [ ] Final scene is the most shareable moment
