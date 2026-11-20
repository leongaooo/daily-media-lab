/** Real loaded-font bounds and DOM consumer regression, without video/GPU rendering. */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const values = process.argv.slice(2);
const option = (name) => {
  const index = values.indexOf(name);
  if (index < 0 || !values[index + 1]) {
    throw new Error(`Required option: ${name}`);
  }
  return path.resolve(values[index + 1]);
};
const install = option("--remotion-install");
const browserExecutable = option("--browser");
const font = option("--font");
const requireRuntime = createRequire(path.join(install, "package.json"));
const { openBrowser } = requireRuntime("@remotion/renderer");
const { buildSync } = requireRuntime("esbuild");
const helper = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../assets/remotion-editorial/JointOverlay.tsx",
);
const source = `
import React from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {JointOverlay, verifyJointLayout} from ${JSON.stringify(helper)};
export {verifyJointLayout};
export const markup=(directing,frame)=>renderToStaticMarkup(React.createElement(JointOverlay,{directing,frame}));
`;
const code = buildSync({
  stdin: { contents: source, resolveDir: install, loader: "tsx" },
  bundle: true,
  nodePaths: [path.join(install, "node_modules")],
  format: "iife",
  globalName: "JointLayout",
  target: "es2022",
  write: false,
}).outputFiles[0].text;
const fontUrl = `data:font/ttf;base64,${readFileSync(font).toString("base64")}`;
console.log(
  JSON.stringify({
    owner: "joint_consumer",
    resource: "joint-layout-test",
    pid: process.pid,
    cleanup: "isolated browser closed in finally",
  }),
);
const browser = await openBrowser("chrome", {
  browserExecutable,
  logLevel: "error",
});
try {
  const page = await browser.newPage({
    context: () => null,
    logLevel: "error",
    indent: false,
    pageIndex: 0,
    onBrowserLog: null,
    onLog: () => {},
  });
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
  const result = await page.evaluate(
    async ({ code, fontUrl }) => {
      const face = await new FontFace(
        "EditorialProjectFont",
        `url(${fontUrl})`,
      ).load();
      document.fonts.add(face);
      (0, eval)(code);
      const directing = {
        overlays: [
          {
            overlay_id: "flex",
            kind: "cavern-flex-v3",
            panel: [900, 180, 910, 640],
            title: "柔性算力",
            identity: "机制示意 · 非实测",
            task: {
              id: "task-A",
              label: "可延后任务 A",
              from: 0.1,
              to: 0.6,
              width: 0.22,
            },
            caveats: [
              { text: "不证明项目已通电", event: "project" },
              { text: "不承诺全天候100%绿电", event: "green" },
            ],
          },
        ],
        frames: [0.1, 0.35, 0.6].map((position, index) => ({
          anchor: { x: 730 + index * 4, y: 450, visible: true },
          overlays: [
            {
              overlay_id: "flex",
              panel_progress: 1,
              prediction_progress: 1,
              task_id: "task-A",
              task_x: position,
              task_progress: index / 2,
              result_visible: index === 2,
              policy_progress: 0,
              caveat_progress: [0, 0],
            },
          ],
        })),
      };
      globalThis.JointLayout.verifyJointLayout(directing);
      const container = document.createElement("div");
      Object.assign(container.style, {
        position: "absolute",
        top: "0",
        left: "0",
        width: "1920px",
        height: "1080px",
        fontFamily: '"EditorialProjectFont"',
      });
      document.body.appendChild(container);
      const samples = directing.frames.map((_, frame) => {
        container.innerHTML = globalThis.JointLayout.markup(directing, frame);
        const task = container.querySelector('[data-task-id="task-A"]');
        const rect = task.querySelector("rect").getBoundingClientRect();
        const texts = [...container.querySelectorAll("text")].map((element) => {
          const bounds = element.getBoundingClientRect();
          if (
            bounds.left < 900 ||
            bounds.right > 1810 ||
            bounds.top < 180 ||
            bounds.bottom >= 904
          ) {
            throw new Error(
              `Board glyph bounds invalid: ${element.textContent}`,
            );
          }
          return element.textContent;
        });
        return { x: rect.x, width: rect.width, id: task.dataset.taskId, texts };
      });
      let rejected = false;
      directing.overlays[0].title = "过长的标题不可任意缩小字号".repeat(8);
      try {
        globalThis.JointLayout.verifyJointLayout(directing);
      } catch (error) {
        rejected = error.message.includes("text exceeds its panel");
      }
      const idc = structuredClone(directing);
      idc.overlays = [
        {
          overlay_id: "idc",
          kind: "idc-status-v3",
          panel: [900, 180, 910, 640],
          title: "供应与核验",
          identity: "来源披露 · 非项目实拍",
          cards: [
            {
              title: "未来安排",
              detail: "2027年下半年以后",
              status: "future",
              event: "future",
            },
          ],
        },
      ];
      globalThis.JointLayout.verifyJointLayout(idc);
      idc.overlays[0].cards[0].detail = "第一行\n第二行\n第三行";
      let multilineRejected = false;
      try {
        globalThis.JointLayout.verifyJointLayout(idc);
      } catch (error) {
        multilineRejected = error.message.includes("text exceeds its panel");
      }
      const leaked = [...document.querySelectorAll("span")].filter(
        (element) => element.style.left === "-10000px",
      ).length;
      container.remove();
      return { samples, rejected, multilineRejected, leaked };
    },
    { code, fontUrl },
  );
  assert.ok(
    result.samples[0].x < result.samples[1].x &&
      result.samples[1].x < result.samples[2].x,
  );
  assert.ok(
    result.samples.every(
      (sample) =>
        sample.id === "task-A" && sample.width === result.samples[0].width,
    ),
  );
  assert.ok(result.samples[2].texts.includes("调整后"));
  assert.equal(result.rejected, true);
  assert.equal(result.multilineRejected, true);
  assert.equal(result.leaked, 0);
  console.log(JSON.stringify({ passed: true, ...result }, null, 2));
} finally {
  await browser.close({ silent: true });
}
