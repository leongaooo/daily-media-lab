# 本地运行

当前默认适配文件仍为 `~/.cache/news-to-video/runtime.json`，也可用 `--runtime` 或 `NEWS_TO_VIDEO_RUNTIME` 指定。只启用 B 版男声，不再配置或下载旧引擎。

画面只使用[Remotion Editorial](remotion-editorial.md)，需要本机Node、固定Remotion运行环境、Chrome/Edge或Headless Shell及独立FFprobe。

```json
{
  "python": "渲染环境Python完整路径",
  "tts_python": "Qwen环境Python完整路径",
  "font": "中文字体路径",
  "voice_id": "b-male-v1",
  "voice_profile": "技能外的私有profile.json",
  "music_manifest": "技能目录/assets/music-pool/manifest.json",
  "remotion_install": "技能外Remotion安装目录，可省略使用本机默认",
  "ffprobe": "独立FFprobe可执行文件路径"
}
```

本机已配置：渲染解释器沿用 `~/.cache/news-to-video/env/Scripts/python.exe`，Qwen 解释器为 `<private-voice-runtime>/qwen3-env/Scripts/python.exe`，模型为 `<private-voice-runtime>/models/Qwen3-TTS-12Hz-1.7B-Base`。私有 B 参考与配置保存在 `<private-voice-runtime>/news-video-runtime/profiles/b-male-v1/`。不要把绝对路径当跨机器默认。

```powershell
$runtime = Get-Content "$HOME/.cache/news-to-video/runtime.json" -Raw | ConvertFrom-Json
& $runtime.python "./skills/news-to-video/scripts/check_runtime.py"
& $runtime.python "./skills/news-to-video/scripts/render.py" "项目.json" --output "成片目录"
```

本地音频、素材准备和分镜预览需要numpy、Pillow、soundfile、imageio-ffmpeg；Pillow仅作图片处理依赖，不提供视频渲染方案，版本在 assets/requirements.txt。Qwen 采用独立 Python 环境，关键依赖在 assets/requirements-qwen.txt；已验证 torch/torchaudio 2.9.1+cu126、qwen-tts 0.1.1、transformers 4.57.3、accelerate 1.12.0，RTX 3060 Ti 8GB、bfloat16、SDPA。CUDA 不可用时明确失败，无其他声音回退。本机可在缺 SoX/flash-attn 的情况下使用当前推理路径；相关库警告不等于生成失败。

模型来自官方 Qwen/Qwen3-TTS-12Hz-1.7B-Base，固定 revision fd4b254389122332181a7c3db7f27e918eec64e3。模型与 speech_tokenizer 权重哈希位于 assets/runtime-lock.json；语音缓存另包含实际配置、分词器、参考与采样设置身份。模型与私有声音放在技能外。运行阶段强制离线模型读取，不上传参考，不调用付费 API。

新机器需先准备渲染与 Qwen 环境、固定模型和用户认可的私有 B 参考，然后使用 setup_runtime.py 的 --font、--render-python、--tts-python、--model、--reference、--reference-text 参数连接。脚本不会安装旧引擎或创建替代声音；参考与当前认可哈希不匹配会停止。完整首装未在全新机器验证。

原创 SVG 使用 scripts/svg_to_png.py 转 PNG；受限图元标准见 svg-standard.md。图片 API 是可选、独立的已授权素材阶段，本机连接与独立凭据位于技能config/image-generation目录，凭据不进入交付包，详见 generated-images.md。render.py 本地读取素材，不联网生成图片。

音乐默认使用已下载免费成品池，安装不需要音乐订阅；公开发布需附输出的音乐署名.txt。声音策略、混音参数与旧项目迁移见 [audio-production.md](audio-production.md)。

## Windows权重加载兼容

本机torch 2.9.1+cu126与safetensors 0.8.0在直接device_map=cuda:0加载时，曾在torch.storage.__getitem__/transformers的权重切片路径发生原生access violation。qwen_synth.py已改为CPU加载同一固定权重，再整体转移主模型与speech tokenizer至CUDA，并同步两者device属性。参考、权重、精度、采样设置和推理设备不变；这不是换声或CPU推理回退。完整工程重配音采用此路径。ASR核对安排在TTS子进程结束后，以避免两套模型同时占用Windows提交内存。

长稿连续生成曾出现内存分配失败；voice_backend.py将未命中片段分为每批最多8段的独立进程，qwen_synth.py逐段释放生成结果并清理CUDA缓存。批次之间退出进程释放资源，已完成片段可恢复，不更换声音或采样设置。

唯一画面方案的固定依赖和参数见 [Remotion Editorial 画面模式](remotion-editorial.md)。

render.py省略--visual-engine时即执行remotion_editorial，不存在其他画面分支。FFprobe优先读取runtime.ffprobe，其次PATH及~/.cache/news-to-video/tools/；不依赖其他画面方案的安装目录。check_runtime.py同时检查Editorial运行依赖，缺失时停止。设置NEWS_TO_VIDEO_BROWSER可复用本机浏览器。
