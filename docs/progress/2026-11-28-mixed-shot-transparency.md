# EXP-09 · 混合分镜透明覆盖

透明 SVG 叠加 Blender 底图时，合成入口校验 PNG 中可透出的区域，逐像素比对透明区和原始三维底图，按当期预设的变化窗口检查画面。纯二维允许全幅背景。路线证据归属、拍摄机位投影、冻结词点和同母版双版检查见[混合分镜渲染](../../skills/news-to-video/references/mixed-shot-render.md)和[视觉导演](../../skills/news-to-video/references/visual-director.md)。

公开的 [IDC 混合分镜示例](../../examples/idc-mixed-shot/README.md) 使用同一合成入口，封存合成 helper 与投影，带声和仅画面复用项目与母版。带声输出附独立 SRT。示例继续使用公开声音适配，已有合法最终干声走冻结入口。

在技能目录运行 `python -m unittest discover -s scripts -p 'test_*.py'`，公开工作副本通过 196 项，含六项透明合成回归和原有公开声音回归。两侧技能格式校验及 Python 格式检查通过。新增提示词用例 118–119 用于描述回归预期。

本机公开适配实跑示例的 `prepare.py`、`visuals.py`、`narrative_media.py --seal`、`check_runtime.py` 和 `render.py --backend-only`。短测试使用 50 张已有公开示例的 Blender 底图和 24 kHz 合成测试音。同一项目输出两版各 200 帧，FFprobe 核实带声版含音流、仅画面版只有视频流，FFmpeg 完整解码通过。带声版 SRT 存在，合成回执记录静音版关闭烧录字幕。

本批公开范围为代码、说明、公开示例与合成测试。现场手机、人工试听及独立新机器尚无本批验收记录。公开维护入口在首次确认中明确推送范围，并沿用同批选择完成交付。
