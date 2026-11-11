# 公开声音配置 · REP-01

`qwen-uncle-fu-v1` 使用官方 `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` 的内置 `Uncle_Fu`，语言为 Chinese。不需要参考录音、参考文字或私人哈希；不调用声音克隆。选它是为了给中文说明提供可独立下载的男声入口，不表示与私人 B 声听感相同。

模型卡声明 Apache-2.0，并列出该内置音色。固定版本为 `85e237c12c027371202489a0ec509ded67b5e4b5`；[策略](../assets/public-voice-policy.json)固定所有下载文件的 SHA-256、采样设置和缓存身份。[来源快照](../assets/voice-evidence/sources.json)、[模型卡](../assets/voice-evidence/model-card.md)及[上游许可证](../assets/voice-evidence/Qwen3-TTS-LICENSE.txt)随仓库保留。第三方模型不改标 MIT；本仓库不分发模型权重。自写测试文案不含第三方新闻或私人录音。

## 准备与运行

先准备渲染 Python 和独立 Qwen Python，分别安装 `assets/requirements.txt`、`assets/requirements-qwen.txt` 中依赖；CUDA、中文字体、Node、Remotion 和 FFprobe 仍按[本地运行](local-runtime.md)及[Editorial](remotion-editorial.md)准备。以下是已有环境的连接命令，不是 REP-02 的干净机器安装证明。

在仓库根目录执行，将示意路径换为真实路径：

```powershell
$renderPython = '<render-env>/Scripts/python.exe'
$ttsPython = '<qwen-env>/Scripts/python.exe'
$modelDir = '<model-cache>/Qwen3-TTS-12Hz-0.6B-CustomVoice'
$publicCache = Join-Path $HOME '.cache/news-to-video/public-voice'
& $renderPython './skills/news-to-video/scripts/setup_public_voice.py' `
  --cache $publicCache --model $modelDir --download `
  --render-python $renderPython --tts-python $ttsPython `
  --font 'C:/Windows/Fonts/msyh.ttc' --ffprobe '<tools>/ffprobe.exe'
$publicRuntime = Join-Path $publicCache 'runtime.json'
& $renderPython './skills/news-to-video/scripts/check_runtime.py' --runtime $publicRuntime
& $renderPython './skills/news-to-video/scripts/render.py' `
  './examples/public-voice-smoke/project.json' `
  --runtime $publicRuntime --output './outputs/public-voice-smoke'
```

`--download` 才联网，下载约 2.5 GB；已存在且哈希匹配的文件直接复用。下载固定 revision，校验成功才替换目标，失败清理 `.partial`。不传此参数仅检查已有模型。模型与运行环境均应放在仓库外。

setup 只连接模型、解释器和字体；不安装软件、不做完整设备预检。候选配置检查失败不会覆盖已有 runtime；成功写入公开专用目录，默认私人 runtime 不变。`check_runtime.py` 再检查渲染依赖、字体、音乐池、Qwen 导入及 CUDA；真正模型加载与合成仍需运行样本。

## 项目、缓存与验收

项目必须显式设置 `"voice": {"id":"qwen-uncle-fu-v1","speed":1.15}`。省略 ID 仍是私人 `b-male-v1`，与公开 runtime 混用会报错，不会自动换声音。旧 Web3 示例保持原有 ID；完整公开示例由 REP-03 处理。

原生音频按模型文件、speaker、language、采样设置、后处理版本与口播文本缓存；与私人 B 声隔离。变速/轻度降噪继续按音频内容和参数缓存，字幕按处理后的实测语音时长生成。仅改音乐不重做配音。

检查 `validation.json` 的 `voice.id`、`model_sha256.speaker`、`continuous_captions`、`full_decode_passed`；`timeline.json` 第一条从零开始、相邻字幕无空隙、最后一条覆盖片尾。这是语义片段计时，不是 ASR 逐字对齐。人耳另听原速读音、默认 1.15 倍速度、停顿和尾字；当前默认短样本已获维护者“挺好的”的整体听感认可；该结论不自动延伸到其他文稿、倍率或播放设备。

本轮实际证据与限制见 [REP-01 进度](../../../docs/progress/2026-11-11-public-voice.md)。
