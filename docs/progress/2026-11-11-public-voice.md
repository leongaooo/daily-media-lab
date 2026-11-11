# REP-01 · 公开内置声音接入

日期：2026-11-11（Asia/Shanghai）。负责人：当前 Codex agent。任务状态只在根目录 ROADMAP 维护。

## 目标与实现

从发布基线 `136c50a` 开始，工作区原先干净。为陌生使用者提供无需私人录音的显式声音入口，保留旧 B 项目和原默认 runtime，不静默换声。

- `assets/public-voice-policy.json`：固定官方 Qwen 0.6B CustomVoice revision `85e237c12c027371202489a0ec509ded67b5e4b5`、全部12个文件 SHA-256、Uncle_Fu、Chinese、采样设置。模型卡 Apache-2.0 与上游许可证/来源快照位于 `assets/voice-evidence/`，第三方声明同步。
- `scripts/public_voice.py`：公开 profile 仅允许 id/model_dir；全文件校验和缓存身份；显式下载、校验后原子替换及失败清理。
- `scripts/setup_public_voice.py`：独立公开 runtime 配置，不安装依赖；失败保留已有 runtime。模型及环境保存在仓库外。
- `voice_backend.py` / `qwen_synth.py`：按 ID 分派内置声音或私人 ICL；公开分支不创建 clone prompt，不读取私人参考。项目/runtime ID 不同在合成前停止；缓存隔离。
- `render.py` 保留项目指定 ID，制作计划记录实际音色；`migrate_audio.py` 保留已支持公开音色与倍率。
- `test_public_voice.py` 覆盖无私人参考、配置混用、篡改与缺文件、下载失败保留、setup失败保留及迁移兼容。中英 README、技能/运行/配音/格式文档同步；没有改本机 `.agents` 维护源。
- `examples/public-voice-smoke/`：两段自写中文、原速及默认速度音频、字幕/时间线/验证/文件哈希。无新闻素材、图片或音乐授权依赖。

## 实际命令与环境

以下从仓库根目录执行，解释器路径为本机既有环境；不是新机器安装验证。`$renderPython` 指既有渲染环境，`$ttsPython` 指既有 Qwen 环境。

```powershell
& $renderPython skills/news-to-video/scripts/setup_public_voice.py `
  --model D:/AppCache/CodexVoice/models/Qwen3-TTS-12Hz-0.6B-CustomVoice `
  --tts-python $ttsPython --font C:/Windows/Fonts/msyh.ttc `
  --ffprobe "$HOME/.cache/news-to-video/tools/ffprobe.exe"
& $renderPython skills/news-to-video/scripts/check_runtime.py `
  --runtime "$HOME/.cache/news-to-video/public-voice/runtime.json"
& $renderPython skills/news-to-video/scripts/render.py `
  examples/public-voice-smoke/project.json `
  --runtime "$HOME/.cache/news-to-video/public-voice/runtime.json" `
  --output outputs/rep-01-public-voice
# 在 skills/news-to-video 目录执行：
& $renderPython -m unittest discover -s scripts -p 'test_*.py'
```

本轮先根据官方 API 的固定 revision 获取小文件哈希，并使用公开下载函数获取与校验权重；共享 tokenizer 权重从本机已有缓存复制后按同一公开 SHA-256 再校验。通用 `--download` 入口支持其他机器从固定官方 URL 下载全部文件。模型约2.5GB，不入 Git。

环境：Windows / Python 3.13.3，RTX 3060 Ti 8GB，torch/torchaudio 2.9.1+cu126，qwen-tts 0.1.1，transformers 4.57.3，accelerate 1.12.0，bfloat16 / SDPA，CPU加载后转CUDA；已有Node/Remotion/FFprobe与微软雅黑字体。模型与私人运行配置均未加入仓库。

## 结果与证据边界

- 49 项单元测试通过。测试日志中的模拟图像请求和模拟失败来自 mock，不是实际付费生图。
- `check_runtime.py` 通过，voice_id 为公开 ID，CUDA 为 RTX 3060 Ti，fallback_voice 为 null。SoX/flash-attn 缺失警告仍存在，本机本次合成成功。
- 实际合成两段中文成功；默认1.15倍、轻度降噪后时间线9.875秒；原速处理样本11.333秒。改变速度命中原生声音缓存，无需重新合成。
- 1920×1080 / 24fps / 237帧，H.264/AAC 成片完整解码通过，峰值约0.78，无音乐。字幕从零开始、相邻连续、最后结束9.875秒，语音尾部均落在字幕区间内；不是ASR逐字对齐或发音正确性证明。
- 最终流程图分镜已看图，三节点为实际实现的音色、音频计时、字幕过程；底部字幕轨独立。未作完整逐帧美学审阅。
- 可复核样本、哈希与渲染报告见 [短样本](../../examples/public-voice-smoke/README.md)。MP4留在忽略的 `outputs/`。
- Black未安装；按既有四空格和多行调用手工整理修改范围，分别检查注释/制作说明与实际分支一致性、文档链接及 `git diff --check`。

## 未解决与下一步

维护者人耳试听尚未完成，不能声称音色或发音已认可，因此 REP-01 保留待验证。试听两份样本后记录反馈；如需调整，保持公开ID与缓存身份明确。REP-02新机器首装、REP-03完整Web3示例尚未开始。未改写历史样片，未推送远程。

上游 GitHub API 查询遇到速率限制403，改用 `git ls-remote` 取得实际HEAD并保存固定commit的LICENSE；没有创建凭据或绕过登录设置。

## 后续试听收口（2026-11-11）

2026-11-11：维护者试听默认1.15倍公开样本后反馈“挺好的”；认可当前短样本整体听感。未单独确认原速对照、逐词读音或其他设备。 用户随后授权立即推进社区贡献入口和Issue发布。REP-01据此收口；前述“待反馈”保留为当时记录，新机器验证与完整Web3示例仍独立验收。
