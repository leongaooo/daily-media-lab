/** Two project sideboards consume states compiled from the shared integer events.
 * The SVG reference line uses camera-exported pixels; it is an editorial annotation,
 * never a claim of an installed screen, electrical connection or occlusion tracking.
 */
import React from "react";
import { Img, staticFile } from "remotion";

type FrameState = {
  overlay_id: string;
  panel_progress: number;
  prediction_progress?: number;
  task_id?: string;
  task_x?: number;
  task_progress?: number;
  result_visible?: boolean;
  policy_progress?: number;
  caveat_progress?: number[];
  card_progress?: number[];
};
type Overlay = {
  overlay_id: string;
  kind: "cavern-flex-v3" | "idc-status-v3";
  panel: [number, number, number, number];
  title: string;
  identity: string;
  status_label_mode?: "cards" | "header";
  task?: { id: string; label: string; from: number; to: number; width: number };
  caveats?: { text: string; event: string }[];
  cards?: {
    title: string;
    detail: string;
    status: "future" | "reported" | "pending" | "reference";
    event: string;
  }[];
  reference?: { asset: string; label: string };
};
export type JointDirecting = {
  overlays: Overlay[];
  frames: {
    anchor: { x: number; y: number; visible: boolean };
    overlays: FrameState[];
  }[];
};

const ink = "#EDF4F5";
const secondary = "#B8C9D1";
const accent = "#F0BE72";
const teal = "#88D8D0";
const background = "#10222E";
const statusLabels = {
  future: "未来安排",
  reported: "运营方披露",
  pending: "采购方待核",
  reference: "产品参考",
};

/** Measure actual loaded glyphs before capture; no shrink-to-fit or silent clipping. */
export const verifyJointLayout = (
  directing: JointDirecting,
  fontFamily = '"EditorialProjectFont", sans-serif',
) => {
  const probe = document.createElement("span");
  Object.assign(probe.style, {
    position: "fixed",
    left: "-10000px",
    top: "0",
    whiteSpace: "pre",
    fontFamily,
    visibility: "hidden",
  });
  document.body.appendChild(probe);
  try {
    for (const overlay of directing.overlays) {
      const width = overlay.panel[2];
      const entries: { text: string; size: number; available: number }[] = [
        { text: overlay.title, size: 42, available: width - 80 },
        { text: overlay.identity, size: 26, available: width - 80 },
      ];
      if (overlay.kind === "cavern-flex-v3") {
        entries.push(
          { text: overlay.task!.label, size: 30, available: width - 150 },
          { text: "政策方向", size: 42, available: width - 80 },
          ...(overlay.caveats ?? []).map((item) => ({
            text: item.text,
            size: 36,
            available: width - 120,
          })),
        );
      } else {
        entries.push(
          ...(overlay.cards ?? []).flatMap((card) => [
            {
              text: card.title,
              size: overlay.reference ? 26 : 29,
              available: width - 120,
            },
            { text: card.detail, size: 32, available: width - 120 },
          ]),
        );
        if (overlay.reference) {
          entries.push({
            text: overlay.reference.label,
            size: 25,
            available: width - 100,
          });
        }
      }
      for (const entry of entries) {
        probe.style.fontSize = `${entry.size}px`;
        probe.textContent = entry.text;
        // These boards reserve one readable row per label, including IDC cards.
        const bounds = probe.getBoundingClientRect();
        if (
          bounds.width > entry.available + 1 ||
          bounds.height > entry.size * 1.55
        ) {
          throw new Error(
            `Joint overlay ${overlay.overlay_id} text exceeds its panel: ${entry.text}. Shorten the board copy; frozen narration is unchanged.`,
          );
        }
      }
    }
  } finally {
    probe.remove();
  }
};

const Text: React.FC<{
  x: number;
  y: number;
  size?: number;
  fill?: string;
  children: string;
}> = ({ x, y, size = 30, fill = ink, children }) => (
  <text x={x} y={y} fontSize={size} fill={fill}>
    {children.split("\n").map((line, index) => (
      <tspan key={index} x={x} dy={index === 0 ? 0 : size * 1.25}>
        {line}
      </tspan>
    ))}
  </text>
);

/** Persistent task id, width and color survive the planned time-slot change. */
const FlexMechanism: React.FC<{ overlay: Overlay; state: FrameState }> = ({
  overlay,
  state,
}) => {
  const width = overlay.panel[2];
  const plotWidth = width - 155;
  const left = 78;
  const task = overlay.task!;
  if (state.task_id !== task.id) {
    throw new Error("Joint mechanism lost the persistent task identity");
  }
  const priorX = left + plotWidth * task.from;
  const currentX = left + plotWidth * state.task_x!;
  const taskWidth = plotWidth * task.width;
  const closure = state.policy_progress ?? 0;
  const curve = `M ${left} 320 C ${left + plotWidth * 0.15} 320, ${left + plotWidth * 0.22} 348, ${left + plotWidth * 0.35} 296 S ${left + plotWidth * 0.68} 198, ${left + plotWidth} 214`;
  return (
    <>
      <g opacity={1 - closure}>
        <Text x={left} y={174} size={29}>
          预测出力（示意）
        </Text>
        <line
          x1={left}
          y1={354}
          x2={left + plotWidth}
          y2={354}
          stroke="#56707F"
        />
        <Text x={left - 10} y={383} size={24} fill={secondary}>
          较低
        </Text>
        <Text x={left + plotWidth - 48} y={383} size={24} fill={secondary}>
          较高
        </Text>
        <defs>
          <clipPath id={`curve-${overlay.overlay_id}`}>
            <rect
              x={left - 4}
              y={188}
              width={(plotWidth + 8) * state.prediction_progress!}
              height={165}
            />
          </clipPath>
        </defs>
        <path
          d={curve}
          stroke={teal}
          strokeWidth={5}
          fill="none"
          clipPath={`url(#curve-${overlay.overlay_id})`}
        />
        <Text x={left} y={430} size={30}>
          {task.label}
        </Text>
        <line
          x1={left}
          y1={517}
          x2={left + plotWidth}
          y2={517}
          stroke="#56707F"
        />
        <g opacity={Math.min(1, state.task_progress! * 5)}>
          <rect
            x={priorX}
            y={458}
            width={taskWidth}
            height={48}
            rx={5}
            fill="none"
            stroke={secondary}
            strokeWidth={2}
            strokeDasharray="7 6"
          />
          <Text x={priorX} y={550} size={24} fill={secondary}>
            原安排
          </Text>
        </g>
        <g data-task-id={task.id} transform={`translate(${currentX},458)`}>
          <rect width={taskWidth} height={48} rx={5} fill={accent} />
          <Text x={14} y={33} size={25} fill="#14232A">
            任务 A
          </Text>
        </g>
        {state.result_visible ? (
          <>
            <Text x={currentX} y={550} size={24} fill={accent}>
              调整后
            </Text>
            <Text x={left + 100} y={610} size={26} fill={secondary}>
              任务相同，安排时段改变
            </Text>
          </>
        ) : null}
        <Text x={left + plotWidth - 112} y={585} size={25} fill={secondary}>
          时间 →
        </Text>
      </g>
      <g opacity={closure}>
        {(overlay.caveats ?? []).map((caveat, index) => (
          <g
            key={caveat.event}
            opacity={state.caveat_progress?.[index] ?? 0}
            transform={`translate(40,${190 + index * 160})`}
          >
            <rect width={width - 80} height={116} rx={8} fill="#1B3443" />
            <rect width={4} height={116} fill={accent} />
            <Text x={24} y={68} size={36}>
              {caveat.text}
            </Text>
          </g>
        ))}
      </g>
    </>
  );
};

const IdcStatus: React.FC<{ overlay: Overlay; state: FrameState }> = ({
  overlay,
  state,
}) => {
  const width = overlay.panel[2];
  const hasReference = Boolean(overlay.reference);
  return (
    <>
      {overlay.reference ? (
        <>
          <foreignObject x={40} y={140} width={width - 80} height={195}>
            <Img
              src={staticFile(overlay.reference.asset)}
              style={{ width: "100%", height: "100%", objectFit: "contain" }}
            />
          </foreignObject>
          <Text x={40} y={370} size={25} fill={secondary}>
            {overlay.reference.label}
          </Text>
        </>
      ) : null}
      {(overlay.cards ?? []).map((card, index) => (
        <g
          key={card.event}
          opacity={state.card_progress?.[index] ?? 0}
          transform={`translate(40,${hasReference ? 380 + index * 112 : 165 + index * 142})`}
        >
          <line x1={0} y1={0} x2={width - 80} y2={0} stroke="#3E596A" />
          {overlay.status_label_mode !== "header" ? (
            <Text
              x={0}
              y={hasReference ? 24 : 32}
              size={hasReference ? 20 : 22}
              fill={accent}
            >
              {statusLabels[card.status]}
            </Text>
          ) : null}
          <Text x={0} y={hasReference ? 54 : 72} size={hasReference ? 26 : 29}>
            {card.title}
          </Text>
          <Text x={0} y={hasReference ? 92 : 112} size={32}>
            {card.detail}
          </Text>
        </g>
      ))}
    </>
  );
};

export const JointOverlay: React.FC<{
  directing: JointDirecting;
  frame: number;
}> = ({ directing, frame }) => {
  const current = directing.frames[frame];
  if (!current) {
    throw new Error(`Missing compiled joint-directing frame ${frame}`);
  }
  return (
    <svg
      width={1920}
      height={904}
      style={{ position: "absolute", left: 0, top: 0, overflow: "hidden" }}
    >
      {current.overlays.map((state) => {
        const overlay = directing.overlays.find(
          (item) => item.overlay_id === state.overlay_id,
        );
        if (!overlay) {
          throw new Error("Compiled sideboard references an unknown overlay");
        }
        const [x, y, width, height] = overlay.panel;
        const anchor = current.anchor;
        const showAnchor =
          anchor.visible &&
          anchor.x >= 0 &&
          anchor.x < x - 24 &&
          anchor.y >= 100 &&
          anchor.y < 880;
        return (
          <g key={overlay.overlay_id} opacity={state.panel_progress}>
            {showAnchor ? (
              <g stroke={teal} strokeWidth={2} fill="none" opacity={0.7}>
                <circle cx={anchor.x} cy={anchor.y} r={6} />
                <path
                  d={`M ${anchor.x + 8} ${anchor.y} L ${x - 28} ${anchor.y} L ${x - 28} ${y + 66} L ${x} ${y + 66}`}
                />
              </g>
            ) : null}
            <g
              transform={`translate(${x},${y + (1 - state.panel_progress) * 14})`}
            >
              <rect width={width} height={height} rx={12} fill={background} />
              <rect x={0} y={0} width={width} height={3} fill={accent} />
              <Text x={40} y={64} size={42}>
                {(state.policy_progress ?? 0) > 0.5
                  ? "政策方向"
                  : overlay.title}
              </Text>
              <Text x={40} y={108} size={26} fill={secondary}>
                {(state.policy_progress ?? 0) > 0.5
                  ? "政策探索 · 非投产证明"
                  : overlay.identity}
              </Text>
              {overlay.kind === "cavern-flex-v3" ? (
                <FlexMechanism overlay={overlay} state={state} />
              ) : (
                <IdcStatus overlay={overlay} state={state} />
              )}
            </g>
          </g>
        );
      })}
    </svg>
  );
};
