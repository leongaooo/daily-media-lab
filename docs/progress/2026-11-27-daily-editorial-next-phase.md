# Daily Media Lab 下一阶段日更入口

日期：2026-11-27（Asia/Shanghai）

## 范围

本批把已确认的下一阶段方案落到公开 `news-to-video` 工作流。公开副本只包含编辑契约、结构校验、回归和文档，不包含本机私人 B 声、参考文字、模型权重、runtime、账号数据、抖音导出或本地成片。

## 实施

- 新增 `skills/news-to-video/references/daily-editorial-workflow.md`，规定观众问题、观众收获、工程进展/技术运维/采购供应链切入点、表达方式、交付标题、可选互动、方向研讨和手动复盘边界。
- 新增 `skills/news-to-video/scripts/daily_editorial.py`，校验日更计划、方向建议和用户明确发起的复盘记录。
- `skills/news-to-video/scripts/episode.py init --editorial-plan` 保存编辑计划文件身份，`verify` 检查计划未被替换。
- README、ROADMAP、HANDOFF 和评测规格补充该入口。新增规格 113–116。

## 验证

公开同步前在同一 Windows 主机完成结构回归和 Python 编译检查。公开副本使用已有公开声音适配和既有生产契约，未生成新的声音或视频。

- `python -m unittest discover -s skills/news-to-video/scripts -p 'test_*.py'` 使用冻结环境通过 190 项。
- `python -m json.tool skills/news-to-video/evals/evals.json` 通过。
- `git diff --check` 通过。
- `daily_editorial.py` 的计划、建议和复盘校验均有独立测试。

## 限制

本批证明结构入口、文件身份保护和编辑边界。它不证明最新新闻事实、观众反馈、平台发布、新机器安装、跨设备观看或人耳试听。日更实际发布仍由维护者控制，正式复盘仍需用户明确发起。

公开提交与远端验证见本文件对应的 Git 提交及 GitHub 远端 `main`。本地工作区 `D:/Dreamwork/daily-media-lab` 的既有未提交改动没有被本批清理或覆盖。
