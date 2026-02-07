/**
 * Spark brand theme — Vibeship design system.
 *
 * Pulled directly from the Pulse dashboard (vibeship-spark-pulse)
 * and Neural dashboard (social_intel/index.html) CSS variables.
 *
 * Fonts: JetBrains Mono (data) + Instrument Serif (headings)
 * loaded via @import in IntelligenceFunnel.tsx
 */

export const SPARK_THEME = {
  // ── Backgrounds ──────────────────────────────────────
  bg: "#0e1016",
  bgSecondary: "#151820",
  bgTertiary: "#1c202a",
  bgCard: "#1a1e28",

  // ── Text ─────────────────────────────────────────────
  textPrimary: "#e2e4e9",
  textSecondary: "#9aa3b5",
  textTertiary: "#6b7489",

  // ── Borders ──────────────────────────────────────────
  border: "#2a3042",
  borderHover: "#3a4058",

  // ── Accent: Green (primary) ──────────────────────────
  green: "#00C49A",
  greenGlow: "rgba(0, 196, 154, 0.4)",
  greenDim: "rgba(0, 196, 154, 0.15)",

  // ── Accent: Orange (secondary) ───────────────────────
  orange: "#D97757",
  orangeGlow: "rgba(217, 119, 87, 0.4)",

  // ── Accent: Gold (tertiary / evolution) ──────────────
  gold: "#c8a84e",
  goldGlow: "rgba(200, 168, 78, 0.4)",
  goldDim: "rgba(200, 168, 78, 0.15)",

  // ── Misc ─────────────────────────────────────────────
  red: "#FF4D4D",
  purple: "#9B59B6",

  // ── Typography ───────────────────────────────────────
  fontMono: "'JetBrains Mono', 'Consolas', monospace",
  fontSerif: "'Instrument Serif', Georgia, serif",

  // ── Canvas (16:9 — landscape widescreen) ─────────────
  width: 1920,
  height: 1080,
} as const;
