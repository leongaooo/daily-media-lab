# IDC 混合分镜渲染

静态数据、分步高亮、局部放大和回到同框可在同一条 SVG 时间线上编排。先按[视觉导演](visual-director.md#路线关系与证据归属)确认要表达的是空间关系、方向还是实际运动。固定机位和锚点时用 Blender 的 `screen_point` 导出一次投影。相机或锚点移动时按当前帧重算。

1. 在当期作业中用 `scripts/mixed_shot.py` 的 `PictureState` 和 `render_states` 栅格化原创 SVG。相同画稿及底图模式复用同一状态键。纯二维镜头可以保留整幅背景。叠加 Blender 时只绘制有意覆盖的部分，保留应露出的底图区域为 `Alpha=0`。Chromium 的 `omit_background` 只清除浏览器默认底色，显式 SVG 或 CSS 全屏底色仍会入图。
2. 正式横屏调用 `render_states(job, page, states, protected_y=904)` 检查覆盖层像素进入字幕轨的情况。混合合成拒绝没有 `Alpha=0` 的覆盖 PNG，并在编码前逐像素检查透明区 RGB 与对应 Blender 底图相等。可用 `verify_overlay_pixels` 对重新读取的母版复核。检查首、中、尾和切换前后，确认实际透出的主体面积符合设计。纯二维的背景和输出模式沿用原路径。
3. 按 `narrative_version: 1` 同时登记 SVG 与 Blender 镜头，引用冻结口播及 cue。用 `narrative_media.py shots.json --seal` 封存实际帧和依赖。带声和静音共用同一个项目与母版，用不同输出目录。
4. 用 `eased_progress` 将变化限制在设计好的整数帧窗口。用 `verify_motion_windows(folder, [(start, end), ...])` 检查必须变化的镜头局部区间，帧号从 1 开始，右边界不含。检查解码像素是否变化，并看前、中、后帧确认变化确实落在预期对象。阅读停留可重复用帧。可编辑场景、原始帧、投影、SVG 和助手源码随作业保留。给合成的左上角镜头标签与底部字幕留空间。

```powershell
python scripts/check_runtime.py --project '<job>/project.json' --runtime '<runtime.json>'
python scripts/render.py '<job>/project.json' --backend-only --output '<job>/output' --runtime '<runtime.json>'
python scripts/render.py '<job>/project.json' --backend-only --output '<job>/silent-compose' --runtime '<runtime.json>' --picture-only
```

`--picture-only` 使用冻结 cue 保持时轴并生成仅含视频流的 MP4。独立 SRT 保存在带声输出。浏览器截图遇到资源不足时先核对磁盘和活动进程，可在当期项目将 `editorial.render.concurrency` 设为 `1`，并关闭 `parallel_encoding` 后重试。

公开项目需重新配音时，沿用公开声音入口及独立运行环境。确定最终音频与处理身份后，再按实测 cue 重做整数帧边界和 SRT。已有合法冻结原声以 external_final 接入并保持 1.0 倍。

编码后按[同画面对照](refinement-workflow.md#同画面对照)复核两版。带声版核对口播字幕、动作词点和尾音，静音版检查同一时点的主体、画内事实及字幕轨。
