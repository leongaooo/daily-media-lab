# Blender → PNG母版 → 成片的最小校色样例

这个技术样例生成原创静态色卡和一秒静音，检查镜头帧映射、字幕保护区、冻结输入及颜色往返。它不是新闻、口播、叙事代表片段、显示器物理校准或用户审美样本。没有声音克隆、私人参考或TTS；静音不能作为“口播音质通过”的证据。

本目录只提交代码和说明，**不提交生成的.blend、PNG、WAV、MP4及运行回执**。统一把产物放仓库outputs或仓库外。颜色与校准几何为自写MIT代码；Blender、字体、Remotion等工具各自遵守原许可。

## 依赖与输出

使用现有 [渲染依赖](../../skills/news-to-video/assets/requirements.txt)，不添加新requirements：Python、numpy、Pillow、soundfile和imageio-ffmpeg。另需Node／固定Remotion、浏览器、FFprobe、中文字体以及Blender **4.4.3**。场景固定EEVEE、AgX、1920×1080、24fps，不能静默换版本／引擎；其他版本应另行验证后明确修改。Blender脚本在Blender自身Python中运行，不用pip安装bpy。

运行时产物由以下步骤创建，不随代码预置伪哈希或成功回执：

| 产物 | 用途 |
| --- | --- |
| calibration.blend、shots.json | 可编辑源与实际内容哈希，局部1—24对应全局[0,24) |
| patches.json | 色片位置、内缩采样框、场景线性输入和比较边界 |
| silence.wav、cues.json、project.json | 24000Hz／24000样本／单声道原创静音，准确[0,1)cue与external_final身份 |
| frames、receipts | 24张PNG母版与真实逐帧内容回执 |
| delivery/video.mp4、decoded.png、roundtrip-report.json | 合成结果、编码后抽帧及色片均值比较 |

## 生成源与最终输入

在仓库根目录执行，将示意变量换为自己的实际路径；不会使用作者盘符或私人runtime。--output可为任意可写位置，但源脚本拒绝覆盖同名已有产物；重复实验使用新目录，不能为重试覆盖旧已确认项目。

```powershell
$renderPython = '<render-env>/Scripts/python.exe'
$blender = '<Blender-4.4.3-executable>'
$example = (Resolve-Path './examples/blender-calibration').Path
$output = [IO.Path]::GetFullPath('./outputs/blender-calibration')
$runtime = '<render-only-runtime.json>'
$ffprobe = '<ffprobe-executable>'

& $blender --background --python-exit-code 1 `
  --python "$example/generate_scene.py" -- --output $output
& $renderPython "$example/prepare_input.py" --output $output
```

generate_scene默认只存.blend、shots及patches，不渲染；可显式加--preview产生单帧定妆，但这仍不代替后续完整序列。色片位于字幕保护区上方，脚本以实际正交相机投影检查，不假设ortho_scale横纵含义。prepare_input必须在源与采样框生成后执行，只创建本技术样例的静音与准确一秒cue，不读取任何声音profile或参考文字。

## 生成母版、项目预检与合成

先准备渲染依赖与工具，再生成母版。项目预检会验证真实帧，因此不能在尚无母版时把缺帧误认为TTS问题，也不能用零字节图或proxy绕过。

```powershell
& $renderPython './skills/news-to-video/scripts/blender_render.py' "$output/shots.json" --blender $blender
& $renderPython './skills/news-to-video/scripts/narrative_media.py' "$output/shots.json"
& $renderPython './skills/news-to-video/scripts/check_runtime.py' --runtime $runtime --project "$output/project.json"
& $renderPython './skills/news-to-video/scripts/render.py' "$output/project.json" --backend-only --runtime $runtime --output "$output/delivery"
```

runtime放仓库外，仅需font、remotion_install和ffprobe等渲染依赖配置，不含tts_python、voice_profile或私人参考。参见 [环境准备](../../docs/GETTING_STARTED.md) 和 [执行契约](../../skills/news-to-video/references/blender-handoff.md)。始终向check_runtime传入此external_final项目；省略--project会进入默认TTS检查，不是纯渲染检查。

最终音频按真实sha256、样本率／样本数／声道和processing_identity复用，playback_rate=1.0；不TTS、不变速、不降噪、不重拼。原始silence.wav与交付voice.wav应逐字节一致。正式合成使用24帧完整1920×1080母版，主视觉y904以下由公共字幕轨覆盖，不能缩成904高或重复套AgX。

## 检查编码与颜色往返

使用本渲染环境的FFmpeg提取最终视频第12帧（零起点），同静态场景的局部第13张母版比较。所选采样框避开色片边缘、来源标签及字幕；不能缩放图片后比较。FFprobe命令只读元数据，不证明颜色处理正确。

```powershell
$ffmpeg = & $renderPython -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())'
& $ffprobe -v error -show_entries 'stream=codec_type,color_range,color_space,color_transfer,color_primaries,r_frame_rate,nb_frames' -of json "$output/delivery/video.mp4"
& $ffmpeg -v error -i "$output/delivery/video.mp4" -vf 'select=eq(n\,12)' -frames:v 1 "$output/decoded.png"
& $renderPython "$example/compare_patches.py" --patches "$output/patches.json" `
  --master "$output/frames/000013.png" --decoded "$output/decoded.png" --report "$output/roundtrip-report.json"
```

色片输入是场景线性RGB，经过Blender一次AgX显示变换后，PNG码值不应直接等于那些输入数字。compare_patches比较**真实显示变换PNG母版**和最终编码抽帧的同框RGB均值，输出0—255尺度的最大色片均值通道差、逐片读数及输入哈希，不自动给审美或感知“通过”阈值。均值接近也不能证明纹理、运动、所有图像的色彩正确性或物理显示器校准；需要结合灰阶、暗部、饱和色实际检查，失败时回查显示变换、色彩转换、标签和范围。

## 本样例可以证明什么

使用者应记录自己实际版本、命令、完整解码／帧数、输入／母版身份、音频字节保留、抽帧和颜色比较结果；运行命令失败不能写成成功。本机同方法的实际记录由 [本批进度](../../docs/progress/2026-11-20-three-media-blender.md) 维护，不能自动等同于这份公开示例在新机器上通过。

一秒静音静态卡不证明真实新闻采编、三维叙事质量、完整口播听感、用户视觉认可或独立新机器安装，也不能替代15—30秒代表片段与真实整期。被用户拒绝的叙事画面仍须返修，不能借校色或技术播放通过升级为认可。公开有声制作另显式选择 [qwen-uncle-fu-v1](../../skills/news-to-video/references/public-voice.md)，或提供有合法使用依据的真正最终干声；本例的静音不可伪装成人声样本。
