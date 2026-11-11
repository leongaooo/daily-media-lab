import React from 'react';
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
} from 'remotion';

type Bar = {label: string; value: number};
type FlowNode = {title: string; detail?: string};
type SceneData = {
  kind: string;
  duration: number;
  headline: string;
  center_text: string;
  chapter: string;
  segments: string[];
  captions: CaptionData[];
  image: string | null;
  data: Bar[];
  unit: string;
  source: string;
  nodes: FlowNode[];
  image_fit: string;
  summary: string;
};
type CaptionData = {text: string; start: number; end: number};
type Props = {
  scenes: SceneData[];
  width: number;
  height: number;
  fps: number;
};

const colors = {
  ink: '#e9f1f0',
  paper: '#f4efe6',
  teal: '#73e0c2',
  gold: '#ffd58d',
  navy: '#0c1725',
  plum: '#3f355d',
};

const CaptionRail: React.FC<{scene: SceneData}> = ({scene}) => {
  const frame = useCurrentFrame();
  const caption = scene.captions.find(
    (item) => frame >= item.start && frame < item.end,
  );
  const opacity = caption ? 1 : 0;
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 0,
        height: 176,
        padding: '28px 86px',
        display: 'flex',
        alignItems: 'center',
        background: 'rgba(5, 12, 20, 0.94)',
        borderTop: '1px solid rgba(255,255,255,0.16)',
        color: '#f8fbfa',
        fontSize: 40,
        lineHeight: 1.25,
        opacity,
      }}
    >
      <div style={{maxWidth: 1748, whiteSpace: 'pre-line'}}>
        {caption?.text || ''}
      </div>
    </div>
  );
};

const Shell: React.FC<{
  children: React.ReactNode;
  scene: SceneData;
  dark?: boolean;
}> = ({children, scene, dark = true}) => {
  const frame = useCurrentFrame();
  const entrance = spring({frame, fps: 24, config: {damping: 180}});
  return (
    <AbsoluteFill style={{fontFamily: '"Microsoft YaHei", sans-serif'}}>
      <AbsoluteFill
        style={{
          padding: 86,
          color: dark ? colors.ink : '#26323b',
          background: dark
            ? 'radial-gradient(circle at 85% 10%, #204b60 0, transparent 38%), ' +
              colors.navy
            : 'radial-gradient(circle at 90% 8%, #ffd9ad 0, transparent 32%), ' +
              colors.paper,
          opacity: interpolate(entrance, [0, 1], [0, 1]),
        }}
      >
        <div
          style={{
            fontSize: 23,
            letterSpacing: 5,
            color: dark ? colors.teal : '#ad5f32',
          }}
        >
          {scene.chapter || 'EDITORIAL VIDEO'}
        </div>
        {children}
      </AbsoluteFill>
      <CaptionRail scene={scene} />
    </AbsoluteFill>
  );
};

const Hero: React.FC<{scene: SceneData}> = ({scene}) => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 220], [1.13, 1], {
    extrapolateRight: 'clamp',
  });
  return (
    <Shell scene={scene}>
      <div
        style={{display: 'flex', alignItems: 'center', gap: 64, marginTop: 70}}
      >
        <div style={{width: 660, flexShrink: 0}}>
          <div
            style={{
              fontSize: 96,
              fontWeight: 800,
              lineHeight: 1.15,
              letterSpacing: -3,
              whiteSpace: 'pre-line',
            }}
          >
            {scene.headline || scene.center_text}
          </div>
          <div
            style={{
              fontSize: 29,
              lineHeight: 1.45,
              color: '#adbfca',
              marginTop: 40,
            }}
          >
            {scene.summary || scene.segments[0]}
          </div>
        </div>
        {scene.image ? (
          <div
            style={{
              width: 1024,
              height: 650,
              flexShrink: 0,
              overflow: 'hidden',
              borderRadius: 28,
            }}
          >
            <Img
              src={staticFile(scene.image)}
              style={{
                width: '100%',
                height: '100%',
                objectFit: scene.image_fit === 'cover' ? 'cover' : 'contain',
                transform:
                  scene.image_fit === 'cover'
                    ? 'scale(' + zoom + ')'
                    : undefined,
              }}
            />
          </div>
        ) : (
          <div
            style={{
              width: 850,
              height: 580,
              border: '2px solid ' + colors.teal,
              borderRadius: 40,
              display: 'grid',
              placeItems: 'center',
            }}
          >
            <div style={{fontSize: 120, fontWeight: 800, color: colors.teal}}>
              {scene.center_text}
            </div>
          </div>
        )}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 86,
          bottom: 195,
          fontSize: 23,
          color: '#adbfca',
        }}
      >
        {scene.source}
      </div>
    </Shell>
  );
};

const Flow: React.FC<{scene: SceneData}> = ({scene}) => {
  const frame = useCurrentFrame();
  const pulse = interpolate(frame, [0, 90, 190], [0, 1, 2], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  // Scene-owned nodes prevent sample-topic content leaking into other programs.
  const nodes = scene.nodes;
  return (
    <Shell scene={scene}>
      <div
        style={{
          fontSize: 94,
          fontWeight: 800,
          marginTop: 90,
          letterSpacing: -5,
        }}
      >
        {scene.headline || scene.center_text}
      </div>
      <div
        style={{display: 'flex', alignItems: 'center', gap: 28, marginTop: 80}}
      >
        {nodes.map(({title, detail}, index) => (
          <React.Fragment key={title}>
            <div
              style={{
                width: 400,
                height: 260,
                padding: 32,
                borderRadius: 28,
                background: ['#25465a', '#20645e', colors.plum][index],
                transform:
                  'translateY(' +
                  (index === Math.floor(pulse) ? -18 : 0) +
                  'px)',
              }}
            >
              <div style={{fontSize: 48, fontWeight: 750}}>{title}</div>
              <div style={{fontSize: 28, color: '#d7ebe7', marginTop: 35}}>
                {detail}
              </div>
            </div>
            {index < nodes.length - 1 ? (
              <div style={{fontSize: 68, color: colors.gold}}>→</div>
            ) : null}
          </React.Fragment>
        ))}
      </div>
      <div style={{fontSize: 31, marginTop: 70, color: '#b7c9d8'}}>
        {scene.center_text || scene.segments[0]}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 86,
          bottom: 195,
          fontSize: 23,
          color: '#adbfca',
        }}
      >
        {scene.source}
      </div>
    </Shell>
  );
};

const Chart: React.FC<{scene: SceneData}> = ({scene}) => {
  const frame = useCurrentFrame();
  const entry = spring({frame, fps: 24, config: {damping: 180}, delay: 10});
  const max = Math.max(...scene.data.map((row) => row.value), 1);
  return (
    <Shell scene={scene} dark={false}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'end',
          marginTop: 70,
        }}
      >
        <div style={{fontSize: 98, fontWeight: 850, lineHeight: 0.95}}>
          {scene.headline || scene.center_text}
        </div>
        <div style={{fontSize: 29, width: 700, lineHeight: 1.45}}>
          {scene.segments[0]}
        </div>
      </div>
      <div style={{marginTop: 72, width: 1440}}>
        {scene.data.map((row, index) => (
          <div key={row.label} style={{marginBottom: 42}}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 31,
              }}
            >
              <span>{row.label}</span>
              <b>
                {row.value}
                {scene.unit}
              </b>
            </div>
            <div
              style={{
                height: 42,
                marginTop: 12,
                borderRadius: 30,
                background: '#ddd5c7',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: (row.value / max) * 100 + '%',
                  height: '100%',
                  background: index ? '#216c65' : '#b07240',
                  transformOrigin: 'left',
                  transform: 'scaleX(' + entry + ')',
                }}
              />
            </div>
          </div>
        ))}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 86,
          bottom: 205,
          fontSize: 23,
          color: '#6d746e',
        }}
      >
        {scene.source}
      </div>
    </Shell>
  );
};

const Scene: React.FC<{scene: SceneData}> = ({scene}) => {
  if (scene.kind === 'chart') return <Chart scene={scene} />;
  if (scene.kind === 'flow') return <Flow scene={scene} />;
  return <Hero scene={scene} />;
};

export const EditorialVideo: React.FC<Props> = ({scenes}) => {
  let from = 0;
  return (
    <AbsoluteFill>
      {scenes.map((scene) => {
        const start = from;
        from += scene.duration;
        return (
          <Sequence
            key={scene.kind + '-' + start}
            from={start}
            durationInFrames={scene.duration}
          >
            <Scene scene={scene} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
