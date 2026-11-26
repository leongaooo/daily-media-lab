# E 盘媒体作业治理回放

2026-11-26，事项 OPS-03。把本机 `E:/CodexMedia` 的 news-to-video 高频目录、交付后即时清理和下一工作日跨日清理接入制作规则。公开副本保留同一入口与合成回归，不提交本机媒体、私人声音、运行时或凭据。

## 受管目录

- `jobs/YYYY-MM-DD/<episode>/output`、`frames`、`composition`、`preview`、`review`、`audio`、`source`、`sources`、`cache`、`tmp`
- `E:/CodexMedia/cache/YYYY-MM-DD/<owner>` 跨作业可再生缓存
- `E:/CodexMedia/governance/YYYY-MM-DD` 盘点、清理和保留回执

`E:/CodexMedia/codex-archives`、`codex-sessions` 和 `visualizations` 由各自应用管理。跨日工具只枚举 `jobs` 和日期化 `cache`，不会把其他应用目录误删。

## 今日实测

### 交付后即时清理

本期已完成技术交付后回收 4 个确认可再生的 Webpack pack。回执位于 `E:/CodexMedia/governance/2026-11-26/post-production-cleanup.json`，删除文件字节数为 `518014046`，卷余量实际增加 `518021120` 字节。正式片、静音对照、SRT、来源、冻结音频和验收回执继续按本期发布记录保存。

### 次日跨日干跑

使用 `cross_day_storage.py --root E:/CodexMedia --as-of 2026-11-27` 对真实媒体根生成 `next-day-dry-run.json`。盘点 16 个受管条目，其中 14 个按用户要求标记为前一天及更早的待清理候选，2 个未日期化缓存保留。实际干跑显示 10 个条目可移除，共 `65956933183` 字节，4 个条目因嵌套锁或链接状态跳过，未删除真实旧作业。

### 合成夹具实际删除

在隔离夹具中复做 dry-run 和 `--apply`。旧作业与日期化可再生缓存各删除 24 字节，当前日期作业、活动锁和未归属缓存均保留。回执为 `E:/CodexMedia/governance/2026-11-26/cross-day-fixture-replay.json`，夹具目录已在回放后移除。

## 代码与回归

- 新增 `skills/news-to-video/scripts/cross_day_storage.py` 和 `test_cross_day_storage.py`。
- `local-runtime.md` 记录 E 盘高频目录、交付后即时清理、次日 MP4/帧/暂存/素材审查和回执位置。
- CI 增加媒体治理单元回归。canonical 的媒体治理与跨日测试共 10 项通过，新增脚本 `py_compile` 通过。
- 默认 Python 环境未安装 `black`，本次改用已存在的仓库 formatter 目录执行 `black --check`，4 个媒体治理脚本通过；`py_compile` 和 `git diff --check` 也通过。

## 下一工作日执行

以当天北京时间日期生成新的审查清单和回执。对前一天及更早的 MP4、帧、暂存和素材先确认已迁移的发布成品、来源、冻结音频和恢复入口，再对 `remove` 项运行 `--apply`。活动锁、链接、日期不明和未审查路径继续写入 `skipped` 或 `retained`，不隐式删除。
