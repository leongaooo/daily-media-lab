/** Real browser regression for the same DOM guard used before video capture.
 * Explicit paths keep this test independent of private voices and browser downloads.
 */
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
const { transformSync } = requireRuntime("esbuild");
const helper = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../assets/remotion-editorial/caption-layout.ts",
);
const bundle = transformSync(readFileSync(helper, "utf8"), {
  loader: "ts",
  format: "iife",
  globalName: "CaptionLayout",
  target: "es2022",
}).code;
const fontUrl = `data:font/ttf;base64,${readFileSync(font).toString("base64")}`;
console.log(
  JSON.stringify({
    owner: "media_pipeline",
    resource: "caption-boundary-test",
    pid: process.pid,
    browser_executable: browserExecutable,
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
    async ({ code, url }) => {
      const face = await new FontFace(
        "EditorialProjectFont",
        `url(${url})`,
      ).load();
      document.fonts.add(face);
      (0, eval)(code);
      const normal = globalThis.CaptionLayout.verifyCaptionLayout([
        { text: "载板供应是未来安排，需要把计划与当期交付分开理解。" },
        { text: "第一行保留完整语义\n第二行保留真实读法与数字。" },
      ]);
      const rejected = [];
      for (const text of [
        Array(5).fill("这是显式换行的字幕边界样本。").join("\n"),
        "这是不能任意截断或缩小字号的长字幕".repeat(14),
      ]) {
        try {
          globalThis.CaptionLayout.verifyCaptionLayout([{ text }]);
          throw new Error("Overflow was accepted");
        } catch (error) {
          if (!error.message.includes("exceeds the fixed y904-1080 rail")) {
            throw error;
          }
          rejected.push(error.message);
        }
      }
      const leaked = [...document.querySelectorAll("div")].filter(
        (element) => element.style.left === "-10000px",
      ).length;
      return { normal, rejected, leaked, browser: navigator.userAgent };
    },
    { code: bundle, url: fontUrl },
  );
  assert.equal(result.normal.length, 2);
  assert.equal(result.rejected.length, 2);
  assert.equal(result.leaked, 0);
  assert.ok(
    result.normal.every((item) => item.content_height <= item.available_height),
  );
  console.log(JSON.stringify({ passed: true, ...result }, null, 2));
} finally {
  await browser.close({ silent: true });
}
