# PUB-07 · 开源发布收尾

日期：2026-11-20（Asia/Shanghai）。状态以[ROADMAP](../../ROADMAP.md)为准。

用户已在源会话01a1f856-969d-79d3-8638-92232151a27d明确要求新开会话，先记录roadmap，再主动完成第一部分。上一轮三部分中第一部分已明确为发布前复核、Git提交、推送及GitHub远程验证；当前授权覆盖该闭环，无需再次询问是否提交／推送。

本轮发布基于main工作区、HEAD f71edbf49008baa6089fe9e8a9c0c36f7864194f及origin https://github.com/leongaooo/daily-media-lab.git。现有dirty含已验收的三媒体入口／Blender／联合导演、公开适配及必要文档；接手者按实际diff审核，不整目录覆盖、不机械全部暂存或回退他人差异。

REP-09本阶段已获用户验收通过，canonical118／public123回归及两片媒体结果见[阶段记录](2026-11-20-joint-directing-v3.md)。实际媒体／冻结私声／本地大资产在E:/CodexMedia/jobs/2026-11-20/joint-directing-v3，不纳入公开仓。公共声音policy／setup／身份校验／专有测试、许可和使用者台账保留。

接手后在此文件追加实际审阅范围、必要检查、提交SHA、推送结果及远程页面／ref验证。新题材生产和独立新机仍属后两部分，仅登记，不在本轮启动。

## 接手复核（2026-11-20，当前会话 `01a1f8af-4350-76e3-9784-ba4b6839de72`）

- 已重新 `git fetch origin --prune`；工作区为 `main`，接手时 `HEAD` 与 `origin/main` 均为 `f71edbf49008baa6089fe9e8a9c0c36f7864194f`，远端没有新增分叉。
- 按当前完整 dirty diff 逐项复核并显式暂存 84 个公开文件：技能、脚本、测试、来源／台账、README／贡献说明、三媒体／Blender 最小示例及本批 progress。未暂存或纳入本批的本地文件包括 `local-review/`、输出媒体、私有声音、E 盘作业、runtime、权重、Key、客户资料及其他被 `.gitignore` 排除项；没有使用 `git add -A`。
- 保护边界核对：`public_voice.py`、`setup_public_voice.py`、`test_public_voice.py`、公开声音参考、`runtime-lock.json`、第三方许可和使用者历史均保持既有状态；兼容导出没有用canonical覆盖公开声音适配。敏感模式扫描未发现私钥或真实凭据，测试中的占位密钥仅用于离线拒绝／脱敏回归。
- 必要检查通过：`git diff --check`；修改／新增 Markdown 相对链接 194 项全部可达；JSON 解析与 Python 编译通过；`skills/news-to-video` 全量回归 123 项通过；`episode.py validate-package assets/editorial-package-example.json` 通过；显式 Remotion 安装、Headless Chrome 与 `C:/Windows/Fonts/msyh.ttc` 运行 `test_caption_layout.mjs`、`test_joint_layout.mjs` 均通过（含超长字幕拒绝、联合图板状态变化、无DOM泄漏）。复用E盘 `implementation/status.md`、`final-validation.json`、`public-runtime-sync.json`、canonical/public 日志中的同版证据；本轮不重新生成TTS、渲染或私有媒体。
- 接手复核阶段的待办已在本记录末尾完成：提交、正常推送 `origin/main` 与远端 SHA／GitHub 页面核验均有证据。PROD-01、OPS-01 仍只登记，不因本次发布提前完成。

## 提交、推送与远程核验

- 发布提交：`dc412bf087e1f67a5da32addb553a09495f4b5d2`（短SHA `dc412bf`），提交页为 <https://github.com/leongaooo/daily-media-lab/commit/dc412bf087e1f67a5da32addb553a09495f4b5d2>；提交包含 84 个已审阅公开文件。
- `git push origin main` 正常完成；随后 `git fetch origin --prune` 与 `git ls-remote origin refs/heads/main` 均返回同一完整 SHA。工作树最终为 `main...origin/main` 且无未提交差异。
- GitHub REST 仓库／提交接口确认默认分支为 `main`、提交消息和完整 SHA；GitHub 页面与 raw 端点实际 HTTP 200：README、ROADMAP、HANDOFF、此发布记录、`skills/news-to-video/SKILL.md`、`skills/idc-compute-news-digest/SKILL.md`。六个关键文件的 `origin/main` Git blob 与本地 HEAD 一致。
- 远端树的本次新增／修改路径未包含 `local-review/`、Key、私声、客户资料、权重、`.blend` 或 MP4；远端原有 `previews/editorial-silent.mp4` 与 `skills/news-to-video/assets/runtime-lock.json` 未被本次提交新增或改动。
- PUB-07验收闭环完成。没有创建 GitHub Release、发布有声媒体、发送外部消息或启动自动化；PROD-01新题材成片、OPS-01工程化／公开复现、独立新机、跨设备声音与跨题材长期稳定性仍未完成，不能由本次提交外推。
