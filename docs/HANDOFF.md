# 当前交接

更新：2026-11-11（Asia/Shanghai）。先读根目录 AGENTS 和 ROADMAP；任务状态仅在 ROADMAP 维护。

## 当前焦点

REP-01 已接入公开内置男声 `qwen-uncle-fu-v1`，采用官方 Apache-2.0 Qwen 0.6B CustomVoice / Uncle_Fu。无需私人参考，项目必须显式选择公开 ID 并匹配独立 runtime。私人 B 声及默认 runtime 保留；未修改本机 canonical skills。

- [本轮实施与证据](progress/2026-11-11-public-voice.md)：49 项回归、实际模型合成、9.875 秒成片完整解码、字幕计时及本机环境。
- [试听入口](../examples/public-voice-smoke/README.md)：1.0 倍与默认 1.15 倍，无音乐。维护者人耳反馈尚缺，不能标记声音验收完成。
- [公开配置与复现命令](../skills/news-to-video/references/public-voice.md)：固定 revision 和所有文件哈希，模型另行下载；没有新机器首装证据。
- `outputs/rep-01-public-voice/` 为 Git 排除的实际完整渲染输出，含 MP4、干声/混音、字幕、时间线与验证 JSON。可提交短测试声音来自官方内置音色，不是私人 B 声。
- GitHub 发布基础的旧证据见 [发布记录](progress/2026-11-11-publication-foundation.md)。本轮未推送远程，也未检查新改动的 GitHub 页面。

## 下一步具体动作

1. 检查当前 Git 状态、提交与远程，不把历史发布 SHA 当作当前实现。
2. 获取维护者对两份声音的读音、尾字、停顿、速度与音色反馈；必要时调整公开配置并更新缓存身份、样本和证据。
3. 人耳验收证据齐备后再收口 REP-01，随后按 ROADMAP 依赖推进 REP-02 干净机器安装及 REP-03 完整公开 Web3 示例。旧 Web3 工程仍为私人 B 声，不代表已交付公开示例。
4. 无需等待声音反馈的独立项可选 REP-04，仍由唯一 ROADMAP 管理，不另建状态表。
