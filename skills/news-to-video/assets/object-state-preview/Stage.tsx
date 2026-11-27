import React from "react";
import type { StageProps } from "../ObjectStage";

/** Render a fictional installation, route and release from the staged cue frames. */
export default function Stage({ stage, frame }: StageProps) {
  const progress = (target: string) => {
    const event = stage.actions.find((item) => item.target === target);
    if (!event) {
      throw new Error("Missing stage event: " + target);
    }
    const fraction = (frame - event.start_frame) / (event.end_frame - event.start_frame);
    return Math.max(0, Math.min(1, fraction));
  };
  const installed = progress("module");
  const connected = progress("route");
  const reviewed = progress("release");
  const moduleX = 360 + 254 * installed;
  const markerX = 1200 - 320 * reviewed;

  return (
    <svg width="100%" height="100%" viewBox="0 0 1600 560" aria-label="合成概念示意">
      <rect width="1600" height="560" rx="16" fill="#142634" />
      <g fontSize="32" fontWeight="650" fill="#edf9ff">
        <text x="96" y="85">合成概念示意 · 模块、链路和交付节点</text>
        <text x="95" y="386">模块入位</text>
        <text x="788" y="386">链路连通</text>
        <text x="95" y="506">预计交付节点</text>
        <text x="1257" y="506">原预计</text>
      </g>
      <rect x="480" y="155" width="300" height="180" rx="10" fill="#36566a" />
      <rect x="606" y="206" width="120" height="72" rx="4" fill="#091d2d" />
      <rect x={moduleX} y="212" width="116" height="60" rx="6" fill="#f2c885" />
      <path d="M720 243C853 148 1047 148 1180 243" fill="none" stroke="#527986" strokeWidth="7" />
      <path
        d="M720 243C853 148 1047 148 1180 243"
        fill="none"
        pathLength="100"
        stroke="#72ead1"
        strokeWidth="9"
        strokeDasharray={100 * connected + " 100"}
      />
      <rect x="1180" y="185" width="195" height="115" rx="10" fill="#36566a" />
      <path d="M510 492H1220" stroke="#8aafc5" strokeWidth="4" />
      <circle cx="1200" cy="492" r="12" fill="#142634" stroke="#8aafc5" strokeWidth="3" />
      <circle cx={markerX} cy="492" r="14" fill="#f2c885" />
    </svg>
  );
}
