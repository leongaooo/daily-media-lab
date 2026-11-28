# IDC 混合分镜渲染

静态数据、分步高亮、局部放大和回到同框可在同一条 SVG 时间线上编排。设备的轮廓、层板和端口表示设备类型，按当期证据标明示意范围。三维小场景从第一帧显示路线和主要地点，动作到达后保留终态。固定机位时用 Blender 的 `screen_point` 投影标注锚点。机位变化时为当前帧重算投影。

1. 在当期作业中用 `scripts/mixed_shot.py` 的 `PictureState` 和 `render_states` 栅格化原创 SVG。使用 `eased_progress` 将明确的状态变化限定到指定整数帧窗口。固定画面复用同一键。带三维底图的画面将 SVG 标注与当帧合成。
2. 在 Blender 脚本用 `scripts/mixed_shot_blender.py` 的 `block`、`arrow`、`route_keys` 和 `screen_point` 组织小场景。可编辑场景、原始帧、投影数据、SVG 和助手源码随作业保留。回看正式合成会添加左上角镜头标签，勿在该区域写栏目或标题，并让 y904–1080 留给正式字幕。
3. 按 `narrative_version: 1` 同时登记 SVG 与 Blender 镜头，引用冻结口播及 cue。用 `narrative_media.py shots.json --seal` 封存实际帧和依赖。带声和静音共用同一个项目与母版，用不同输出目录。

```powershell
python scripts/check_runtime.py --project '<job>/project.json' --runtime '<runtime.json>'
python scripts/render.py '<job>/project.json' --backend-only --output '<job>/output' --runtime '<runtime.json>'
python scripts/render.py '<job>/project.json' --backend-only --output '<job>/silent-compose' --runtime '<runtime.json>' --picture-only
```

`--picture-only` 使用冻结 cue 保持时轴并生成仅含视频流的 MP4。独立 SRT 保存在带声输出。浏览器截图遇到资源不足时先核对磁盘和活动进程，可在当期项目将 `editorial.render.concurrency` 设为 `1`，并关闭 `parallel_encoding` 后重试。

从编码结果抽查画面主体、路线首帧和到达帧、镜头标签、首末字幕及两版主体一致性。用连续播放和轨道检查记录技术结果，人工体验与用户验收各自登记。
