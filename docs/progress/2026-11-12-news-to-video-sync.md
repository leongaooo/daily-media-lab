# REP-05 · 同步正式 news-to-video 技能副本

日期：2026-11-12（Asia/Shanghai）。负责人：当前 Codex agent。任务状态维护在 [ROADMAP](../../ROADMAP.md)。

## 目标与范围

将 `C:\Users\xc_sc\.agents\skills\news-to-video` 的正式更新同步到仓库 `skills/news-to-video`，覆盖统一横屏 Editorial、固定底部字幕与 B 版男声、故事世界、连续 `story` 镜头、动效计划、视觉选择和每期最多 10 次新的付费生图尝试。合并保留仓库已有公开声音实现、显式声音选择和 runtime 匹配校验，以及 REP-01 证据、测试和示例；本轮不删除历史证据，不复制本机凭据、私人参考或本地生成素材。

## 实施文件

- 更新 `skills/news-to-video/SKILL.md`、`CHANGELOG.md`、`evals/evals.json` 和 Editorial 参考文档。
- 同步 `scripts/director_contract.py`、`scripts/remotion_visual.py`、`scripts/render.py`、`scripts/generate_images.py` 及对应验证脚本。
- 同步 `assets/example-project.json`、Remotion `story` 组件和新增 `references/visual-director.md`、`evals/general-director-validation.md`。
- 更新中英文 README、`docs/WORKFLOW.md`、`ROADMAP.md` 与 `docs/HANDOFF.md`；未复制 `config/image-generation/api-key.local.json`、`connection.json` 或其他本机敏感/未跟踪素材。

## 验证证据

- `git diff --check`：通过格式检查；首次发现 `CHANGELOG.md` 末尾多余空行，已清理后复核。
- `python -m compileall -q scripts`（工作区 Python 运行时）：通过。
- 全量测试中的导演契约测试：6 项通过，覆盖通用题材、旧项目未评估、世界缺失/冲突、口播身份冻结、语速/模式边界和字幕索引绑定。
- 完整回归：在技能已配置的 `C:/Users/xc_sc/.cache/news-to-video/env/Scripts/python.exe` 环境运行 `-m unittest discover -s scripts -p 'test_*.py'`，56 项通过（正式技能 51 项，加仓库公开声音扩展 5 项）。此前默认 Python/工作区 Python 缺依赖，切换既有环境后解决；未安装或下载新依赖。图片和模型下载测试均使用 mock，未调用真实生图接口、未读取私人凭据或下载模型。
- 格式与注释：对修改的 Python 文件执行 Black 25.1.0；手工整理新增 TSX，并复核缓存、预算串行写入、规划报告与真实视觉验收的注释边界。使用既有 esbuild 对 `Composition.tsx` 完成 TSX 语法转译；不冒称类型检查或真实渲染。
- 提交范围检查：JSON 可解析、本地 Markdown 链接有效；禁止路径与常见凭据签名扫描通过。默认示例通过渲染前置校验和导演规划检查，与旧示例口播身份一致。
- 未启动 TTS、Remotion 渲染、真实成片或试听；本轮目标是技能副本同步。

## 限制与下一步

本轮证明了同步文件可编译、56 项回归通过，未证明完整音视频解码、视觉连续性、人耳听感、图片授权或新机器安装。下一步继续按 ROADMAP 推进 REP-02、REP-03 或 REP-04，新契约实际画面表现仍留待下一次成片验收。

合并差异：仓库继续支持显式公开音色，正式技能默认 B 声不变；不得静默替换。未引入本机独有的主持人图片或未在仓库音乐清单启用的曲目。
