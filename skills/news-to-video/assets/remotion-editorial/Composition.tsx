/** Editorial stage: fixed rails, authored visual grammar, caption-bound shot state.
 * Asset pixels establish atmosphere; native geometry owns exact labels and relations.
 */
import React from "react";
import ProjectStage from "./ProjectStage";
import { ComparisonPanel, EvidenceBoard } from "./EditorialPanels";
import { JointOverlay, verifyJointLayout } from "./JointOverlay";
import type { JointDirecting } from "./JointOverlay";
import {
  captionRailStyle,
  captionTextStyle,
  verifyCaptionLayout,
} from "./caption-layout";
import type { StageProps } from "./ObjectStage";
import {
  AbsoluteFill,
  Img,
  Sequence,
  staticFile,
  useCurrentFrame,
  delayRender,
  continueRender,
  cancelRender,
} from "remotion";

type Palette = {
  background: string;
  primary: string;
  accent: string;
  warning: string;
  muted: string;
};
type Node = { title: string; detail?: string };
type Shot = {
  stage_view?: number[];
  nodes?: Node[];
  image?: string | null;
  title: string;
  detail?: string;
  start: number;
  end: number;
  composition?: string;
  focus?: number;
  background_asset?: string | null;
  subject_asset?: string | null;
  supporting_asset?: string | null;
  camera_language?: string;
};
type Scene = {
  object_stage?: StageProps["stage"];
  motion_plan?: { entrance?: string; emphasis?: string; camera?: string };
  kind: string;
  composition?: string;
  duration: number;
  headline: string;
  chapter: string;
  center_text: string;
  summary: string;
  source: string;
  image: string | null;
  image_fit: string;
  nodes: Node[];
  comparison_labels?: string[];
  segments: string[];
  captions: { text: string; start: number; end: number }[];
  shots: Shot[];
  palette?: Palette;
  background_asset?: string | null;
  subject_asset?: string | null;
  supporting_asset?: string | null;
  camera_language?: string;
  background_style?: string;
  story_world?: { id: string };
  data: { label: string; value: number }[];
  unit: string;
};
type NarrativeShot = {
  shot_id: string;
  start_frame: number;
  end_frame: number;
  frames: string[];
  label: string;
};
type Props = {
  scenes: Scene[];
  width: number;
  height: number;
  fps: number;
  font_asset?: string;
  narrative_version?: number;
  narrative_shots?: NarrativeShot[];
  narrative_cues?: { text: string; start_frame: number; end_frame: number }[];
  narrative_directing?: JointDirecting;
};
const fallback: Palette = {
  background: "#161A22",
  primary: "#64D8CB",
  accent: "#F4B860",
  warning: "#EE8067",
  muted: "#AAB6C4",
};
const bounded = (value: number) => Math.max(0, Math.min(1, value));

/** Pure SVG geometry retains node identity and position while caption focus changes. */
const Relationship: React.FC<{
  scene: Scene;
  shot: Shot;
  palette: Palette;
  progress: number;
  grammar: string;
}> = ({ scene, shot, palette, progress, grammar }) => {
  const nodes = shot.nodes ?? scene.nodes;
  const focus = shot.focus ?? 0;
  if (grammar === "timeline" || grammar === "flow") {
    return (
      <svg width="100%" height="100%" viewBox="0 0 1120 480">
        <path d="M100 240 H1020" stroke={palette.muted} strokeWidth="3" />
        <path
          d="M100 240 H1020"
          stroke={palette.primary}
          strokeWidth="6"
          pathLength="1"
          strokeDasharray="1"
          strokeDashoffset={1 - progress}
        />
        {nodes.map((node, index) => {
          const x = 180 + (index * 760) / Math.max(1, nodes.length - 1);
          const active = focus === index;
          return (
            <g key={node.title} opacity={1}>
              <circle
                cx={x}
                cy="240"
                r={active ? 20 : 10}
                fill={active ? palette.accent : palette.primary}
              />
              <text
                x={x}
                y={index % 2 ? 310 : 160}
                textAnchor="middle"
                fill="#F7F9FC"
                fontSize="34"
                fontWeight="700"
              >
                {node.title}
              </text>
              <text
                x={x}
                y={index % 2 ? 355 : 202}
                textAnchor="middle"
                fill={palette.muted}
                fontSize="23"
              >
                {node.detail}
              </text>
            </g>
          );
        })}
      </svg>
    );
  }
  // Topology is explicitly an abstract editorial relationship, never real node counts.
  return (
    <svg width="100%" height="100%" viewBox="0 0 1120 480">
      <ellipse
        cx="550"
        cy="245"
        rx="400"
        ry="175"
        stroke={palette.primary}
        strokeWidth="2"
        strokeDasharray="8 12"
        fill="none"
        opacity="0.5"
      />
      {nodes.map((node, index) => {
        const angle =
          -Math.PI / 2 + (index * 2 * Math.PI) / Math.max(1, nodes.length);
        const x = 550 + Math.cos(angle) * 340;
        const y = 245 + Math.sin(angle) * 155;
        return (
          <g key={node.title}>
            <path
              d={`M550 245 L${x} ${y}`}
              stroke={index === focus ? palette.accent : palette.primary}
              strokeWidth={index === focus ? 5 : 2}
              pathLength="1"
              strokeDasharray="1"
              strokeDashoffset={1 - progress}
            />
            <circle
              cx={x}
              cy={y}
              r="38"
              fill={palette.background}
              stroke={index === focus ? palette.accent : palette.primary}
              strokeWidth="4"
            />
            <text
              x={x}
              y={y + 7}
              textAnchor="middle"
              fill="#F7F9FC"
              fontSize="25"
            >
              {index + 1}
            </text>
            <text
              x={x}
              y={y + 80}
              textAnchor="middle"
              fill="#F7F9FC"
              fontSize="29"
            >
              {node.title}
            </text>
          </g>
        );
      })}
      <circle
        cx="550"
        cy="245"
        r="62"
        fill={palette.background}
        stroke={palette.primary}
        strokeWidth="4"
      />
      <text
        x="550"
        y="252"
        textAnchor="middle"
        fill={palette.primary}
        fontSize="24"
      >
        关系示意
      </text>
    </svg>
  );
};

const VisualStage: React.FC<{
  scene: Scene;
  shot: Shot;
  palette: Palette;
  progress: number;
  grammar: string;
}> = ({ scene, shot, palette, progress, grammar }) => {
  const focus = shot.focus ?? 0;
  const subject =
    shot.subject_asset ?? shot.image ?? scene.subject_asset ?? scene.image;
  if (grammar === "hero_scene" || grammar === "hero" || grammar === "story") {
    return (
      <div
        style={{
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {subject ? (
          <Img
            src={staticFile(subject)}
            style={{
              width: "85%",
              height: "90%",
              objectFit: scene.image_fit === "cover" ? "cover" : "contain",
            }}
          />
        ) : (
          <div
            style={{ fontSize: 90, lineHeight: 1.2, color: palette.primary }}
          >
            {shot.title}
          </div>
        )}
      </div>
    );
  }
  if (grammar === "workbench") {
    return (
      <div
        style={{
          padding: 35,
          height: "100%",
          background: "#10151C",
          border: `1px solid ${palette.muted}`,
          borderRadius: 14,
          boxSizing: "border-box",
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 12,
            borderBottom: `1px solid ${palette.muted}`,
            paddingBottom: 22,
          }}
        >
          <span style={{ color: palette.accent }}>● ● ●</span>
          <span style={{ marginLeft: 30, color: palette.muted, fontSize: 24 }}>
            开发工作台 / 原创示意
          </span>
        </div>
        {(shot.nodes ?? scene.nodes).map((node, index) => (
          <div
            key={node.title}
            style={{
              display: "flex",
              gap: 28,
              marginTop: 26,
              padding: 22,
              borderLeft: `4px solid ${index === focus ? palette.accent : palette.primary}`,
              opacity: 1,
              background: index === focus ? "#243142" : "transparent",
            }}
          >
            <div style={{ color: palette.primary, fontSize: 27, width: 130 }}>
              {node.title}
            </div>
            <div style={{ fontSize: 27, color: "#F7F9FC" }}>{node.detail}</div>
          </div>
        ))}
        <div style={{ fontSize: 23, color: palette.accent, marginTop: 26 }}>
          › {shot.detail}
        </div>
      </div>
    );
  }
  if (grammar === "evidence_board") {
    return (
      <EvidenceBoard
        nodes={shot.nodes ?? scene.nodes}
        focus={shot.focus}
        detail={shot.detail}
        palette={palette}
      />
    );
  }
  if (grammar === "comparison") {
    return (
      <ComparisonPanel
        nodes={shot.nodes ?? scene.nodes}
        labels={scene.comparison_labels ?? ["对照 A", "对照 B"]}
        palette={palette}
      />
    );
  }
  if (grammar === "chart") {
    const maximum = Math.max(1, ...scene.data.map((row) => row.value));
    return (
      <div style={{ padding: 30 }}>
        {scene.data.map((row) => (
          <div key={row.label} style={{ marginBottom: 30 }}>
            <div style={{ fontSize: 30 }}>
              {row.label} · {row.value}
              {scene.unit}
            </div>
            <div
              style={{
                height: 30,
                background: palette.primary,
                marginTop: 16,
                width: `${((100 * row.value) / maximum) * progress}%`,
              }}
            />
          </div>
        ))}
      </div>
    );
  }
  return (
    <Relationship
      scene={scene}
      shot={shot}
      palette={palette}
      progress={scene.motion_plan?.emphasis === "none" ? 1 : progress}
      grammar={grammar}
    />
  );
};

const SceneView: React.FC<{ scene: Scene; fps: number }> = ({ scene, fps }) => {
  const frame = useCurrentFrame();
  const palette = scene.palette ?? fallback;
  const seconds = frame / fps;
  const shots = scene.shots?.length
    ? scene.shots
    : [
        {
          title: scene.headline,
          detail: scene.summary,
          start: 0,
          end: scene.duration / fps,
        },
      ];
  const active = Math.max(
    0,
    shots.findIndex((shot) => seconds >= shot.start && seconds < shot.end),
  );
  const shot: Shot = shots[active];
  const grammar = shot.composition ?? scene.composition ?? scene.kind;
  const localFrame = frame - Math.round(shot.start * fps);
  const progress = bounded(
    localFrame / Math.min(24, Math.max(1, ((shot.end - shot.start) * fps) / 3)),
  );
  const cameraProgress = bounded(
    localFrame / Math.max(1, (shot.end - shot.start) * fps),
  );
  const camera =
    shot.camera_language ??
    scene.camera_language ??
    (scene.motion_plan?.camera === "slow_push" ? "slow-push" : "none");
  const cameraTransform =
    camera === "slow-pan-right"
      ? `scale(1.07) translateX(${-20 + cameraProgress * 40}px)`
      : camera === "slow-push"
        ? `scale(${1 + cameraProgress * 0.05})`
        : undefined;
  const background = shot.background_asset ?? scene.background_asset;
  const support = shot.supporting_asset ?? scene.supporting_asset;
  const subject = shot.subject_asset ?? shot.image ?? scene.subject_asset;
  const caption = scene.captions.find(
    (cue) => frame >= cue.start && frame < cue.end,
  );
  if (grammar === "object_stage" && scene.object_stage) {
    const ink = scene.object_stage.ink ?? "#F7F9FC";
    return (
      <AbsoluteFill
        style={{
          fontFamily: '"Microsoft YaHei", sans-serif',
          background: palette.background,
          color: ink,
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: "0 0 176px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 80,
              top: 44,
              fontSize: 24,
              color: palette.muted,
            }}
          >
            {scene.chapter}
          </div>
          <div
            style={{
              position: "absolute",
              left: 80,
              right: 80,
              top: 92,
              fontSize: 50,
              lineHeight: 1.25,
              fontWeight: 800,
            }}
          >
            {scene.headline}
          </div>
          <div
            style={{
              position: "absolute",
              left: 80,
              right: 80,
              top: 178,
              fontSize: 30,
              color: palette.accent,
            }}
          >
            {shot.title}
          </div>
          <div
            style={{
              position: "absolute",
              left: 80,
              right: 80,
              top: 244,
              height: 560,
              overflow: "hidden",
            }}
          >
            <ProjectStage
              stage={scene.object_stage}
              frame={frame}
              palette={palette}
              view={shot.stage_view}
              previousView={shots[Math.max(0, active - 1)].stage_view}
              shotFrame={localFrame}
            />
          </div>
          <div
            style={{
              position: "absolute",
              left: 80,
              right: 80,
              top: 842,
              fontSize: 23,
              color: palette.muted,
            }}
          >
            {scene.source || "原创教学示意"} · 非真实界面、部署或实测结果
          </div>
        </div>
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 904,
            height: 176,
            padding: "22px 80px",
            boxSizing: "border-box",
            display: "flex",
            alignItems: "center",
            background: "#050C14",
            borderTop: "1px solid #46515E",
            color: "#F8FBFA",
            fontSize: 36,
            lineHeight: 1.35,
          }}
        >
          <div style={{ whiteSpace: "pre-line" }}>{caption?.text || ""}</div>
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill
      style={{
        fontFamily: '"Microsoft YaHei", sans-serif',
        background: palette.background,
        color: "#F7F9FC",
      }}
    >
      {/* All scenery and camera movement are clipped before the fixed caption rail. */}
      <div
        style={{ position: "absolute", inset: "0 0 176px", overflow: "hidden" }}
      >
        {background ? (
          <Img
            src={staticFile(background)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              transform: cameraTransform,
              opacity: 0.5,
            }}
          />
        ) : null}
        <AbsoluteFill
          style={{
            background: `linear-gradient(90deg, ${palette.background} 0%, ${palette.background}E8 31%, ${palette.background}66 100%)`,
          }}
        />
        {scene.background_style === "grid" ? (
          <AbsoluteFill
            style={{
              backgroundImage: `linear-gradient(${palette.muted}16 1px, transparent 1px),linear-gradient(90deg, ${palette.muted}16 1px, transparent 1px)`,
              backgroundSize: "64px 64px",
            }}
          />
        ) : null}
        <div
          style={{
            position: "absolute",
            left: 80,
            top: 52,
            right: 80,
            height: 135,
          }}
        >
          <div
            style={{ fontSize: 24, color: palette.primary, letterSpacing: 4 }}
          >
            {scene.chapter}
          </div>
          <div
            style={{
              fontSize: 48,
              fontWeight: 750,
              marginTop: 18,
              lineHeight: 1.3,
            }}
          >
            {scene.headline}
          </div>
        </div>
        <div style={{ position: "absolute", left: 80, top: 245, width: 480 }}>
          <div
            style={{ fontSize: 23, color: palette.accent, letterSpacing: 3 }}
          >
            {String(active + 1).padStart(2, "0")} /{" "}
            {String(shots.length).padStart(2, "0")}
          </div>
          <div
            style={{
              fontSize: 56,
              fontWeight: 800,
              lineHeight: 1.25,
              marginTop: 24,
            }}
          >
            {shot.title}
          </div>
          <div
            style={{
              fontSize: 29,
              lineHeight: 1.6,
              color: palette.muted,
              marginTop: 28,
            }}
          >
            {shot.detail || scene.summary}
          </div>
          {support ? (
            <Img
              src={staticFile(support)}
              style={{
                width: 115,
                height: 100,
                objectFit: "contain",
                marginTop: 28,
              }}
            />
          ) : null}
        </div>
        {subject && !["hero", "hero_scene", "story"].includes(grammar) ? (
          <Img
            src={staticFile(subject)}
            style={{
              position: "absolute",
              right: 90,
              top: 170,
              width: 150,
              height: 100,
              objectFit: "contain",
            }}
          />
        ) : null}
        <div
          style={{
            position: "absolute",
            left: 650,
            top: 260,
            width: 1180,
            height: 480,
            opacity: 1,
          }}
        >
          <VisualStage
            scene={scene}
            shot={shot}
            palette={palette}
            progress={scene.motion_plan?.emphasis === "none" ? 1 : progress}
            grammar={grammar}
          />
        </div>
        <div
          style={{
            position: "absolute",
            left: 80,
            bottom: 32,
            right: 80,
            fontSize: 23,
            color: palette.muted,
            lineHeight: 1.5,
          }}
        >
          {scene.source} · 原创示意，非真实界面或拓扑
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 904,
          height: 176,
          boxSizing: "border-box",
          padding: "22px 80px",
          display: "flex",
          alignItems: "center",
          background: "#050C14",
          borderTop: "1px solid #46515E",
          color: "#F8FBFA",
          fontSize: 36,
          lineHeight: 1.35,
        }}
      >
        <div style={{ whiteSpace: "pre-line" }}>{caption?.text || ""}</div>
      </div>
    </AbsoluteFill>
  );
};

/** Integer global frames arrive from the single audio timeline compiler. */
const NarrativeView: React.FC<Props> = ({
  narrative_shots = [],
  narrative_cues = [],
  narrative_directing,
  font_asset,
}) => {
  const [fontHandle] = React.useState(() =>
    delayRender("Load the declared project font"),
  );
  React.useEffect(() => {
    if (!font_asset) {
      cancelRender(new Error("Narrative project is missing its declared font"));
      return;
    }
    const face = new FontFace(
      "EditorialProjectFont",
      `url(${staticFile(font_asset)})`,
    );
    let active = true;
    face
      .load()
      .then((loaded) => {
        if (active) {
          document.fonts.add(loaded);
          verifyCaptionLayout(narrative_cues);
          if (narrative_directing) {
            verifyJointLayout(narrative_directing);
          }
          continueRender(fontHandle);
        }
      })
      .catch((error) => cancelRender(error));
    return () => {
      active = false;
      document.fonts.delete(face);
    };
  }, [font_asset, fontHandle, narrative_cues, narrative_directing]);
  const frame = useCurrentFrame();
  const shot = narrative_shots.find(
    (item) => frame >= item.start_frame && frame < item.end_frame,
  );
  const cue = narrative_cues.find(
    (item) => frame >= item.start_frame && frame < item.end_frame,
  );
  if (!shot || !shot.frames[frame - shot.start_frame]) {
    throw new Error(`Missing sealed narrative frame ${frame}`);
  }
  return (
    <AbsoluteFill
      style={{
        background: "#050C14",
        fontFamily: '"EditorialProjectFont", sans-serif',
      }}
    >
      {/* Keep the authored 1920x1080 geometry; mask the rail without rescaling the master. */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: 1920,
          height: 904,
          overflow: "hidden",
        }}
      >
        <Img
          src={staticFile(shot.frames[frame - shot.start_frame])}
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
          }}
        />
        {narrative_directing ? (
          <JointOverlay directing={narrative_directing} frame={frame} />
        ) : null}
        <div
          style={{
            position: "absolute",
            left: 64,
            top: 42,
            padding: "10px 18px",
            background: "#050C14E8",
            color: "#F8FBFA",
            fontSize: 25,
          }}
        >
          {shot.label}
        </div>
      </div>
      <div style={captionRailStyle}>
        <div style={captionTextStyle}>{cue?.text || ""}</div>
      </div>
    </AbsoluteFill>
  );
};

export const EditorialVideo: React.FC<Props> = (props) => {
  const { scenes, fps } = props;
  if (props.narrative_version === 1) {
    return <NarrativeView {...props} />;
  }
  let cursor = 0;
  return (
    <AbsoluteFill>
      {scenes.map((scene, index) => {
        const start = cursor;
        cursor += scene.duration;
        return (
          <Sequence
            key={`${scene.story_world?.id ?? index}-${start}`}
            from={start}
            durationInFrames={scene.duration}
          >
            <SceneView scene={scene} fps={fps} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
