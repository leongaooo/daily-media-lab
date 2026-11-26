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

### 目录和清理时点

本机 `news-to-video` 管理 `E:/CodexMedia/jobs/YYYY-MM-DD/<episode>/`、`E:/CodexMedia/cache/` 及明确归属于某一作业的临时目录。公开环境使用自己的媒体根。根内其他应用的 archive、session、visualization 目录由各自管理。

### 素材与母版的生产设计

通用粗场景和临时布景用可编辑 SVG、React/SVG 或小型生成脚本，按期构图并渲染。预估磁盘时分开计算真正需要 Blender 母版的镜头、合成副本和编码输出。已过技术检查的精细素材只维护一份可编辑源及必要依赖，按 [素材索引](../assets/illustration-kit/asset-manifest.json)保留版权、用途和哈希。只在受核验的语义边界内复用。

可编辑工程、来源和许可、冻结口播与 cue、正式交付、必要的审阅证据长期保留。新的可重建三维镜头可在开工时标记拟退役帧范围，先在独立位置按相同源、依赖、Blender 版本和渲染参数重建，按原有逐帧回执核对像素身份、帧号和引用，再逐帧退役。没有可用替代或重建证据的原始母版继续保留。从正常入口可按源重新生成的 SVG 或 React/SVG 场景无需落整套 Blender 母版。

### 保留与回收

| 目录 | 内容及回收边界 |
| --- | --- |
| `output/`、`release/` | 正式 MP4、SRT、回执、哈希及可再生的合成暂存。正式交付身份通过回执核对。 |
| `frames/`、`composition/` | 生产母版、合成中间轨和试编码。用于当前复做的母版及硬链接来源继续保护。 |
| `preview/`、`review/` | 短段、代表帧和审核证据。确认无用途且可重建的预演暂存可回收。 |
| `audio/` | 冻结口播、cue、音频身份及试音缓存。冻结母带与已核准 cue 是恢复输入。 |
| `source/`、`sources/` | Blender、组件、来源、配置和许可。保留仍引用或缺少替代的唯一来源。 |
| `cache/`、`tmp/` | 作业内可再生缓存及明确归属的临时文件。浏览器配置、模型、依赖运行时分别核对，活动锁和链接保留。 |
| 媒体根 `cache/` | 新的可再生跨作业缓存按 `cache/YYYY-MM-DD/<owner>/` 记录归属。未建立日期和归属的旧缓存先保留。 |
| `E:/CodexMedia/governance/YYYY-MM-DD` | 盘点、删除和保留回执。放在 `jobs`、`cache` 之外，不参与媒体作业删除。 |

受管 Blender 合成经 `render.py` 完整解码并写入验证记录后，仍持有作业锁时逐张匹配并回收 `remotion/public/narrative` 内的独立合成副本，并写入 `storage-stage-cleanup-*.json`。直接在 Remotion Studio 使用暂存时运行 `--keep-narrative-stage`。用原工程重跑该命令可重建暂存。硬链接、身份变化和证据不全的文件按回执保留。Blender 和 Remotion 的受管入口共用同一作业锁。

旧版采用同一封存契约、且已有带 SHA‑256 的正式视频验证文件时，用以下命令预览。复核后改用新回执路径并加 `--apply`。

```powershell
python scripts/media_storage.py --job '<dated-job>' --stage-output '<output>' --project '<project.json>' --receipt '<review.json>' --reason 'Recoverable staging with sealed masters and decoded delivery'
```

**交付后立即执行。** 正式片完成技术校验并保存回执后，盘点作业临时目录。确认可复做、无在写、无引用的暂存按精确路径清理。Remotion Webpack pack 通过 `media_storage.py` 先预览再执行。把处理项、恢复入口、磁盘余量和跳过原因写入作业树之外的持久回执。同日作业的正式媒体和生产依赖可供接续。

**次日开工时执行。** 先盘点前一天及更早的受管内容，包括 MP4、帧、暂存和素材。确认归属与引用后，为每个候选写相对媒体根的 `path`、`action`（`remove` 或 `retain`）和 `reason`。当前或未来日期、无法确认归属的目录、活动作业、锁、链接与当前制作所需的唯一依赖保留。受管根的 `governance/active-media-inputs.json` 沿用同一清单格式，只登记仍在使用的 `retain` 项。它优先于旧审查中的 `remove` 决定。确定替代位置和恢复身份后再更新这份现用清单。若对仍在引用的文件取得替代版本，先核对新位置、哈希、回执和恢复入口，再重新审查旧路径。

```powershell
python scripts/cross_day_storage.py --root '<media-root>' --as-of 2026-11-27 --review '<review.json>' --receipt '<dry-run.json>'
python scripts/cross_day_storage.py --root '<media-root>' --as-of 2026-11-27 --review '<review.json>' --receipt '<apply.json>' --apply
```

两次均使用当天北京时间日期和互不覆盖的回执，先查看 `eligible`、`retained`、`skipped` 及实际删除路径。文件大小之和和卷余量差均写回执。工具只枚举媒体根内 `jobs` 与 `cache`，跨日删除仅处理经过确认的日期目录下作业或缓存子目录。其他作业专用临时目录逐项核对归属与恢复入口后，纳入对应作业清理记录。

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

首次核对输出路径、暂存和输入，成片交付后在进度回执登记保留或跳过原因。每日开工的整作业清理按本页跨日入口执行。既有发布收尾仍可按已核对的新成片回执复核退役名单。
