import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type MainProps = { cloudMinutes: number; localSeconds: number };

const C = { ink: "#0b0d17", card: "#151a2e", line: "#262d4a", lime: "#c6ff3d", coral: "#ff5c39", paper: "#f4f1ea", mute: "#7d84a3" };
const FONT = '"Helvetica Neue", Helvetica, Arial, sans-serif';

const clock = (s: number) => {
  const m = Math.floor(s / 60);
  const r = Math.floor(s % 60);
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
};

const Title: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14, mass: 0.8 } });
  const out = interpolate(frame, [40, 55], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: "0 200px", opacity: 1 - out }}>
      <div style={{ color: C.mute, fontSize: 34, letterSpacing: 8, fontWeight: 700, transform: `translateY(${(1 - s) * 40}px)` }}>
        SAME VIDEO
      </div>
      <div style={{ color: C.paper, fontSize: 150, fontWeight: 900, letterSpacing: -5, lineHeight: 1,
        transform: `translateY(${(1 - s) * 90 - out * 60}px)`, opacity: s }}>
        Two machines.
      </div>
    </AbsoluteFill>
  );
};

const Card: React.FC<{
  delay: number; label: string; spec: string; color: string; elapsed: number; progress: number; doneText?: string;
}> = ({ delay, label, spec, color, elapsed, progress, doneText }) => {
  const frame = useCurrentFrame() - delay;
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 16 } });
  const done = progress >= 1;
  return (
    <div style={{
      flex: 1, background: C.card, border: `2px solid ${done ? color : C.line}`, borderRadius: 36, padding: "56px 60px",
      transform: `translateY(${(1 - enter) * 120}px) scale(${0.94 + 0.06 * enter})`, opacity: enter,
    }}>
      <div style={{ color: C.mute, fontSize: 28, fontWeight: 700, letterSpacing: 5 }}>{label.toUpperCase()}</div>
      <div style={{ color: C.paper, fontSize: 30, marginTop: 14 }}>{spec}</div>
      <div style={{ color, fontSize: 168, fontWeight: 900, letterSpacing: -4, marginTop: 40, fontVariantNumeric: "tabular-nums" }}>
        {done && doneText ? doneText : clock(elapsed)}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", color: C.mute, fontSize: 28, marginTop: 8 }}>
        <span>{done ? "finished in " + clock(elapsed) : "rendering…"}</span>
        <span style={{ fontVariantNumeric: "tabular-nums" }}>{Math.floor(Math.min(1, progress) * 100)}%</span>
      </div>
      <div style={{ height: 16, background: C.line, borderRadius: 8, marginTop: 18, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(1, progress) * 100}%`, height: "100%", background: color, borderRadius: 8 }} />
      </div>
    </div>
  );
};

const Punchline: React.FC<{ factor: number }> = ({ factor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 9, stiffness: 120 } });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 90 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 28, transform: `scale(${0.6 + 0.4 * s})`, opacity: Math.min(1, s * 1.5) }}>
        <span style={{ color: C.lime, fontSize: 120, fontWeight: 900, letterSpacing: -4 }}>{factor}× faster</span>
        <span style={{ color: C.mute, fontSize: 36 }}>on the machine you already own</span>
      </div>
    </AbsoluteFill>
  );
};

export const Main: React.FC<MainProps> = ({ cloudMinutes, localSeconds }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const glow = interpolate(frame, [0, durationInFrames], [0, 360]);
  // one simulated wall clock for both machines: 0 -> localSeconds over 45 frames
  const sim = interpolate(frame, [62, 107], [0, localSeconds], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad),
  });
  return (
    <AbsoluteFill style={{
      fontFamily: FONT,
      background: `radial-gradient(circle at ${60 + 20 * Math.sin((glow * Math.PI) / 180)}% 30%, #1b2140 0%, ${C.ink} 60%)`,
    }}>
      <Sequence durationInFrames={56}>
        <Title />
      </Sequence>
      <Sequence from={48}>
        <AbsoluteFill style={{ flexDirection: "row", alignItems: "flex-start", gap: 60, padding: "190px 160px 0" }}>
          <Card delay={0} label="Cloud sandbox" spec="2 CPU cores · no GPU" color={C.coral}
            elapsed={sim} progress={sim / (cloudMinutes * 60)} />
          <Card delay={6} label="Your laptop" spec="Apple Silicon · VideoToolbox" color={C.lime}
            elapsed={sim} progress={sim / localSeconds} doneText="DONE ✓" />
        </AbsoluteFill>
      </Sequence>
      <Sequence from={112}>
        <Punchline factor={Math.round((cloudMinutes * 60) / localSeconds)} />
      </Sequence>
    </AbsoluteFill>
  );
};
