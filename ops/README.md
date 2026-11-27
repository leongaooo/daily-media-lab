# OPS-01 · 生产预检、恢复与可搬迁源包

`ops/` 是仓库级生产工程化入口，不是第二套媒体渲染器。它复用 `skills/news-to-video/scripts` 的节目、音频和镜头校验器，负责在重型任务前暴露路径、磁盘、缓存、回执和包边界问题。

## 入口

从仓库根目录执行。路径全部替换为实际环境；`runtime.local.json` 只放仓库外。

```powershell
$renderPython = 'C:/Users/xc_sc/.cache/news-to-video/env/Scripts/python.exe'
$job = 'E:/CodexMedia/jobs/2026-11-20/prod-01-webb'
$cache = 'E:/CodexMedia/cache'

& $renderPython ops/preflight.py `
  --job $job `
  --runtime "$job/runtime.local.json" `
  --blender E:/blender.exe `
  --cache $cache `
  --report "$job/ops-preflight.json"

& $renderPython ops/cache_audit.py `
  --root $job --root $cache `
  --report "$job/cache-audit.json"

& $renderPython ops/recovery_drill.py `
  --job $job --report "$job/recovery-drill.json"

& $renderPython ops/portable_package.py `
  --job $job `
  --output 'E:/CodexMedia/jobs/2026-11-21/ops-01/prod-01-webb-source.zip'
```

预检是只读的：它不会下载模型、启动TTS、渲染帧或删除缓存。`cache_audit.py` 只报告可再生目录和重复哈希；`recovery_drill.py` 只在内存回执副本中删除一项，验证“缺回执被拒绝、恢复原回执后通过”。实际断电续渲仍需 Blender 进程和真实失败现场。

默认源包包含 `project.json`、`shots.json`、相对 `.blend`、冻结音频／cue、来源／许可、设计源和审计元数据，不包含 runtime、权重、字体、Key、缓存、Remotion bundle、日志或 PNG 序列。加 `--include-media` 才会把 output 与预演媒体加入包；它仍不会加入 `frames/` 母版序列。源包可在另一台机器上作为输入，但“包可解压”不等于新机安装、GPU、声音试听或用户认可通过。

## 公开复现与边界

`examples/three-media-minimal` 是合法的结构／编排输入，包含合成证据和显式公开声音 ID；它默认不联网、不TTS、不Blender、不生成媒体。`examples/blender-calibration` 与 `examples/joint-directing-minimal` 是无私人素材的技术源例，运行产物放 `outputs/` 或仓库外。OPS-01 不把这些样例升级为真实新闻、完整 Web3 成片或新机验收。

当前机器可执行的证据应分别记录：仓库回归、预检、缓存审计、恢复演练、源包哈希、完整合成、连续观看、试听、新机和远程发布。任何一层失败或未做都保留在 progress，不用“ZIP能打开”替代完整复现。

仓库的 `.github/workflows/python-tests.yml` 只安装渲染侧 requirements，不下载 Qwen、模型、GPU 运行时、Remotion 或生图服务；它运行媒体契约测试和 `ops/test_ops.py`。CI 通过只证明无 GPU 的自动回归层，不证明完整视频制作、浏览器观看或新机复现。
