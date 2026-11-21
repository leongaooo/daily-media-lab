/** 纯展示面板：节点与标签来自已校验载荷；不推断前后关系或项目完成态。 */
import React from "react";

type Node = { title: string; detail?: string };
type Palette = {
  primary: string;
  accent: string;
  muted: string;
  warning: string;
};

export function ComparisonPanel({
  nodes,
  labels,
  palette,
}: {
  nodes: Node[];
  labels: string[];
  palette: Palette;
}) {
  if (nodes.length !== 2 || labels.length !== 2) {
    throw new Error("ComparisonPanel requires two authored nodes and labels");
  }
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 50,
        height: "100%",
        alignItems: "center",
      }}
    >
      {nodes.map((node, index) => (
        <div
          key={index}
          data-editorial-node={index}
          style={{
            borderTop: `4px solid ${index ? palette.primary : palette.accent}`,
            padding: 28,
          }}
        >
          <div style={{ fontSize: 24, color: palette.muted }}>
            {labels[index]}
          </div>
          <div style={{ fontSize: 44, marginTop: 30, lineHeight: 1.3 }}>
            {node.title}
          </div>
          <div
            style={{
              fontSize: 29,
              marginTop: 25,
              lineHeight: 1.5,
              color: palette.muted,
            }}
          >
            {node.detail}
          </div>
        </div>
      ))}
    </div>
  );
}

/** 始终展示全部核对项，focus只强调相应项，不再把其余内容丢弃。 */
export function EvidenceBoard({
  nodes,
  focus,
  detail,
  palette,
}: {
  nodes: Node[];
  focus?: number;
  detail?: string;
  palette: Palette;
}) {
  if (nodes.length < 1 || nodes.length > 4) {
    throw new Error("EvidenceBoard requires one to four authored nodes");
  }
  return (
    <div
      style={{
        padding: "20px 38px",
        height: "100%",
        boxSizing: "border-box",
        borderLeft: `6px solid ${palette.accent}`,
        display: "flex",
        flexDirection: "column",
        gap: 22,
      }}
    >
      <div style={{ fontSize: 24, color: palette.muted, letterSpacing: 3 }}>
        证据与核对项
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: nodes.length > 1 ? "1fr 1fr" : "1fr",
          gap: 22,
          flex: 1,
          minHeight: 0,
        }}
      >
        {nodes.map((node, index) => (
          <div
            key={index}
            data-editorial-node={index}
            style={{
              padding: 20,
              border: `2px solid ${focus === index ? palette.accent : palette.primary}`,
              borderRadius: 10,
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                fontSize: nodes.length > 2 ? 30 : 37,
                lineHeight: 1.25,
                fontWeight: 700,
                color: palette.primary,
              }}
            >
              {node.title}
            </div>
            <div
              style={{
                fontSize: nodes.length > 2 ? 25 : 29,
                marginTop: 15,
                lineHeight: 1.5,
                color: "#F7F9FC",
              }}
            >
              {node.detail}
            </div>
          </div>
        ))}
      </div>
      {detail ? (
        <div style={{ fontSize: 25, color: palette.accent, lineHeight: 1.4 }}>
          {detail}
        </div>
      ) : null}
    </div>
  );
}
