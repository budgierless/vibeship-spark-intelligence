import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
} from "remotion";
import { SPARK_THEME as T } from "./theme";
import { loadFonts } from "./fonts";

loadFonts();

// ════════════════════════════════════════════════════════
//  DATA
// ════════════════════════════════════════════════════════

const FUNNEL = [
  { count: 4516, label: "TWEETS SCANNED", desc: "vibe coding, Claude, AI agents, MCP, AGI..." },
  { count: 68, label: "WENT VIRAL", desc: "50+ likes engagement threshold" },
  { count: 58, label: "LLM-ANALYZED", desc: "phi4-mini pattern extraction" },
  { count: 5, label: "PATTERNS FOUND", desc: "quality gate distillation" },
];

const TRIGGERS = [
  { name: "curiosity gap", what: "open a question they need answered", count: 41, avg: 2490, pct: 0.87 },
  { name: "surprise", what: "say something that breaks assumptions", count: 37, avg: 2545, pct: 0.79 },
  { name: "social proof", what: "show that others already believe this", count: 22, avg: 2595, pct: 0.47 },
  { name: "validation", what: "confirm what people feel but haven't said", count: 39, avg: 2419, pct: 0.83 },
  { name: "contrast", what: "show a stark before vs after", count: 27, avg: 1890, pct: 0.57 },
];

// ════════════════════════════════════════════════════════
//  HELPERS
// ════════════════════════════════════════════════════════

const Particles: React.FC<{ count: number; seed: number }> = ({ count, seed }) => {
  const frame = useCurrentFrame();
  const pts = React.useMemo(() => {
    const r = (i: number) => Math.sin(seed * 9301 + i * 49297) * 0.5 + 0.5;
    return Array.from({ length: count }, (_, i) => ({
      x: r(i * 3) * 100, y: r(i * 3 + 1) * 100,
      sz: 1 + r(i * 3 + 2) * 1.5, sp: 0.1 + r(i * 7) * 0.3,
      op: 0.05 + r(i * 11) * 0.12,
    }));
  }, [count, seed]);
  return (
    <>
      {pts.map((p, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${p.x}%`,
            top: `${(p.y - frame * p.sp * 0.12 + 200) % 120 - 10}%`,
            width: p.sz, height: p.sz, borderRadius: "50%",
            backgroundColor: T.gold,
            opacity: p.op * (0.7 + 0.3 * Math.sin(frame * 0.04 + i)),
          }}
        />
      ))}
    </>
  );
};

const Counter: React.FC<{
  to: number; delay: number; duration?: number;
  style?: React.CSSProperties;
}> = ({ to, delay, duration = 25, style }) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [delay, delay + duration], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  return <span style={style}>{Math.round(to * progress).toLocaleString()}</span>;
};

const Label: React.FC<{ text: string; delay?: number }> = ({ text, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ent = spring({ fps, frame: frame - delay, config: { damping: 14 } });
  return (
    <div style={{ opacity: ent, display: "flex", alignItems: "center", gap: 12, marginBottom: 18 }}>
      <div style={{
        width: 10, height: 10, background: T.green, borderRadius: "50%",
        boxShadow: `0 0 14px ${T.greenGlow}`,
        opacity: 0.6 + 0.4 * Math.sin(frame * 0.1),
      }} />
      <span style={{
        fontFamily: T.fontMono, fontSize: 22, fontWeight: 500,
        letterSpacing: 5, textTransform: "uppercase" as const, color: T.green,
      }}>{text}</span>
    </div>
  );
};

const Bar: React.FC<{
  label: string; value: string; pct: number;
  color: string; delay: number; sub?: string;
}> = ({ label, value, pct, color, delay, sub }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ent = spring({ fps, frame: frame - delay, config: { damping: 14 } });
  const grow = spring({ fps, frame: frame - delay - 4, config: { damping: 20, mass: 1.2 } });
  return (
    <div style={{ opacity: ent, transform: `translateX(${(1 - ent) * 30}px)`, marginBottom: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontFamily: T.fontMono, fontSize: 26, color: T.textPrimary, fontWeight: 500 }}>{label}</span>
        <span style={{ fontFamily: T.fontMono, fontSize: 26, color, fontWeight: 700 }}>{value}</span>
      </div>
      <div style={{ width: "100%", height: 10, background: T.bgTertiary, overflow: "hidden" }}>
        <div style={{
          width: `${pct * 100 * grow}%`, height: "100%",
          background: color, boxShadow: `0 0 12px ${color}55`,
        }} />
      </div>
      {sub && <div style={{ fontFamily: T.fontMono, fontSize: 20, color: T.textTertiary, marginTop: 4 }}>{sub}</div>}
    </div>
  );
};

const Attribution: React.FC<{ delay?: number }> = ({ delay = 0 }) => {
  const frame = useCurrentFrame();
  const op = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{
      position: "absolute", bottom: 28, left: 0, right: 0,
      display: "flex", alignItems: "center", justifyContent: "center", gap: 12, opacity: op,
    }}>
      <div style={{ width: 9, height: 9, background: T.green, borderRadius: "50%", boxShadow: `0 0 10px ${T.greenGlow}` }} />
      <span style={{ fontFamily: T.fontMono, fontSize: 22, letterSpacing: 4, color: T.textTertiary }}>@Spark_coded</span>
    </div>
  );
};

/**
 * Wraps a scene with fade-in at start and fade-out at end.
 * Scenes overlap so the cross-dissolve is seamless.
 */
const SceneWrap: React.FC<{
  children: React.ReactNode;
  durationInFrames: number;
  fadeIn?: number;
  fadeOut?: number;
}> = ({ children, durationInFrames, fadeIn = 15, fadeOut = 15 }) => {
  const frame = useCurrentFrame();
  let opacity = 1;
  if (fadeIn > 0) {
    opacity = Math.min(opacity, interpolate(frame, [0, fadeIn], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  }
  if (fadeOut > 0) {
    opacity = Math.min(opacity, interpolate(frame, [durationInFrames - fadeOut, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  }
  return (
    <AbsoluteFill style={{ opacity }}>
      {children}
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════
//  SCENE 1: FUNNEL (0–4.5s, frames 0–135)
// ════════════════════════════════════════════════════════

const SceneFunnel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titleOp = interpolate(frame, [5, 22], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [5, 22], [18, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ padding: "45px 70px", display: "flex", flexDirection: "row", gap: 50 }}>
      {/* Left */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Label text="Intelligence Funnel" delay={2} />
        <div style={{ opacity: titleOp, transform: `translateY(${titleY}px)` }}>
          <div style={{ fontFamily: T.fontSerif, fontSize: 78, fontWeight: 400, color: T.textPrimary, lineHeight: 1.1 }}>
            What Survives{"\n"}When an AI{" "}
            <span style={{ color: T.green, textShadow: `0 0 35px ${T.greenGlow}` }}>Studies You</span>
          </div>
        </div>

        <div style={{
          fontFamily: T.fontMono, fontSize: 24, color: T.textSecondary, marginTop: 18, lineHeight: 1.6,
          opacity: interpolate(frame, [18, 33], [0, 1], { extrapolateRight: "clamp" }),
        }}>
          13 sessions across the vibe coding{"\n"}ecosystem — Claude, AI agents, MCP, AGI...
        </div>

        {/* Signal rate */}
        <div style={{
          marginTop: 36,
          opacity: interpolate(frame, [90, 105], [0, 1], { extrapolateRight: "clamp" }),
          display: "flex", alignItems: "center", gap: 24,
        }}>
          <div style={{
            fontFamily: T.fontMono, fontSize: 100, fontWeight: 800,
            color: T.green, textShadow: `0 0 40px ${T.greenGlow}`, lineHeight: 1,
          }}>0.11%</div>
          <div>
            <div style={{ fontFamily: T.fontMono, fontSize: 18, letterSpacing: 3, color: T.textTertiary, textTransform: "uppercase" as const }}>SIGNAL RATE</div>
            <div style={{ fontFamily: T.fontSerif, fontSize: 34, fontStyle: "italic", color: T.textSecondary, marginTop: 4 }}>99.89% was noise</div>
          </div>
        </div>
      </div>

      {/* Right: funnel cards */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        {FUNNEL.map((stage, i) => {
          const ent = spring({ fps, frame: frame - 26 - i * 13, config: { damping: 12, mass: 0.8 } });
          const isBottom = i >= 2;
          const color = isBottom ? T.gold : T.green;
          const glow = isBottom ? T.goldGlow : T.greenGlow;
          return (
            <React.Fragment key={i}>
              {i > 0 && (
                <div style={{ textAlign: "center", padding: "5px 0", fontFamily: T.fontMono, fontSize: 18, color: T.textTertiary, opacity: ent }}>▼</div>
              )}
              <div style={{
                opacity: ent, transform: `translateY(${(1 - ent) * 18}px)`,
                background: T.bgCard, border: `1px solid ${T.border}`,
                padding: "18px 26px",
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}>
                <div>
                  <div style={{ fontFamily: T.fontMono, fontSize: 24, fontWeight: 600, color: T.textPrimary, letterSpacing: 1 }}>{stage.label}</div>
                  <div style={{ fontFamily: T.fontMono, fontSize: 18, color: T.textTertiary, marginTop: 3 }}>{stage.desc}</div>
                </div>
                <div style={{ fontFamily: T.fontMono, fontSize: 64, fontWeight: 700, color, textShadow: `0 0 30px ${glow}` }}>
                  <Counter to={stage.count} delay={28 + i * 13} duration={18} />
                </div>
              </div>
            </React.Fragment>
          );
        })}
      </div>

      <Attribution delay={90} />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════
//  SCENE 2: TRIGGERS (4.5–8s, frames 135–240)
// ════════════════════════════════════════════════════════

const SceneTriggers: React.FC = () => {
  const frame = useCurrentFrame();
  const titleOp = interpolate(frame, [5, 22], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [5, 22], [18, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ padding: "45px 70px", display: "flex", flexDirection: "row", gap: 50 }}>
      {/* Left: triggers */}
      <div style={{ flex: 1.1, display: "flex", flexDirection: "column" }}>
        <Label text="What Makes Tweets Go Viral" delay={2} />
        <div style={{ opacity: titleOp, transform: `translateY(${titleY}px)`, marginBottom: 22 }}>
          <div style={{ fontFamily: T.fontSerif, fontSize: 68, fontWeight: 400, color: T.textPrimary, lineHeight: 1.15 }}>
            Emotional{" "}
            <span style={{ color: T.green, textShadow: `0 0 35px ${T.greenGlow}` }}>Triggers</span>
            {"\n"}That Win
          </div>
          <div style={{
            fontFamily: T.fontMono, fontSize: 22, color: T.textSecondary, marginTop: 10,
            opacity: interpolate(frame, [15, 28], [0, 1], { extrapolateRight: "clamp" }),
          }}>
            from the top 47 viral tweets
          </div>
        </div>

        {TRIGGERS.map((t, i) => (
          <Bar
            key={i}
            label={t.name}
            value={`${t.avg.toLocaleString()} avg`}
            pct={t.pct}
            color={T.green}
            delay={18 + i * 7}
            sub={`${t.what}  ·  ${t.count}/47 tweets`}
          />
        ))}
      </div>

      {/* Right: insight cards */}
      <div style={{ flex: 0.9, display: "flex", flexDirection: "column", justifyContent: "center", gap: 18 }}>
        <div style={{
          background: T.bgCard, border: `1px solid ${T.border}`, borderLeft: `3px solid ${T.green}`,
          padding: "22px 26px",
          opacity: interpolate(frame, [50, 64], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateX(${interpolate(frame, [50, 64], [25, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{ fontFamily: T.fontMono, fontSize: 18, letterSpacing: 2, color: T.green, textTransform: "uppercase" as const, marginBottom: 10 }}>
            #1 INSIGHT
          </div>
          <div style={{ fontFamily: T.fontMono, fontSize: 24, color: T.textPrimary, lineHeight: 1.45 }}>
            Curiosity gaps appeared in <span style={{ color: T.green, fontWeight: 700 }}>87%</span> of viral tweets.
            Make people wonder before you explain.
          </div>
        </div>

        <div style={{
          background: T.bgCard, border: `1px solid ${T.border}`, borderLeft: `3px solid ${T.green}`,
          padding: "22px 26px",
          opacity: interpolate(frame, [62, 76], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateX(${interpolate(frame, [62, 76], [25, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{ fontFamily: T.fontMono, fontSize: 18, letterSpacing: 2, color: T.green, textTransform: "uppercase" as const, marginBottom: 10 }}>
            #2 INSIGHT
          </div>
          <div style={{ fontFamily: T.fontMono, fontSize: 24, color: T.textPrimary, lineHeight: 1.45 }}>
            Surprise beats validation. Tweets that <span style={{ color: T.green, fontWeight: 700 }}>defy expectations</span> get
            5% more engagement.
          </div>
        </div>

        <div style={{
          background: T.bgCard, border: `1px solid ${T.border}`, borderLeft: `3px solid ${T.green}`,
          padding: "22px 26px",
          opacity: interpolate(frame, [74, 88], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateX(${interpolate(frame, [74, 88], [25, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{ fontFamily: T.fontMono, fontSize: 18, letterSpacing: 2, color: T.green, textTransform: "uppercase" as const, marginBottom: 10 }}>
            #3 INSIGHT
          </div>
          <div style={{ fontFamily: T.fontMono, fontSize: 24, color: T.textPrimary, lineHeight: 1.45 }}>
            Social proof has the <span style={{ color: T.green, fontWeight: 700 }}>highest per-tweet avg</span> (2,595)
            but appears less often. Quality over quantity.
          </div>
        </div>
      </div>

      <Attribution delay={50} />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════
//  SCENE 3: 4x + STORYTELLING (8–11.5s, frames 240–345)
// ════════════════════════════════════════════════════════

const SceneFindings: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ padding: "45px 70px", display: "flex", flexDirection: "row", gap: 50, alignItems: "center" }}>
      {/* Left: 4x */}
      <div style={{ flex: 1 }}>
        <Label text="The Data Speaks" delay={2} />

        <div style={{
          opacity: interpolate(frame, [6, 20], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateY(${interpolate(frame, [6, 20], [15, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{ fontFamily: T.fontSerif, fontSize: 64, fontWeight: 400, color: T.textPrimary, lineHeight: 1.15, marginBottom: 28 }}>
            Two findings that{"\n"}
            <span style={{ color: T.green, textShadow: `0 0 35px ${T.greenGlow}` }}>change everything</span>
          </div>
        </div>

        <div style={{
          background: T.bgCard, border: `1px solid ${T.border}`, borderLeft: `4px solid ${T.green}`,
          padding: "28px 28px",
          display: "flex", alignItems: "center", gap: 28,
          opacity: interpolate(frame, [18, 32], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateY(${interpolate(frame, [18, 32], [15, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{
            fontFamily: T.fontMono, fontSize: 140, fontWeight: 800,
            color: T.green, textShadow: `0 0 50px ${T.greenGlow}`, lineHeight: 1, flexShrink: 0,
          }}>4x</div>
          <div style={{ borderLeft: `1px solid ${T.border}`, paddingLeft: 24 }}>
            <div style={{ fontFamily: T.fontMono, fontSize: 30, fontWeight: 600, color: T.textPrimary, lineHeight: 1.3 }}>
              Long tweets destroy short ones
            </div>
            <div style={{ marginTop: 14, fontFamily: T.fontMono, fontSize: 26, color: T.textSecondary }}>
              Long: <span style={{ color: T.green, fontWeight: 700, fontSize: 36 }}>2,299</span> avg
            </div>
            <div style={{ marginTop: 6, fontFamily: T.fontMono, fontSize: 26, color: T.textTertiary }}>
              Short: <span style={{ fontWeight: 600 }}>560</span> avg
            </div>
            <div style={{ fontFamily: T.fontMono, fontSize: 20, color: T.textTertiary, marginTop: 12 }}>
              45 of 47 top performers were long-form
            </div>
          </div>
        </div>
      </div>

      {/* Right: storytelling */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div style={{
          background: T.bgCard, border: `1px solid ${T.border}`, borderLeft: `4px solid ${T.green}`,
          padding: "32px 28px",
          opacity: interpolate(frame, [42, 56], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateX(${interpolate(frame, [42, 56], [30, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{
            fontFamily: T.fontMono, fontSize: 20, letterSpacing: 3,
            color: T.green, textTransform: "uppercase" as const, marginBottom: 18,
          }}>THE WINNING FORMULA</div>

          <div style={{ fontFamily: T.fontSerif, fontSize: 46, color: T.textPrimary, lineHeight: 1.25, marginBottom: 22 }}>
            Announce something new.{"\n"}
            Then <span style={{ color: T.green }}>tell the story</span>.
          </div>

          <div style={{
            fontFamily: T.fontMono, fontSize: 20, letterSpacing: 3,
            color: T.textTertiary, textTransform: "uppercase" as const, marginBottom: 12,
          }}>ANNOUNCEMENT + STORYTELLING</div>

          <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
            <div style={{
              fontFamily: T.fontMono, fontSize: 88, fontWeight: 800,
              color: T.green, textShadow: `0 0 35px ${T.greenGlow}`, lineHeight: 1,
            }}>
              <Counter to={6086} delay={48} duration={22} />
            </div>
            <div style={{ fontFamily: T.fontMono, fontSize: 26, color: T.textSecondary }}>avg engagement</div>
          </div>

          <div style={{ width: "100%", height: 1, background: T.border, margin: "18px 0" }} />

          <div style={{ fontFamily: T.fontMono, fontSize: 24, color: T.textSecondary, lineHeight: 1.5 }}>
            That's the difference between{"\n"}
            <span style={{ color: T.textTertiary }}>615</span> and{" "}
            <span style={{ color: T.green, fontWeight: 700 }}>6,086</span>.
          </div>
        </div>
      </div>

      <Attribution delay={42} />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════
//  SCENE 4: THE REVEAL (10.5–14s, frames 315–420)
// ════════════════════════════════════════════════════════

const SceneReveal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // localhost pulse glow
  const pulse = 0.7 + 0.3 * Math.sin(frame * 0.15);

  return (
    <AbsoluteFill style={{ padding: "45px 70px", display: "flex", flexDirection: "row", gap: 60, alignItems: "center" }}>
      {/* Left: the tweet */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <Label text="The Most Viral Tweet" delay={2} />

        <div style={{
          opacity: interpolate(frame, [6, 20], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateY(${interpolate(frame, [6, 20], [15, 0], { extrapolateRight: "clamp" })}px)`,
          marginBottom: 24,
        }}>
          <div style={{ fontFamily: T.fontSerif, fontSize: 60, fontWeight: 400, color: T.textPrimary, lineHeight: 1.2 }}>
            A <span style={{ color: T.orange, textShadow: `0 0 30px ${T.orangeGlow}` }}>comedy account</span>{"\n"}
            broke every record
          </div>
        </div>

        {/* Stylized tweet card */}
        <div style={{
          background: T.bgCard, border: `1px solid ${T.border}`,
          borderLeft: `4px solid ${T.orange}`,
          padding: "28px 30px",
          opacity: interpolate(frame, [16, 30], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateX(${interpolate(frame, [16, 30], [-30, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{
            fontFamily: T.fontMono, fontSize: 28, color: T.textPrimary, lineHeight: 1.55,
          }}>
            <span style={{ color: T.textSecondary }}>"</span>i know literally{" "}
            <span style={{ color: T.orange, fontWeight: 700 }}>NOTHING</span>{" "}
            about coding. ZERO.
          </div>
          <div style={{
            fontFamily: T.fontMono, fontSize: 28, color: T.textPrimary, lineHeight: 1.55, marginTop: 8,
          }}>
            and i just built a fully functioning web app in minutes.
          </div>

          {/* The punchline */}
          <div style={{
            marginTop: 20, padding: "14px 20px",
            background: `rgba(217, 119, 87, 0.08)`,
            border: `1px solid rgba(217, 119, 87, 0.25)`,
            opacity: interpolate(frame, [32, 44], [0, 1], { extrapolateRight: "clamp" }),
            transform: `scale(${interpolate(frame, [32, 44], [0.95, 1], { extrapolateRight: "clamp" })})`,
          }}>
            <div style={{
              fontFamily: T.fontMono, fontSize: 32, fontWeight: 700,
              color: T.orange, textShadow: `0 0 ${20 * pulse}px ${T.orangeGlow}`,
            }}>
              localhost:3000
            </div>
            <div style={{
              fontFamily: T.fontMono, fontSize: 22, color: T.textTertiary, marginTop: 4,
            }}>
              check it out<span style={{ color: T.textSecondary }}>"</span>
            </div>
          </div>

          <div style={{
            fontFamily: T.fontMono, fontSize: 20, color: T.textTertiary, marginTop: 16,
            opacity: interpolate(frame, [40, 52], [0, 1], { extrapolateRight: "clamp" }),
          }}>
            she knew exactly what she was doing.
          </div>
        </div>
      </div>

      {/* Right: the numbers + insight */}
      <div style={{ flex: 0.85, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div style={{
          opacity: interpolate(frame, [28, 42], [0, 1], { extrapolateRight: "clamp" }),
          transform: `scale(${interpolate(frame, [28, 42], [0.85, 1], { extrapolateRight: "clamp" })})`,
          textAlign: "center", marginBottom: 36,
        }}>
          <div style={{
            fontFamily: T.fontMono, fontSize: 120, fontWeight: 800,
            color: T.green, textShadow: `0 0 50px ${T.greenGlow}`, lineHeight: 1,
          }}>
            <Counter to={12706} delay={30} duration={22} />
          </div>
          <div style={{
            fontFamily: T.fontMono, fontSize: 22, letterSpacing: 4,
            color: T.textTertiary, textTransform: "uppercase" as const, marginTop: 10,
          }}>
            likes on a single tweet
          </div>
        </div>

        <div style={{ width: "100%", height: 1, background: T.border, marginBottom: 32 }} />

        {/* The real insight */}
        <div style={{
          opacity: interpolate(frame, [52, 66], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateY(${interpolate(frame, [52, 66], [15, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{
            fontFamily: T.fontMono, fontSize: 24, color: T.textSecondary, lineHeight: 1.55, marginBottom: 24,
          }}>
            Not a thread. Not a tutorial.{"\n"}
            A <span style={{ color: T.orange, fontWeight: 700 }}>joke</span> — and it outperformed every serious post in our dataset.
          </div>

          <div style={{
            fontFamily: T.fontSerif, fontSize: 46, fontWeight: 400,
            color: T.textPrimary, lineHeight: 1.3,
            opacity: interpolate(frame, [64, 78], [0, 1], { extrapolateRight: "clamp" }),
            transform: `translateY(${interpolate(frame, [64, 78], [10, 0], { extrapolateRight: "clamp" })}px)`,
          }}>
            Make them{" "}
            <span style={{ color: T.textTertiary, textDecoration: "line-through", textDecorationColor: T.textTertiary }}>learn</span>
            ?{" "}Make them{" "}
            <span style={{ color: T.green, textShadow: `0 0 30px ${T.greenGlow}` }}>laugh</span>.
          </div>
        </div>
      </div>

      <Attribution delay={50} />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════
//  MAIN — 14s = 420 frames @ 30fps
// ════════════════════════════════════════════════════════

export const IntelligenceFunnel: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: T.bg, fontFamily: T.fontMono, overflow: "hidden" }}>
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
        background: `radial-gradient(ellipse at center,
          rgba(0, 196, 154, 0.035) 0%,
          rgba(0, 196, 154, 0.012) 35%,
          transparent 60%)`,
      }} />

      <Particles count={20} seed={42} />

      {/* Scenes overlap by 15 frames for smooth cross-dissolve */}
      <Sequence from={0} durationInFrames={135}>
        <SceneWrap durationInFrames={135} fadeIn={0} fadeOut={15}>
          <SceneFunnel />
        </SceneWrap>
      </Sequence>

      <Sequence from={120} durationInFrames={115}>
        <SceneWrap durationInFrames={115} fadeIn={15} fadeOut={15}>
          <SceneTriggers />
        </SceneWrap>
      </Sequence>

      <Sequence from={220} durationInFrames={115}>
        <SceneWrap durationInFrames={115} fadeIn={15} fadeOut={15}>
          <SceneFindings />
        </SceneWrap>
      </Sequence>

      <Sequence from={320} durationInFrames={100}>
        <SceneWrap durationInFrames={100} fadeIn={15} fadeOut={0}>
          <SceneReveal />
        </SceneWrap>
      </Sequence>
    </AbsoluteFill>
  );
};
