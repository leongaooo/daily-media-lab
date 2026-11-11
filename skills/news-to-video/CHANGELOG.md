## 2026-11-11 — 唯一Remotion Editorial方案

用户明确要求删除其他方案。移除退休渲染器及其布局/人物层/镜头脚本、说明和入口，默认无参数调用即为Editorial；旧布局配置在音频前停止，须另存迁移副本。保留生图、唯一B声、音乐、SVG准备与一期一片规则。以下历史记录仅描述当时状态，不再代表当前可用方案。

## 2026-11-11 — Editorial 底部字幕轨

Remotion Editorial 默认保留 y=904..1080 的固定底部字幕区域，素材和镜头内容在其上方自由布局；字幕按实测语义时间线替换，仍可显式关闭并独立交付 SRT。
## 2026-11-11 — Remotion Editorial 画面模式

新增完全独立于旧版式的文稿驱动横屏画面引擎。Remotion 只渲染代码生成的编辑式镜头和可选本地图片，现有 B 声、音乐、生图、SRT、语义时间线和 FFmpeg 合成继续复用。支持 hero、flow、chart 三种镜头；旧 Pillow 与 HyperFrames 项目不迁移，默认行为不变。

## 2026-11-11 — 可选 HyperFrames 画面

接入本地网页画面引擎，共用原有生图素材、B 声、音乐、语义时间线和 FFmpeg 合成。支持图像缓推、按语义片段点亮原创 SVG、数据条展开。默认保留 Pillow；用 MoE/SSD 三幕对照样片验证画面和音轨。技能触发和生命周期无变化。

## 2026-11-04 — Windows B-backend load compatibility

Full-project execution exposed a native access violation in direct CUDA safetensors storage slicing. Load the same pinned weights on CPU, then move both the main model and speech tokenizer to CUDA and update their wrapper devices. Reference, generation parameters and the sole B voice remain unchanged. Bound long-script generation to eight clips per isolated process, release per-clip allocations and resume completed caches after failures; added a behavioral regression for batching and reuse. Reused the DORA visual assets for a complete new narration/timeline render and included the used free music plus publication attribution in the project delivery.

## 2026-11-04 — Sole approved B voice and zero-budget music

User selected the separated-reference B male voice as the only enabled default and retired previous narration. Replaced the Kokoro execution/setup/check paths with a separate, pinned local Qwen backend, private reference hash policy, isolated cache identity and explicit old-project migration. Added five official Kevin MacLeod CC BY 4.0 tracks, provenance/checksums, stereo voice-first mixing and publishable attribution. Missing voice/reference/weights/music license fails without fallback. Synchronized templates, runtime docs, routing default and regression specifications; experimental/on-demand scope unchanged.

## 2026-11-02 — Existing-script execution

Added an existing-script entry and references/script-handoff.md: preserve narration and scene order, map scene/segment/asset/source identities, merge negative instructions into the actual generation prompt, generate each unique asset once and bind reuse paths, respect script visual choices with scoring override reasons, and audit measured timing and script consistency. Added agent-authored script-map.json and script-execution-report.md handoffs; neither is claimed as automatic renderer output. Documented missing-image fallback as an incomplete script execution. No renderer/API protocol changes; existing creation and music-only workflows retained. Routing and regression cases updated; lifecycle remains experimental/on-demand.

## 2026-10-31 — Visual choice accountability

Added editorial scoring reference and offline auditor; versioned new projects run preflight before generation/voice. Compare image and non-image alternatives; support image+diagram; facts/source/layout/execution gates outrank score. Existing music-only projects remain compatible. Added four prompt regressions and eight executable tests. 34 local tests pass; no audience efficacy claim.
## 2026-11-03 — Local image connection discovery

Recorded the verified external image-demo connection/credentials paths in generated-images.md and linked the lookup step from SKILL.md. Check existing paths before asking the user again; keep secrets outside skill and deliverables. Narrow user-requested documentation correction; no trigger, routing, lifecycle or renderer change. Validation: local configuration files located; image API execution tracked separately in the current production report.

## 2026-11-04 — B narration playback at 1.25

User requested +0.25 from native 1.0. Default playback is now 1.25 through pitch-preserving FFmpeg atempo; native B synthesis caches, reference, model and sampling remain unchanged. Tempo caches isolate source bytes and speed, and captions use processed clip lengths. Music stays at original speed. Explicit 1.0 reproduces native playback. Updated renderer, migration, examples, routing and behavioral tests; skill scope and lifecycle unchanged.


## 2026-11-04 — Default B playback revised to 1.15

User revised the default to 1.15 and explicitly excluded changes to the existing video. Updated the sole-B default, example, routing and regression expectations; export a dry audition only. Existing project, MP4, captions and ZIP stay unchanged.

## 2026-11-04 — Approved audible music bed

User accepted the audition: default music relative -16dB, extra duck 2dB; detect actual PCM activity at 20ms/-36dBFS with existing hold/smoothing. Explicit project levels remain respected. Synchronized examples/docs/evals and tested release during silence. Noise cleanup is an audition-only candidate, not an approved B voice processing default. Existing video/archive remain unchanged.

## 2026-11-04 — Skill-local image API configuration

User requested removing the image-generation dependency on the temporary Codex image-demo directory. Copied the verified Images API connection and separate local credential into `config/image-generation/`; updated canonical discovery and CLI examples. The old directory is historical only. Credentials remain excluded from generated assets, reports, delivered projects and shared skill archives. No API, rendering, voice or lifecycle behavior change.

## 2026-11-05 — Approved mild B denoise enabled

User adopted the audition. Enable fixed afftdn nr8/nf-35/tn0/gs6 after tempo, with 600-sample delay compensation, exact length, active-RMS matching and peak guard. Preserve raw synthesis/reference identity, isolate cleanup caches and report actual cleanup in validation. Sole B default1.15 and approved music -16/2 remain. Existing deliverables are not regenerated.
