# 从一个具体任务开始

无需先承诺完成整个开发阶段。在对应 Issue 评论认领范围即可。任务状态只在 [ROADMAP](../../ROADMAP.md) 维护，Issue 承载讨论、认领及验证证据；下面的任务说明是发布时范围。

| 任务 | 参与门槛 | 讨论入口 |
| --- | --- | --- |
| EXP-02-01 · 10组中文读法样例 | 无需GPU，适合内容贡献者 | [Issue](https://github.com/leongaooo/daily-media-lab/issues?q=is%3Aissue+EXP-02-01) |
| REP-04-01 · 无GPU单元测试CI | Python与GitHub Actions | [Issue](https://github.com/leongaooo/daily-media-lab/issues?q=is%3Aissue+REP-04-01) |
| EXP-02-02 · 手机字幕反馈 | 无需编程，真实设备或注明模拟 | [Issue](https://github.com/leongaooo/daily-media-lab/issues?q=is%3Aissue+EXP-02-02) |
| REP-02-01 · 独立Windows/CUDA复现 | 已有NVIDIA设备，无需购买硬件 | [Issue](https://github.com/leongaooo/daily-media-lab/issues?q=is%3Aissue+REP-02-01) |
| EXP-01-01 · 单张原创SVG | Python/Pillow与合法字体，无需付费API | [Issue](https://github.com/leongaooo/daily-media-lab/issues?q=is%3Aissue+EXP-01-01) |

读法、字幕反馈、单张SVG为 `good first issue`；CI及独立机器复现为 `help wanted`。每项仅覆盖对应父任务的一部分。维护者可协助后续GPU合成或入片检查，贡献者如实说明自己完成的验证。

## EXP-02-01 · 中文读法

入口：`examples/public-voice-smoke/project.json`、`skills/news-to-video/references/project-format.md`。在 `examples/pronunciation/` 新增README与 `samples.json`，至少10组 `id/text/spoken/reason`。覆盖 API、Web3、v1.2.3、12.5%、2026年11月11日及整数、小数、混读；保持原数字含义，说明读法选择。用 `python -m json.tool` 检查JSON。不要求合成，不改后端、默认音色或全局词典；未试听不写“试听通过”。

## REP-04-01 · 自动回归

入口：`skills/news-to-video/assets/requirements.txt`、`scripts/test_*.py`。新增 `.github/workflows/python-tests.yml`，选择一个实际可运行的OS/Python组合，在main推送与PR时执行现有 `python -m unittest discover -s scripts -p 'test_*.py'`。明确工作目录，完整运行测试，失败返回非零。只读权限，无私有凭据，不下载模型、不装Qwen/torch/Remotion，不调用付费生图。提供真实Actions链接及环境，同步CONTRIBUTING本地命令。该任务不涵盖REP-04全部依赖锁。

## EXP-02-02 · 字幕观察

入口：`previews/editorial-silent.mp4`（18秒，无私人声音）、`previews/README.md`。在 `docs/feedback/` 提交一种设备的记录：设备/播放器、方向、显示尺寸、至少3个时间点截图及字幕原文。正常案例也可，不必制造问题。区分换行、字号、对比度、遮挡、显示过短等观察并提建议。说明真实手机或桌面模拟；截图去除通知和账号信息。不将独立WAV与历史视频拼成同步证据，不宣称WCAG认证或群体研究。本次先收集反馈，不重写布局。

## REP-02-01 · 新机器复现

入口：[开始使用](../GETTING_STARTED.md)、[公开声音](../../skills/news-to-video/references/public-voice.md)和Editorial运行说明。使用另一台Windows/NVIDIA机器、新建Python环境与独立缓存，从安装到公开短片。模型约2.5GB，现有实现要求CUDA，维护者仅验证RTX3060Ti 8GB；不保证其他显存规格。记录OS、GPU/显存、驱动、Python、torch/CUDA、Node、Remotion、FFprobe、commit、完整命令、失败与修复。提交 `docs/reproduction/` 脱敏记录、validation、字幕覆盖和解码结果；实际试听则注明设备。失败记录也欢迎。不提交模型/字体/浏览器/runtime/profile或私人日志。不把单机成功扩展为所有平台支持，也不代替REP-02完整安装锁与教程验收。

## EXP-01-01 · 原创SVG

入口：公开声音project中的三节点、[SVG规范](../../skills/news-to-video/references/svg-standard.md)、`assets/svg-examples/review.svg` 与 `scripts/svg_to_png.py --help`（均位于制作技能目录）。新增 `examples/public-voice-smoke/diagrams/voice-timeline.svg`，720×480，仅表达“公开内置音色→实测语音→连续字幕”。使用支持的基础元素，无外链字体/图片；不改默认构图。交付SVG、PNG、转换报告、命令、字体来源、前后图和设计理由；文字完整可读。关系依据为当前project及render.py，不增加“自动逐字对齐”等无证据能力。素材必须有权公开；无需GPU或生图API，维护者可协助入片检查。

[贡献规范](../../CONTRIBUTING.md) · [新建Issue](https://github.com/leongaooo/daily-media-lab/issues/new/choose)
