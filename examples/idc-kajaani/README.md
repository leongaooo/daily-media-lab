# 卡亚尼首座数据中心混合分镜

原始口播和事实分别保存在 [narration.json](narration.json) 与 [evidence.json](evidence.json)。图形、建筑和路线均为原创示意。实际结果见[制作记录](../../docs/progress/2026-11-27-idc-kajaani.md)。

先准备[公开语音运行环境](../../skills/news-to-video/references/public-voice.md)、Blender 4.4.3、Edge 或 Chromium，以及渲染 Python 上的 Playwright 1.61.0。以下命令使用 PowerShell，从仓库根运行。工作目录位于日期化媒体根内，留出至少 2 GiB。

```powershell
$repo = (Resolve-Path '.').Path
$example = Join-Path $repo 'examples/idc-kajaani'
$skill = Join-Path $repo 'skills/news-to-video'
$scripts = Join-Path $skill 'scripts'
$job = '<绝对媒体工作根>/jobs/2026-11-27/idc-kajaani'
$runtime = '<公开 runtime.json 的绝对路径>'
$profile = Get-Content -Raw $runtime | ConvertFrom-Json
$py = $profile.python
$blender = '<Blender 可执行文件>'
$env:NEWS_TO_VIDEO_BROWSER = '<Edge 或 Chromium 可执行文件>'

New-Item -ItemType Directory -Force "$job/source" | Out-Null
Copy-Item "$example/narration.json","$example/evidence.json" $job
Copy-Item "$example/source/*.py","$scripts/mixed_shot*.py" "$job/source/"
Copy-Item "$skill/assets/illustration-kit/liquid-cooled-server-rack.svg" "$job/source/rack.svg"
& $py "$job/source/freeze.py" $job --scripts $scripts --runtime $runtime
& $py "$job/source/prepare.py" $job
& $blender --background --factory-startup --python-exit-code 1 --python "$job/source/campus.py" -- $job
& $py "$job/source/visuals.py" $job --browser $env:NEWS_TO_VIDEO_BROWSER
& $py "$job/source/prepare.py" $job --manifest
& $py "$scripts/narrative_media.py" "$job/shots.json" --seal
& $py "$scripts/check_runtime.py" --runtime $runtime --project "$job/project.json"
& $py "$scripts/render.py" "$job/project.json" --output "$job/output" --runtime $runtime --min-free-bytes 2147483648
& $py "$scripts/render.py" "$job/project.json" --output "$job/silent-compose" --runtime $runtime --min-free-bytes 2147483648 --picture-only
& $py "$job/source/verify.py" $job --probe $profile.ffprobe --browser $env:NEWS_TO_VIDEO_BROWSER --output "$job/deliverables"
```

按顺序运行，各步成功后再继续。公开音色每次按实际 cue 排帧。验证脚本复核两版流、正式 SRT、编码画面与 Edge 原速播放。原创代码与图形随仓库采用 MIT 许可，公开音色由使用者本地生成。
