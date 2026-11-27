# IDC 混合分镜复现

一条 1920×1080、24 fps 时间线内依次播放拟议拓扑、旧机房改造参考和模块进场示意。三条案例各自说明一个分镜问题。图形和场景由本例源代码现场生成，采用仓库 MIT 许可。

| 证据 | 本例取用的信息 |
| --- | --- |
| ODCC-EDGE-1126 | 两类节点、拟议交互规则和拟议一致性测试集。部署与测试结果待核。[ODCC 会议动态](https://www.odcc.org.cn/news/p-2125790864840908802.html) |
| SE-RD120-1125 | 以原有 4 条电力链及平均 20 kW／柜的机房为起点，移除 3 个机柜组，以 10 套 Helios 和 720 张 GPU 为参考配置。[施耐德电气 RD120](https://www.se.com/au/en/download/document/RD120DSR0/) |
| fluidstack-e01 | 模块化交付和现场组装的产品背景。地面路线、运载装置、转向和接收平台均为原创空间示意。[Fluidstack Blackbird](https://fluidstack.com/blackbird) |

## 在已有运行环境中复现

先配置[公开声音运行环境](../../skills/news-to-video/references/public-voice.md)。使用 Windows 上可访问的 Blender 4.4.3、安装了中文字体的本地 Chromium 或 Edge，以及渲染 Python 环境中的 Playwright。下面的命令使用 PowerShell。将工作目录设为新建的空目录，并预留至少 2 GiB。两份 MP4 与 SRT 写到单独交付目录。

```powershell
$repo = (Resolve-Path '.').Path
$example = Join-Path $repo 'examples/idc-mixed-shot'
$scripts = Join-Path $repo 'skills/news-to-video/scripts'
$job = '<新建的绝对作业路径>'
$runtime = '<公开 runtime.json 的绝对路径>'
$blender = '<Blender 4.4.3 可执行文件>'
$browser = '<Edge 或 Chromium 可执行文件>'
$profile = Get-Content -Raw $runtime | ConvertFrom-Json
$py = $profile.python
$env:NEWS_TO_VIDEO_BROWSER = $browser

New-Item -ItemType Directory -Force "$job/source" | Out-Null
Copy-Item "$example/narration.json" "$job/narration.json"
Copy-Item "$example/source/*.py" "$job/source/"
& $py "$job/source/freeze.py" $job --scripts $scripts --runtime $runtime
& $py "$job/source/prepare.py" $job
& $blender --background --factory-startup --python-exit-code 1 --python "$job/source/blackbird.py" -- $job
& $py "$job/source/visuals.py" $job --browser $browser
& $py "$job/source/prepare.py" $job --manifest
& $py "$scripts/narrative_media.py" "$job/shots.json" --seal
& $py "$scripts/check_runtime.py" --runtime $runtime --project "$job/project.json"
& $py "$scripts/render.py" "$job/project.json" --output "$job/output" --runtime $runtime --min-free-bytes 2147483648
& $py "$scripts/render.py" "$job/project-silent-picture.json" --output "$job/silent-compose" --runtime $runtime --min-free-bytes 2147483648
& $py "$job/source/verify.py" $job --probe $profile.ffprobe --browser $browser --output "$job/deliverables"
```

按顺序运行，任一步非零退出时先处理该步。`freeze.py` 以公开音色 `qwen-uncle-fu-v1` 实测句长。`prepare.py` 由句级 cue 生成整数帧边界。`blackbird.py` 由该边界生成可编辑 Blender 场景、三维帧及实际机位投影。`visuals.py` 生成可编辑 SVG、二维帧和三维标注层。两版经正式 Remotion 合成。带声版烧录字幕并交 SRT，静音版关闭口播字幕并从 MP4 移除音轨。检查读取编码文件并将记录写入 `review/encoded-checks.json`。

公开运行会按实测口播重新确定时长。技术与感知证据见[制作记录](../../docs/progress/2026-11-27-idc-mixed-shot-validation.md)。
