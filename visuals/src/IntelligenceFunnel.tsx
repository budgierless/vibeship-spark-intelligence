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
//  REAL DATA
// ════════════════════════════════════════════════════════

const FUNNEL = [
  { count: 4516, label: "TWEETS SCANNED", desc: "18 vibe coding topics" },
  { count: 68, label: "WENT VIRAL", desc: "50+ likes threshold" },
  { count: 58, label: "LLM-ANALYZED", desc: "phi4-mini extraction" },
  { count: 5, label: "PATTERNS FOUND", desc: "quality gate" },
];

const TOPICS = [
  { name: "Claude Ecosystem", hits: 39, pct: 0.83 },
  { name: "Frontier AI", hits: 10, pct: 0.22 },
  { name: "MCP / Tool Use", hits: 4, pct: 0.08 },
  { name: "Building in Public", hits: 2, pct: 0.04 },
  { name: "Vibe Coding", hits: 1, pct: 0.02 },
];

const TRIGGERS = [
  { name: "curiosity gap", count: 41, avg: 2490, pct: 0.87 },
  { name: "surprise", count: 37, avg: 2545, pct: 0.79 },
  { name: "social proof", count: 22, avg: 2595, pct: 0.47 },
  { name: "validation", count: 39, avg: 2419, pct: 0.83 },
  { name: "contrast", count: 27, avg: 1890, pct: 0.57 },
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
    <div style={{ opacity: ent, display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
      <div style={{
        width: 8, height: 8, background: T.green, borderRadius: "50%",
        boxShadow: `0 0 12px ${T.greenGlow}`,
        opacity: 0.6 + 0.4 * Math.sin(frame * 0.1),
      }} />
      <span style={{
        fontFamily: T.fontMono, fontSize: 13, fontWeight: 500,
        letterSpacing: 4, textTransform: "uppercase" as const, color: T.green,
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
    <div style={{ opacity: ent, transform: `translateX(${(1 - ent) * 30}px)`, marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
        <span style={{ fontFamily: T.fontMono, fontSize: 17, color: T.textPrimary, fontWeight: 500 }}>{label}</span>
        <span style={{ fontFamily: T.fontMono, fontSize: 17, color, fontWeight: 700 }}>{value}</span>
      </div>
      <div style={{ width: "100%", height: 7, background: T.bgTertiary, overflow: "hidden" }}>
        <div style={{
          width: `${pct * 100 * grow}%`, height: "100%",
          background: color, boxShadow: `0 0 10px ${color}55`,
        }} />
      </div>
      {sub && <div style={{ fontFamily: T.fontMono, fontSize: 13, color: T.textTertiary, marginTop: 3 }}>{sub}</div>}
    </div>
  );
};

const Attribution: React.FC<{ delay?: number }> = ({ delay = 0 }) => {
  const frame = useCurrentFrame();
  const op = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{
      position: "absolute", bottom: 30, left: 0, right: 0,
      display: "flex", alignItems: "center", justifyContent: "center", gap: 10, opacity: op,
    }}>
      <div style={{ width: 7, height: 7, background: T.green, borderRadius: "50%", boxShadow: `0 0 8px ${T.greenGlow}` }} />
      <span style={{ fontFamily: T.fontMono, fontSize: 13, letterSpacing: 3, color: T.textTertiary }}>@Spark_coded</span>
    </div>
  );
};

// ════════════════════════════════════════════════════════
//  SCENE 1: FUNNEL (0–4s) — two-column landscape
// ════════════════════════════════════════════════════════

const SceneFunnel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titleOp = interpolate(frame, [5, 22], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [5, 22], [18, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ padding: "55px 80px", display: "flex", flexDirection: "row", gap: 70 }}>
      {/* Left: title + signal rate */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Label text="Intelligence Funnel" delay={2} />
        <div style={{ opacity: titleOp, transform: `translateY(${titleY}px)` }}>
          <div style={{ fontFamily: T.fontSerif, fontSize: 50, fontWeight: 400, color: T.textPrimary, lineHeight: 1.15 }}>
            What Survives{"\n"}When an AI{" "}
            <span style={{ color: T.green, textShadow: `0 0 30px ${T.greenGlow}` }}>Studies You</span>
          </div>
          <div style={{
            fontFamily: T.fontMono, fontSize: 15, color: T.textSecondary, marginTop: 14,
            opacity: interpolate(frame, [18, 32], [0, 1], { extrapolateRight: "clamp" }),
          }}>
            13 sessions · 18 vibe coding topics
          </div>
        </div>

        {/* Signal rate */}
        <div style={{
          marginTop: 44,
          opacity: interpolate(frame, [88, 102], [0, 1], { extrapolateRight: "clamp" }),
          display: "flex", alignItems: "center", gap: 22,
        }}>
          <div style={{
            fontFamily: T.fontMono, fontSize: 64, fontWeight: 800,
            color: T.green, textShadow: `0 0 30px ${T.greenGlow}`, lineHeight: 1,
          }}>0.11%</div>
          <div>
            <div style={{ fontFamily: T.fontMono, fontSize: 11, letterSpacing: 2, color: T.textTertiary, textTransform: "uppercase" as const }}>SIGNAL RATE</div>
            <div style={{ fontFamily: T.fontSerif, fontSize: 22, fontStyle: "italic", color: T.textSecondary, marginTop: 3 }}>99.89% was noise</div>
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
                <div style={{ textAlign: "center", padding: "6px 0", fontFamily: T.fontMono, fontSize: 12, color: T.textTertiary, opacity: ent }}>▼</div>
              )}
              <div style={{
                opacity: ent, transform: `translateY(${(1 - ent) * 18}px)`,
                background: T.bgCard, border: `1px solid ${T.border}`,
                padding: "16px 24px",
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}>
                <div>
                  <div style={{ fontFamily: T.fontMono, fontSize: 15, fontWeight: 600, color: T.textPrimary, letterSpacing: 1 }}>{stage.label}</div>
                  <div style={{ fontFamily: T.fontMono, fontSize: 12, color: T.textTertiary, marginTop: 3 }}>{stage.desc}</div>
                </div>
                <div style={{ fontFamily: T.fontMono, fontSize: 40, fontWeight: 700, color, textShadow: `0 0 25px ${glow}` }}>
                  <Counter to={stage.count} delay={28 + i * 13} duration={18} />
                </div>
              </div>
            </React.Fragment>
          );
        })}
      </div>

      <Attribution delay={88} />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════
//  SCENE 2: TOPICS (4–7s)
// ════════════════════════════════════════════════════════

const SceneTopics: React.FC = () => {
  const frame = useCurrentFrame();
  const titleOp = interpolate(frame, [5, 22], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [5, 22], [18, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ padding: "55px 80px", display: "flex", flexDirection: "row", gap: 70 }}>
      {/* Left: title + callout */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Label text="Research Scope" delay={2} />
        <div style={{ opacity: titleOp, transform: `translateY(${titleY}px)` }}>
          <div style={{ fontFamily: T.fontSerif, fontSize: 46, fontWeight: 400, color: T.textPrimary, lineHeight: 1.2 }}>
            We studied the{"\n"}
            <span style={{ color: T.green, textShadow: `0 0 30px ${T.greenGlow}` }}>vibe coding{"\n"}ecosystem</span>
          </div>
          <div style={{
            fontFamily: T.fontMono, fontSize: 15, color: T.textSecondary, marginTop: 14,
            opacity: interpolate(frame, [15, 28], [0, 1], { extrapolateRight: "clamp" }),
          }}>
            from Claude Code to AGI. one dominated.
          </div>
        </div>

        {/* Callout */}
        <div style={{
          marginTop: 36,
          background: T.bgCard, border: `1px solid ${T.border}`, borderLeft: `3px solid ${T.green}`,
          padding: "20px 24px",
          opacity: interpolate(frame, [62, 76], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateY(${interpolate(frame, [62, 76], [12, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{ fontFamily: T.fontSerif, fontSize: 24, color: T.textPrimary, lineHeight: 1.4 }}>
            Claude ecosystem:{" "}
            <span style={{ color: T.green }}>83%</span> of all viral signal.
          </div>
          <div style={{ fontFamily: T.fontMono, fontSize: 14, color: T.textSecondary, marginTop: 8 }}>
            "Vibe coding" only produced 1 viral tweet out of 47.
          </div>
        </div>
      </div>

      {/* Right: bars */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        {TOPICS.map((t, i) => (
          <Bar
            key={i}
            label={t.name}
            value={`${t.hits} viral`}
            pct={t.pct}
            color={i === 0 ? T.green : i === 1 ? T.green : T.textTertiary}
            delay={20 + i * 8}
          />
        ))}
      </div>

      <Attribution delay={62} />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════
//  SCENE 3: TRIGGERS + 4x (7–11s)
// ════════════════════════════════════════════════════════

const SceneTriggers: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titleOp = interpolate(frame, [5, 22], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [5, 22], [18, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ padding: "55px 80px", display: "flex", flexDirection: "row", gap: 60 }}>
      {/* Left: title + triggers */}
      <div style={{ flex: 1.1, display: "flex", flexDirection: "column" }}>
        <Label text="What Makes Tweets Go Viral" delay={2} />
        <div style={{ opacity: titleOp, transform: `translateY(${titleY}px)`, marginBottom: 28 }}>
          <div style={{ fontFamily: T.fontSerif, fontSize: 44, fontWeight: 400, color: T.textPrimary, lineHeight: 1.2 }}>
            Emotional{" "}
            <span style={{ color: T.green, textShadow: `0 0 30px ${T.greenGlow}` }}>Triggers</span>
            {" That Win"}
          </div>
          <div style={{
            fontFamily: T.fontMono, fontSize: 14, color: T.textSecondary, marginTop: 10,
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
            sub={`${t.count}/47 tweets`}
          />
        ))}
      </div>

      {/* Right: 4x highlight */}
      <div style={{ flex: 0.9, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div style={{
          background: T.bgCard, border: `1px solid ${T.border}`, borderLeft: `4px solid ${T.green}`,
          padding: "36px 32px",
          opacity: interpolate(frame, [55, 70], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateX(${interpolate(frame, [55, 70], [30, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{
            fontFamily: T.fontMono, fontSize: 96, fontWeight: 800,
            color: T.green, textShadow: `0 0 40px ${T.greenGlow}`, lineHeight: 1,
            marginBottom: 20,
          }}>4x</div>
          <div style={{ fontFamily: T.fontMono, fontSize: 22, fontWeight: 600, color: T.textPrimary, lineHeight: 1.3 }}>
            Long tweets destroy{"\n"}short ones
          </div>
          <div style={{ marginTop: 20 }}>
            <div style={{ fontFamily: T.fontMono, fontSize: 18, color: T.textSecondary }}>
              Long: <span style={{ color: T.green, fontWeight: 700, fontSize: 26 }}>2,299</span> avg likes
            </div>
            <div style={{ fontFamily: T.fontMono, fontSize: 18, color: T.textTertiary, marginTop: 6 }}>
              Short: <span style={{ fontWeight: 600 }}>560</span> avg likes
            </div>
          </div>
          <div style={{ fontFamily: T.fontMono, fontSize: 13, color: T.textTertiary, marginTop: 16 }}>
            45 of 47 top performers were long-form
          </div>
        </div>
      </div>

      <Attribution delay={55} />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════
//  SCENE 4: THE REVEAL (11–14s)
// ════════════════════════════════════════════════════════

const SceneReveal: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ padding: "55px 80px", display: "flex", flexDirection: "row", gap: 60, alignItems: "center" }}>
      {/* Left: the big statement */}
      <div style={{ flex: 1 }}>
        <div style={{
          opacity: interpolate(frame, [3, 14], [0, 1], { extrapolateRight: "clamp" }),
          fontFamily: T.fontMono, fontSize: 13, letterSpacing: 4,
          textTransform: "uppercase" as const, color: T.green, marginBottom: 24,
        }}>
          the pattern that outperformed everything
        </div>

        <div style={{
          opacity: interpolate(frame, [10, 28], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateY(${interpolate(frame, [10, 28], [20, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{
            fontFamily: T.fontSerif, fontSize: 50, fontWeight: 400,
            color: T.textPrimary, lineHeight: 1.25,
          }}>
            People don't want{"\n"}to be{" "}
            <span style={{ color: T.textTertiary, textDecoration: "line-through", textDecorationColor: T.textTertiary }}>taught</span>
            .{"\n\n"}They want to be{" "}
            <span style={{ color: T.green, textShadow: `0 0 35px ${T.greenGlow}` }}>shown</span>.
          </div>
        </div>

        {/* Kicker */}
        <div style={{
          marginTop: 36,
          opacity: interpolate(frame, [48, 60], [0, 1], { extrapolateRight: "clamp" }),
          transform: `translateY(${interpolate(frame, [48, 60], [12, 0], { extrapolateRight: "clamp" })}px)`,
        }}>
          <div style={{ fontFamily: T.fontSerif, fontSize: 21, fontStyle: "italic", color: T.textSecondary, lineHeight: 1.5 }}>
            "The most viral tweet? Someone confessing they knew{" "}
            <span style={{ color: T.orange }}>nothing</span> about coding — then showing what they built."
          </div>
          <div style={{
            fontFamily: T.fontMono, fontSize: 32, fontWeight: 800,
            color: T.orange, textShadow: `0 0 20px ${T.orangeGlow}`, marginTop: 12,
          }}>12,706 likes.</div>
        </div>
      </div>

      {/* Right: strategy card */}
      <div style={{
        flex: 0.8, display: "flex", flexDirection: "column", justifyContent: "center",
        opacity: interpolate(frame, [26, 40], [0, 1], { extrapolateRight: "clamp" }),
        transform: `translateX(${interpolate(frame, [26, 40], [30, 0], { extrapolateRight: "clamp" })}px)`,
      }}>
        <div style={{
          background: T.bgCard, border: `1px solid ${T.border}`, borderLeft: `4px solid ${T.green}`,
          padding: "32px 28px",
        }}>
          <div style={{
            fontFamily: T.fontMono, fontSize: 12, letterSpacing: 2,
            color: T.green, textTransform: "uppercase" as const, marginBottom: 16,
          }}>ANNOUNCEMENT + STORYTELLING</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
            <div style={{
              fontFamily: T.fontMono, fontSize: 64, fontWeight: 800,
              color: T.green, textShadow: `0 0 30px ${T.greenGlow}`, lineHeight: 1,
            }}>
              <Counter to={6086} delay={30} duration={22} />
            </div>
          </div>
          <div style={{ fontFamily: T.fontMono, fontSize: 16, color: T.textSecondary, marginTop: 6 }}>avg engagement</div>
          <div style={{ width: "100%", height: 1, background: T.border, margin: "18px 0" }} />
          <div style={{ fontFamily: T.fontMono, fontSize: 16, color: T.textSecondary, lineHeight: 1.6 }}>
            Announce something new.{"\n"}Then{" "}
            <span style={{ color: T.textPrimary }}>wrap it in a story{"\n"}people can feel</span>.
          </div>
        </div>
      </div>

      <Attribution delay={48} />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════
//  TRANSITIONS — slide up
// ════════════════════════════════════════════════════════

const SlideTransition: React.FC<{ at: number }> = ({ at }) => {
  const frame = useCurrentFrame();
  if (frame < at - 8 || frame > at + 10) return null;
  const progress = interpolate(frame, [at - 8, at - 1, at + 3, at + 10], [1, 0, 0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  return (
    <div style={{
      position: "absolute", left: 0, right: 0, bottom: 0, zIndex: 50, height: "100%",
      background: `linear-gradient(to top, ${T.bg} 0%, ${T.bg} 90%, transparent 100%)`,
      transform: `translateY(${progress * 100}%)`,
    }} />
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

      <Sequence from={0} durationInFrames={125}><SceneFunnel /></Sequence>
      <SlideTransition at={120} />
      <Sequence from={125} durationInFrames={90}><SceneTopics /></Sequence>
      <SlideTransition at={210} />
      <Sequence from={215} durationInFrames={120}><SceneTriggers /></Sequence>
      <SlideTransition at={330} />
      <Sequence from={335} durationInFrames={85}><SceneReveal /></Sequence>
    </AbsoluteFill>
  );
};
