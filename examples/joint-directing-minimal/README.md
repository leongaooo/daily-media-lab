# 联合事件与投影的24帧技术样例

本例用原创几何占位物、真实相机推进、同一任务A的图板动画和一秒静音，检查 `narrative_directing` 的实际项目消费路径。左侧多面体**不是服务器、产品复原、现场或观赏质量样板**；右侧曲线只是现有机制消费者的假设图，不提供性能、实际出力或调度证据。一秒刻意压缩到接口检查长度，不用来判断正式影片阅读停留、叙事节奏或配音听感。

这里只提交源码、事件JSON和说明，不提交生成的 `.blend`、PNG、WAV、MP4、运行回执或runtime。原创代码和几何适用仓库MIT；Blender、Remotion、字体等仍按各自许可使用。不读Key、不发图片请求、不调用TTS、不使用私人声音或新设计图片。原[校色样例](../blender-calibration/README.md)保留，此例检查不同路径，不覆盖它的源或产物。

## 依赖与真实入口

使用现有[渲染依赖](../../skills/news-to-video/assets/requirements.txt)、Blender **4.4.3**／EEVEE、Node／固定Remotion、浏览器、FFprobe及可读中文字体，不增加依赖。`generate_scene.py` 在Blender自身Python中运行，默认仅写源与实际投影；`prepare_input.py` 在渲染Python中运行并调用随库的源／联合计划校验器，母版尚未渲染时仅跳过帧存在检查，不伪造帧或成功回执。

| 文件 | 实际职责 |
| --- | --- |
| [directing.json](directing.json) | 全局24fps共享事件：approach `[0,6)`、panel `[4,8)`、prediction `[8,12)`、reschedule `[12,18)`、result `[18,24)`；没有policy或隐含政策结论 |
| [generate_scene.py](generate_scene.py) | 读取approach事件，逐整数帧写入相机关键帧，保持原创几何在左侧；导出真实源哈希、摄影采样哈希与24帧投影 |
| [prepare_input.py](prepare_input.py) | 验证真实源／摄影事件／依赖／映射与投影，创建24000Hz／24000样本／单声道PCM16原创静音、准确一秒cue及external_final项目 |

生成的 `project.json` 同时引用 `narrative_manifest:"shots.json"` 和 `narrative_directing:"directing.json"`。`shots.json` 将全局 `[0,24)` 映射到Blender局部1—24；摄影事件子集只有approach。`projection.json` 绑定相同source／camera／camera_events摘要、依赖清单及全局／局部映射，锚点来自当前相机实际投影；几何可见标记不证明遮挡。二维板面及任务移动由正式 `JointOverlay` 消费，源Blender不烘焙文字或曲线。

## 在仓库根目录执行

将变量换为自己的工具路径。产物放 `outputs/` 或仓库外的新空目录；脚本拒绝覆盖已有冻结项目，也拒绝在本样例源码目录里生成媒体。

```powershell
$renderPython = '<render-env>/Scripts/python.exe'
$blender = '<Blender-4.4.3-executable>'
$example = (Resolve-Path './examples/joint-directing-minimal').Path
$output = [IO.Path]::GetFullPath('./outputs/joint-directing-minimal')
$runtime = '<render-only-runtime.json>'

& $blender --background --python-exit-code 1 `
  --python "$example/generate_scene.py" -- --output $output
& $renderPython "$example/prepare_input.py" --output $output
& $renderPython './skills/news-to-video/scripts/blender_render.py' `
  "$output/shots.json" --blender $blender
& $renderPython './skills/news-to-video/scripts/narrative_media.py' "$output/shots.json"
& $renderPython './skills/news-to-video/scripts/check_runtime.py' `
  --runtime $runtime --project "$output/project.json"
& $renderPython './skills/news-to-video/scripts/render.py' "$output/project.json" --backend-only `
  --runtime $runtime --output "$output/delivery"
```

runtime放仓库外，仅含可读字体 `font`、固定依赖目录 `remotion_install`、`ffprobe` 等渲染路径，不填 `tts_python`、`voice_profile`、私人参考或图片配置。中文字体供合成层使用，Blender几何没有字体依赖。始终给check_runtime传 `--project`，省略会走默认TTS检测。音乐显式off，无独立声轨；静音仅用于这条技术支路，不当作真正口播或公开声音认可样本。真实公开新配音另显式选[公开声音](../../skills/news-to-video/references/public-voice.md)，合法最终干声仍按[冻结入口](../../skills/news-to-video/references/blender-handoff.md#冻结最终口播)处理。

母版是完整1920×1080、24fps、24张不透明PNG；主视觉不压缩到904高，y904—1080由公共字幕轨独立覆盖。源脚本逐帧检查占位物与锚点留在左侧，不借整体缩图给板面让位；图板使用当前消费者的真实字体边界门。

## 检查与修改边界

记录自己实际版本、命令、完整解码／24帧、源／母版回执和投影身份，比较 `silence.wav` 与交付 `voice.wav` 的SHA256，应逐字节一致。按0、5、8、11、15、18、23等零起点帧检查相机接近、板面／曲线显现、同一task.id及宽度不变、任务移动与“调整后”终态；1秒不是足够阅读时间，逐帧结构检查不代表连续观赏通过。渲染未实际执行或命令失败时不能补写成功回执。

板面文字／task位置等图形修改只重合成，有效 `.blend` 与PNG应保留；只改approach时旧摄影事件摘要应被拒绝，需要从新空目录重新生成真实相机／源／投影并渲染，不通过手改哈希沿用旧摄影。源／依赖／取帧映射变动同样使旧投影失效。具体规则见[项目联合导演](../../skills/news-to-video/references/blender-handoff.md#项目联合导演接入)；不要把完整directing.json列成三维依赖，否则只改文案也会误触三维重算。

源码、JSON或离线校验成功只说明当前检查层；本例自身不证明真实服务器设计、联合叙事质量、人耳试听、用户认可或独立新机器安装。主实施者在[本批进度](../../docs/progress/2026-11-20-joint-directing-v3.md)记录本例实际运行和未验范围，本目录不预置作者机器的成功结论。
