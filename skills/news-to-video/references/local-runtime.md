# Portable media runtime

## 作业根与暂存

为媒体资产选择有足够余量的可配置工作根，项目使用 `jobs/YYYY-MM-DD/<episode-id>/` 的稳定目录；重试沿用同一期目录。sources／audio／frames／output和回执使用现有项目格式，不需改schema。用户明确目录优先，技能安装源与大媒体分离，不要求特定盘符。

`render.py --output`显式指向job内output，现有Remotion暂存和`.cache`随output保留；跨job可再生缓存放工作根的cache目录。不把工作根示例当成CLI已支持的新配置项。开始前核对目标盘余量，计入PNG母版、合成暂存和输出，禁止默认使用系统盘聊天资产目录存大媒体。已有运行时不随该规则自动搬迁。

生产子进程的`TEMP`／`TMP`也指向选定工作根的cache或job内临时目录，避免Remotion打包、浏览器和编码临时文件仍落到系统盘。只给子进程传环境，或保存原终端值并在`finally`恢复；不修改系统全局环境，不新增runtime字段。仅迁output不等于全部进程临时文件已迁移。

迁移先停止写入、复制并逐项校验哈希，修正实际引用、核对恢复入口后再清理已验证重复件。只清理可识别归属本任务的可再生暂存；源、完整母版、冻结音轨、许可、回执和有效失败依据按用途保留。禁止按年龄、扩展名或模糊目录名清理用户及其他任务文件。

See [installation](../../../docs/GETTING_STARTED.md) for the explicit public voice and render-only routes. Existing final vocal mode needs Python with the declared requirements, Node/Remotion, a readable Chinese font and FFprobe. It does not need Qwen, model weights, a voice profile or private reference. Supply --runtime with a local JSON containing python, font, remotion_install and ffprobe; keep this file outside Git. NEWS_TO_VIDEO_BROWSER can point to an installed supported Chromium browser.

Blender 4.4.3 was tested locally with EEVEE on an RTX 3060 Ti. Use scripts/blender_render.py shots.json --blender <installed executable>; the executable path is configured by the caller. GPU and fresh installation on another machine remain unverified. Source, engine and worker identities must match; do not silently switch renderer.

For new public narration, explicitly select qwen-uncle-fu-v1 and follow [public voice](public-voice.md). Its separate profile, fixed weights, policy and tests are preserved. Local private b-male-v1 assets and audio are not distributed. For final narration supply a legitimately usable mono vocal, accurate cues and its actual sample/hash/processing identity; external_final never grants redistribution rights. Never place keys, weights, runtime, reference audio or private vocal samples in this repository.

## 作业空间治理

日更先估算完整母版、合成暂存与输出总预算，再传给制作入口。以下示例预算为 2 GiB，按本期实际估算填写。

```powershell
python scripts/render.py <project.json> --output <root>/jobs/2026-11-27/<episode>/output --min-free-bytes 2147483648
```

规范作业目录默认记录渲染前实际可用空间，历史非规范路径继续兼容。运行期间持有作业同级的 `.<episode-id>.media-production.lock`。中断遗留锁时，先核实原进程、渲染子进程及其他写入者均已退出，再恢复。使用独立合成入口时包裹 `render_storage(project, output, min_free_bytes)`，共享同一作业锁和预检回执。

交付后检查引用、在写状态、可再生性和许可。只为确认无引用且可由原工程与固定运行环境再生的 Remotion Webpack pack 提供其作业内相对路径。先预览，再使用新回执路径加 `--apply`。命令核对日期层级、文件类型、链接和共享作业锁，记录每项删除或跳过原因、文件字节数和卷余量变化。受保护项包括浏览器缓存、模型、冻结声、源、母版、正式片、回执、许可与其他在用作业。旧作业完整退役使用 [Remove-RetiredMediaJobs.ps1](../scripts/Remove-RetiredMediaJobs.ps1)，由主执行者逐一确认迁移和引用，再显式传入退役名单。

```powershell
python scripts/media_storage.py --job '<root>/jobs/2026-11-27/<episode>' `
  --pack 'output/remotion/node_modules/.cache/webpack/remotion-production-4.0.542/0123456789abcdef/0.pack' `
  --reason '已核对无引用、写入者已退出、原项目可重建' --receipt '<job>/storage-preview.json'
```

首次核对输出路径、暂存和输入，成片交付后在进度回执登记保留或跳过原因。完整作业清理继续沿用旧作业验证门槛。
