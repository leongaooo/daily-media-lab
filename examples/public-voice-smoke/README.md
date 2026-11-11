# 公开声音短样本

任务 REP-01：官方 Qwen 0.6B CustomVoice 内置 Uncle_Fu，无私人参考，测试文案为本仓库自写。模型 Apache-2.0 依据见[第三方声明](../../THIRD_PARTY_NOTICES.md)与[固定策略](../../skills/news-to-video/assets/public-voice-policy.json)。

- [默认 1.15 倍试听](voice-speed-1.15.wav)：9.875 秒，变速后轻度降噪。
- [1.0 倍试听](voice-speed-1.0.wav)：11.333 秒，原速、同样轻度降噪。
- [项目](project.json)、[字幕](captions.srt)、[时间线](timeline.json)、[渲染检查](validation.json)、[文件校验](verification.json)。

两段字幕覆盖默认样本全长；不是 ASR 逐字对齐。完整视频在运行后输出到 `outputs/`，不为该短测试重复分发字体或模型。无音乐，无额外署名音乐要求。

[复现命令](../../skills/news-to-video/references/public-voice.md)。本轮是已有 Windows/CUDA 环境验证；新机器安装与完整 Web3 示例分别由 REP-02、REP-03 验收。2026-11-11 维护者试听默认1.15倍样本后反馈“挺好的”，认可当前短样本整体听感。原速对照未获单独评价；不是逐词读音或跨设备验收。
