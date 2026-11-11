# 第三方素材说明

项目自有代码许可证不覆盖第三方音乐、声音、模型、字体及其他依赖。下面记录本次导出的实际素材信息，不替代各来源的许可原文。

## 音乐

技能保留当前音乐池的三首曲目、manifest、署名与许可证据快照：Voice Over Under、Tech Live、Inspired。来源及文件身份见 `skills/news-to-video/assets/music-pool/manifest.json`。这些曲目不是本仓库原创。

“Voice Over Under” Kevin MacLeod (incompetech.com)

Licensed under Creative Commons: By Attribution 4.0 License

Source: https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1600001

License: https://creativecommons.org/licenses/by/4.0/

本仓库 `previews/music-preview.mp3` 截取 20 秒，做淡入淡出及 MP3 转码；未改变速度。完整其他曲目署名见 [ATTRIBUTION.txt](skills/news-to-video/assets/music-pool/ATTRIBUTION.txt) 和 manifest。发布混音或成片时需把该次输出的署名带入实际发布页面或片尾。

## 私人声音

私有参考录音、参考文字、profile 与模型权重不在仓库内。现有 B 声输出仅留在 Git 排除的本地审阅包。个人试听认可不等于允许公开传播或再分发；未取得适用授权前，不把它们作为公开开源资产。

## 图片与样片

预览画面来自已有 Web3 Editorial 工程。生成场景为示意，流程/状态关系由原创图解或组件表达；不是项目现场、真实设备或链上执行证明。记录见 [预览清单](previews/manifest.json)。维护者于 2026-11-11 明确确认现有预览图片可公开分发；这是本次发布的授权依据，不代表独立法律审查，也不自动适用于未来素材。私人声音仍不公开。

## 运行依赖

Qwen 模型、Remotion、FFmpeg、Python/Node 依赖与字体分别遵循其许可。当前仅导出技能自身的配置和实现，没有分发模型权重、浏览器、字体或 node_modules；正式发布时继续核对上游许可，不宣称整个生产工具链均为 MIT 或对所有团队均免费。
