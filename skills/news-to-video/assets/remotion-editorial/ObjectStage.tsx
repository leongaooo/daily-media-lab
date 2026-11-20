/** Persistent object stage. Cue-bound actions change state, never object identity.
 * Coordinates belong to a 1600x560 visual world, clipped above the subtitle rail.
 */
import React from "react";
import { Img, staticFile } from "remotion";

type Palette = Record<string, string>;
type Actor = {
  id: string;
  kind: string;
  label: string;
  x: number;
  y: number;
  tone?: string;
  value?: number;
  asset?: string;
  scale?: number;
};
type Action = {
  type: string;
  target: string;
  to?: string;
  x?: number;
  y?: number;
  label?: string;
  tone?: string;
  value?: number;
  start_frame: number;
  end_frame: number;
};
type Stage = {
  objects: Actor[];
  actions: Action[];
  connections?: { from: string; to: string; evidence: string }[];
  groups?: {
    x: number;
    y: number;
    width: number;
    height: number;
    label: string;
  }[];
  surface?: string;
  ink?: string;
  shadow?: boolean;
};
export type StageProps = {
  stage: Stage;
  frame: number;
  palette: Palette;
  view?: number[];
  previousView?: number[];
  shotFrame: number;
};

const clamp = (value: number) => Math.max(0, Math.min(1, value));
const ease = (value: number) => {
  const progress = clamp(value);
  return progress * progress * (3 - 2 * progress);
};
const progressAt = (action: Action, frame: number) =>
  ease((frame - action.start_frame) / (action.end_frame - action.start_frame));
const mix = (from: number, to: number, progress: number) =>
  from + (to - from) * progress;

/** Local SVG glyphs provide reusable shapes; labels and values remain editable. */
const Glyph: React.FC<{
  kind: string;
  color: string;
  surface: string;
  value: number;
}> = ({ kind, color, surface, value }) => {
  if (kind === "queue") {
    return (
      <g fill={surface} stroke={color} strokeWidth={3}>
        <rect x={-135} y={-57} width={270} height={114} rx={25} />
        <path d="M-44 -42 V42 M44 -42 V42" opacity={0.35} />
        <path d="M-155 0 H-142 M142 0 H155" strokeWidth={5} />
      </g>
    );
  }
  if (kind === "database") {
    return (
      <g fill={surface} stroke={color} strokeWidth={4}>
        <path d="M-60 -44 V42 C-60 68 60 68 60 42 V-44" />
        <ellipse cy={-44} rx={60} ry={19} />
        <path
          d="M-60 -5 C-60 21 60 21 60 -5 M-60 26 C-60 52 60 52 60 26"
          fill="none"
        />
      </g>
    );
  }
  if (kind === "message") {
    return (
      <g fill={surface} stroke={color} strokeWidth={4}>
        <rect x={-60} y={-40} width={120} height={80} rx={10} />
        <path
          d="M-55 -34 L0 10 L55 -34 M-55 34 L-18 0 M55 34 L18 0"
          fill="none"
        />
      </g>
    );
  }
  if (kind === "phone") {
    return (
      <g stroke={color} strokeWidth={4}>
        <rect x={-43} y={-73} width={86} height={146} rx={17} fill={surface} />
        <path d="M-15 -58 H15 M-12 57 H12" />
        <rect
          x={-29}
          y={-35}
          width={58}
          height={58}
          rx={8}
          fill={color}
          fillOpacity={0.16}
        />
        <path d="M0 12 V-20 M-12 -8 L0 -20 L12 -8" fill="none" />
      </g>
    );
  }
  if (kind === "bar") {
    return (
      <g>
        <rect
          x={-75}
          y={-55}
          width={150}
          height={110}
          rx={16}
          fill={surface}
          stroke={color}
          strokeWidth={3}
        />
        <path d="M-52 25 H52" stroke={color} strokeWidth={3} />
        <rect
          x={-20}
          y={25 - value * 0.8}
          width={40}
          height={value * 0.8}
          fill={color}
          rx={4}
        />
      </g>
    );
  }
  if (kind === "building") {
    return (
      <g stroke={color} strokeWidth={3} fill={surface}>
        <path d="M-70 55 V-35 L0 -65 L70 -35 V55 Z" />
        {[-40, 0, 40].map((x) => (
          <g key={x}>
            <path d={`M${x} -18 V35`} strokeWidth={12} />
          </g>
        ))}
        <path d="M-82 55 H82" strokeWidth={6} />
      </g>
    );
  }
  if (kind === "document") {
    return (
      <g stroke={color} strokeWidth={4} fill={surface}>
        <path d="M-48 -65 H22 L48 -39 V65 H-48 Z" />
        <path
          d="M22 -65 V-39 H48 M-28 -16 H28 M-28 7 H28 M-28 30 H12"
          fill="none"
        />
      </g>
    );
  }
  if (kind === "server") {
    return (
      <g fill={surface} stroke={color} strokeWidth={3}>
        {[-48, -8, 32].map((y) => (
          <g key={y}>
            <rect x={-62} y={y} width={124} height={32} rx={7} />
            <path
              d={`M-45 ${y + 11} V${y + 21} M-32 ${y + 11} V${y + 21} M-19 ${y + 11} V${y + 21}`}
            />
            <circle cx={42} cy={y + 16} r={4} fill={color} />
          </g>
        ))}
      </g>
    );
  }
  return (
    <rect
      x={-75}
      y={-48}
      width={150}
      height={96}
      rx={kind === "note" ? 28 : 12}
      fill={surface}
      stroke={color}
      strokeWidth={3}
    />
  );
};

export const ObjectStage: React.FC<StageProps> = ({
  stage,
  frame,
  palette,
  view = [0, 0, 1600, 560],
  previousView = [0, 0, 1600, 560],
  shotFrame,
}) => {
  const ink = stage.ink ?? "#F7F9FC";
  const surface = stage.surface ?? palette.background;
  // Resolve the full scene history, rather than resetting state at a shot boundary.
  const actors = stage.objects.map((object) => {
    let x = object.x;
    let y = object.y;
    let label = object.label;
    let tone = object.tone ?? "primary";
    let value = object.value ?? 0;
    let opacity = stage.actions.some(
      (a) => a.target === object.id && a.type === "enter",
    )
      ? 0
      : 1;
    let emphasis = 0;
    for (const action of stage.actions.filter((a) => a.target === object.id)) {
      if (frame < action.start_frame) continue;
      const progress = progressAt(action, frame);
      if (action.type === "move") {
        x = mix(x, action.x!, progress);
        y = mix(y, action.y!, progress);
      }
      if (action.type === "enter") opacity = progress;
      if (action.type === "exit") opacity = 1 - progress;
      if (action.type === "value") value = mix(value, action.value!, progress);
      if (action.type === "state" && progress >= 0.5) {
        label = action.label ?? label;
        tone = action.tone ?? tone;
      }
      if (action.type === "emphasize" && frame <= action.end_frame)
        emphasis = Math.sin(progress * Math.PI);
    }
    return { ...object, x, y, label, tone, value, opacity, emphasis };
  });
  const lookup = (id: string) => actors.find((object) => object.id === id)!;
  const cameraProgress = ease(shotFrame / 14);
  const viewport = view.map((value, i) =>
    mix(previousView[i], value, cameraProgress),
  );
  return (
    <svg
      width="100%"
      height="100%"
      viewBox={viewport.join(" ")}
      style={{ overflow: "hidden" }}
    >
      <defs>
        <filter id="object-shadow" x="-40%" y="-40%" width="180%" height="200%">
          <feDropShadow
            dx="0"
            dy="9"
            stdDeviation="8"
            floodColor="#000000"
            floodOpacity="0.18"
          />
        </filter>
        <marker
          id="object-arrow"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path
            d="M0 0 L10 5 L0 10"
            fill="none"
            stroke={palette.muted}
            strokeWidth="1.8"
          />
        </marker>
      </defs>
      {(stage.groups ?? []).map((group, index) => (
        <g key={index}>
          <rect
            x={group.x}
            y={group.y}
            width={group.width}
            height={group.height}
            rx={26}
            fill={surface}
            stroke={palette.muted}
            strokeWidth={2}
          />
          <text
            x={group.x + 24}
            y={group.y + 38}
            fill={ink}
            fontSize={25}
            fontWeight={700}
          >
            {group.label}
          </text>
        </g>
      ))}
      {(stage.connections ?? []).map((edge, index) => {
        const from = lookup(edge.from),
          to = lookup(edge.to);
        const dx = to.x - from.x,
          dy = to.y - from.y;
        const length = Math.max(1, Math.hypot(dx, dy));
        const inset = Math.min(88, length / 3);
        return (
          <line
            key={index}
            x1={from.x + (dx / length) * inset}
            y1={from.y + (dy / length) * inset}
            x2={to.x - (dx / length) * inset}
            y2={to.y - (dy / length) * inset}
            stroke={palette.muted}
            strokeWidth={2.5}
            opacity={Math.min(from.opacity, to.opacity)}
            markerEnd="url(#object-arrow)"
          />
        );
      })}
      {stage.actions
        .filter(
          (a) =>
            a.type === "transfer" &&
            frame >= a.start_frame &&
            frame <= a.end_frame,
        )
        .map((action, index) => {
          const from = lookup(action.target),
            to = lookup(action.to!);
          const progress = progressAt(action, frame);
          return (
            <g
              key={index}
              transform={`translate(${mix(from.x, to.x, progress)} ${mix(from.y, to.y, progress)})`}
            >
              <circle
                r={16}
                fill={palette.accent}
                stroke={surface}
                strokeWidth={5}
              />
              {action.label ? (
                <text y={-28} textAnchor="middle" fontSize={24} fill={ink}>
                  {action.label}
                </text>
              ) : null}
            </g>
          );
        })}
      {actors.map((actor) => {
        const tint = palette[actor.tone];
        return (
          <g
            key={actor.id}
            transform={`translate(${actor.x} ${actor.y})`}
            opacity={actor.opacity}
          >
            <ellipse
              cy={95}
              rx={80}
              ry={9}
              fill={palette.muted}
              opacity={0.12}
            />
            {actor.emphasis > 0 ? (
              <rect
                x={-99}
                y={-100}
                width={198}
                height={215}
                rx={24}
                fill="none"
                stroke={palette.accent}
                strokeWidth={3 + actor.emphasis * 3}
                opacity={actor.emphasis}
              />
            ) : null}
            <g
              filter={
                stage.shadow === false ? undefined : "url(#object-shadow)"
              }
              transform={`scale(${actor.scale ?? 1})`}
            >
              {actor.asset ? (
                <foreignObject x={-80} y={-80} width={160} height={160}>
                  <Img
                    src={staticFile(actor.asset)}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "contain",
                    }}
                  />
                </foreignObject>
              ) : (
                <Glyph
                  kind={actor.kind}
                  color={tint}
                  surface={surface}
                  value={actor.value}
                />
              )}
            </g>
            <text
              y={actor.kind === "message" ? 68 : 130}
              textAnchor="middle"
              fill={ink}
              fontSize={28}
              fontWeight={700}
            >
              {actor.label}
            </text>
            {actor.kind === "bar" ? (
              <text
                y={-82}
                textAnchor="middle"
                fill={tint}
                fontSize={30}
                fontWeight={700}
              >
                {Math.round(actor.value)}
              </text>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
};
