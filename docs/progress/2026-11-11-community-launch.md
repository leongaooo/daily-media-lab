# COM-04 · 社区贡献入口启动

日期：2026-11-11（Asia/Shanghai）。负责人：当前Codex agent。任务状态只在ROADMAP维护。

## 授权、目标与范围

维护者试听公开默认短样本后反馈“挺好的”，随后明确要求立即执行公开声音更新、三类Issue模板、三个入门任务及两个协作任务。该反馈仅作为当前默认短样本整体听感认可，不冒称原速对照、逐词或跨设备验收。REP-01已收口；新机器与完整Web3示例保持独立任务。

## 文件与验收计划

- `.github/ISSUE_TEMPLATE/`：复现失败、声音/字幕反馈、改进建议三种Markdown模板，保留空白入口及贡献指引。
- 中英文README、CONTRIBUTING、`docs/community/README.md`：五项任务入口、文件/样本/命令、修改范围和验收证据。
- ROADMAP登记COM-04及五个父任务的子项，避免Issue变成另一份状态表。
- REP-01样本验证JSON、技能说明和交接文件同步试听结果；不改声音及图像素材。
- 发布前检查文档链接、样本哈希、YAML/模板结构、Git格式及全部待推送历史中的禁止文件与疑似凭据；发布后核对远程SHA、Issue正文/标签、模板选择和中英文README。

## 发布执行

准备阶段：GitHub CLI未登录，浏览器有现有维护者会话；Issue将通过该会话发布，不创建新凭据。公开声音实现来自此前本地提交ec73941，尚待随本轮推送。

发布后的实际Issue链接与验证结果在下文补记。

## 真实发布结果

- 公开声音及模板入口已通过 `git push origin main` 发布，首个社区准备提交为6c9ea72（同时带上此前ec73941声音实现）。未创建凭据、未修改安全设置。
- GitHub模板选择页实际显示三类模板、Blank issue及贡献指引。
- 五个Issue已逐项创建并核验标题、编号及标签，列表显示Open(5)、Closed(0)：
  - [#1 中文读法](https://github.com/leongaooo/daily-media-lab/issues/1)：EXP-02-01，good first issue。
  - [#2 无GPU测试CI](https://github.com/leongaooo/daily-media-lab/issues/2)：REP-04-01，help wanted。
  - [#3 手机字幕反馈](https://github.com/leongaooo/daily-media-lab/issues/3)：EXP-02-02，good first issue。
  - [#4 Windows/CUDA独立复现](https://github.com/leongaooo/daily-media-lab/issues/4)：REP-02-01，help wanted。
  - [#5 原创SVG](https://github.com/leongaooo/daily-media-lab/issues/5)：EXP-01-01，good first issue。
- 每项包含范围、文件入口、验收清单、环境门槛和证据限制；未指派给外部人员，也未声称已有贡献者参与。
- README中英文与贡献索引由任务搜索链接替换为上述实际Issue地址。

## 验证与限制

本轮无音频或生产代码行为修改。49项测试、合成/全解码/时间线结果沿用REP-01记录，没有将其冒称为本轮重跑。准备阶段82个本地文档链接、三个模板结构、7项样本哈希通过。发布前33个未发布历史blob检查未发现禁止文件路径或常见凭据签名；后续文档提交按相同规则检查。模板只作结构检查，GitHub实际显示为运行证据。Issue公开不意味着贡献量或流量已经增长。

初次保存长命令被自动执行策略拒绝，改为范围明确的文件补丁及短命令完成；未依赖该失败动作的任何输出。
