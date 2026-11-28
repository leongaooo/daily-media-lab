# 当前交接

更新：2026-11-21（Asia/Shanghai）。先读AGENTS和ROADMAP；任务状态仅在ROADMAP维护。

## 当前焦点

PROD-01 已由会话 `01a1f934-d7a6-7220-961c-5ab5fcae26d1` 实际制作并交付新一期《十八面镜子，一束星光》，主题为韦布望远镜2022年分段镜校准，采用“现象—误判—相位—全仪器边界”结构。完整命令、来源、设计、预演、整片、返修与限制见[本期进度](progress/2026-11-20-prod-01-webb.md)。没有用旧IDC／cavern片或REP-09阶段认可替代本片验收。

本地权威作业根：`<MEDIA_WORK_ROOT>/jobs/2026-11-20/prod-01-webb/`。

- 完整成片：`output/video.mp4`，59.833333秒／1436帧，1920×1080／24fps；SHA256 `d139cc71fc834b8e2c47712f867ef8f4af97f83305fb42fe14639d9018f3c3c9`。
- 字幕与声音：`output/captions.srt`、`audio/voice.wav`、`output/mix.wav`；10条连续实测语义cue，公开qwen-uncle-fu-v1冻结干声，无私人参考、音乐或模拟现场声。最终合成不再TTS／变速／降噪／重拼。
- 可编辑交付：`prod-01-webb-editable.zip`，63文件／14,044,602字节，SHA256 `39355d170206fb8d1728a72ea82a6afe1d2bed6697f9ebda5153ec0c7b3de470`。包含两个真实blend、原创字卡／作者脚本、来源／许可、事件／镜头／音频身份、主片与预演。包内逐文件SHA已核对，不含runtime、权重、字体、Key、网页影像或私人声音；完整PNG及原始HTML留job。
- 证据：`quality-review.json`、`technical-review.json`、`artifact-manifest.json`、`phase-repair-provenance.json`、`source-dependency-review.json`；原母版及失败／恢复日志保留。NASA三份一手页面URL、HTML及哈希在sources；本片只用原创示意，不冒充实测光路、整星复原或2026新闻。

## 必须保留的验收边界

实际完成：正式render.py与独立verify.py完整解码、1436帧及10条字幕连续、输出干声字节保持、双声道PCM等于单声道干声复制、峰值0.779968、123项公开回归；Chrome从头1.0／unmuted播放至59.833333、关键状态与相位段定点复核。15张编码后抽帧另用于排版，不称持续观看。

尚无本片持续人眼观看、人耳读音／耳机／普通扬声器试听、手机实机或用户认可证据；不能从ended、未静音或抽帧外推。390px竖屏内嵌字幕偏小，不判通过；844px桌面横放模拟字形可辨，仍不是手机实机。建议实际手机全屏横放并核对SRT／声音；收到设备、时间点及听感反馈后，在当前job返修对应层，再收口唯一任务表。没有新机或远程发布证据。

相位段曾因顶点线性混合在中态缩小波幅，已改为定幅波列平移，仅重渲156帧。其余1280帧先与原1436帧回执逐项SHA匹配，再按原源／参数技术重新登记；两个源和原回执保留，不将原帧伪称新源生成。恢复采用shots.json三段清单，不能只打开旧源的失败相位段判定正式片。

## 前序与后续边界

PUB-07沿用[发布收尾](progress/2026-11-20-open-source-publication.md)：发布载荷 `dc412bf087e1f67a5da32addb553a09495f4b5d2`、收口 `6be44db792ae8c9d7e190f7ffb714979b6b07fdc2`，当时origin/main与GitHub入口已核验。本轮没有重新提交／推送、改远程历史或新增发布。

REP-09用户阶段验收与旧负反馈均保留，见[阶段记录](progress/2026-11-20-joint-directing-v3.md)；旧根为 `<MEDIA_WORK_ROOT>/jobs/2026-11-20/joint-directing-v3/`。旧C junction不变，新作业／暂存在E盘。前序阶段认可不扩展到本片或跨设备声音。

OPS-01 已由会话 `01a1f934-d7a6-7220-961c-5ab5fcae26d1` 实际推进并进入待验证：`ops/` 预检、缓存审计、回执恢复演练、相对源包、公开最小示例、同机 clean venv 和无GPU CI入口已落地并实跑。详细命令和回执见[OPS-01进度](progress/2026-11-21-ops-01.md)。REP-02／REP-02-01第二台Windows/NVIDIA机器、REP-03完整真实Web3示例、REP-04远程CI回执与远程发布仍按各自证据单独记录，不能由本机结果外推。

当前可复核产物：PROD-01 `ops-preflight-final.json` 为 pass；`ops-cache-audit.json` 扫描5288文件并登记1681组重复SHA；`ops-recovery-drill.json` 的 baseline／拒绝／恢复均通过；可搬迁源包位于 `<MEDIA_WORK_ROOT>/jobs/2026-11-21/ops-01/prod-01-webb-source.zip`，46项、SHA256 `84861087318c2f6c78469f538f90151e92a268166d9638fb785fc357e652345d`；同机clean venv记录在 `clean-env-reproduction.json`。这些文件都在E盘作业区，不进入Git。

三个媒体技能本体本轮零修改，未触发维护同步；PUB-07答复没有作为永久授权。未来首次技能写入前仍按media-maintenance询问本批同步选择。私人声音、Key、runtime、模型、客户资料及未授权素材继续不进Git。

本任务本地审片服务已停止，18766无监听，无制作子进程残留。job/tmp、__pycache__及自动blend1备份的清理被自动审批拒绝（仅返回blocked by policy），故保留；未换方式删除，不影响正式视频或工程包。


## 精炼成果固化接续（2026-11-21）

用户明确不继续制作整片，要求落实其余精炼成果并同步推送远端。EXP-05落实字段映射、空内容防护、全部检查项真实显示、独立对照标签、冻结原声审查窗口及项目级资源参数；canonical146/public151项回归通过。技能入口为[精炼与复用](../skills/news-to-video/references/refinement-workflow.md)，证据见[本批progress](progress/2026-11-21-refinement-consolidation.md)。

本次不包含新媒体、有声样片、私人声音、源PDF或新机／设备试听证明。用户一般赞许只认可对应短段方向，技术、连续观看、人耳及用户反馈分开；未来不得把本轮授权解释为继续整片制作。其他PROD-01／OPS-01工作和已有未提交改动继续保留；本条不改变它们的原验收状态。

## 对象状态叙事接续（2026-11-25）

已将独立新闻场景、对象前后态、最终口播短段、实际画面和声音消费者接入 [news-to-video](../skills/news-to-video/SKILL.md)。公开复验入口见[合成示例](../skills/news-to-video/assets/object-state-preview/README.md)，当期证据见[本次进度](progress/2026-11-25-object-state-narrative.md)。下一轮研究先复核当前范围，再以具体验证方法对比可选价值目标及同方向产品。

## 稳定日更门槛接续（2026-11-26）

稳定日更门槛已接入本机 `news-to-video` 的 `stability_gate_version: 1` 入口和回执校验。历史 `legacy`、旧 `daily-v1`、简单图解与独立 Blender narrative 继续兼容。今日 IDC 独立复做目录为 `<MEDIA_WORK_ROOT>/jobs/2026-11-26/idc-20261126-stability-gate/`，新版视频、字幕、预演回执、整期复核、验证报告和稳定门槛清单已绑定新的哈希。稳定结论是 `deferred`，技术解码、实际画面和连续声画通过，持续人工观看、人工试听、手机、耳机、普通扬声器、观众复述、跨机复现和本片用户认可没有证据，不能登记稳定日更通过。

Blackbird 同画面对照在整期复渲后补齐。下次涉及主体动作、路径或状态变化时，把静音去口播字幕版和同画面冻结口播版前置到整期合成之前。具体文件与跨期验证范围见[验收记录](progress/2026-11-26-idc-daily-acceptance.md#2026-11-26--稳定日更门槛与独立作业复做)。

维护者已指定 `Westgate-Traffic-Silent.mp4` 为最新视觉成果标准。旧 IDC 信息卡版保留为历史交付，当前三维返修作业根为 `<MEDIA_WORK_ROOT>/jobs/2026-11-26/idc-westgate-standard/`。先查看整期静音版的主体、方位、触发、动作与结果，再核查同一画面流的冻结原声版。文件身份、抽帧观察和剩余验收范围见[返修记录](progress/2026-11-26-idc-daily-acceptance.md#westgate-视觉基准与-idc-返修)。

## Daily Media Lab 下一阶段日更入口（2026-11-27）

日更编辑计划已接入 `news-to-video`。下一期先用
`skills/news-to-video/scripts/daily_editorial.py validate-plan` 检查观众问题、
观众收获、切入点、表达方式、交付标题、可选互动和价值意图，再用
`episode.py init --editorial-plan` 绑定计划文件。当前演练使用真实卡亚尼证据包，
但没有把演练清单当作交付或采用。

- 计划契约：[日更编辑工作流](../skills/news-to-video/references/daily-editorial-workflow.md)
- 结构入口：`skills/news-to-video/scripts/daily_editorial.py`
- 11 月 28 日演练证据：见当期实施核验
- 当前公开里程碑：[实施核验](progress/2026-11-27-daily-editorial-next-phase.md)

方向建议进入独立方向板，由人工记录 `accepted`、`revise_after_evidence` 或
`parked` 的理由。私人抖音导出和评论只有在用户明确发起“复盘”后读取。正式发布仍由维护者控制。

## EXP-08 · 统一制作基线

新一期通过 `production.py new` 自动读取已启用的 2026.11.28-1。已有节目通过 `production.py revalidate` 使用原期编辑计划和证据，在新路径生成复验版。公开配音沿用已授权的叔傅音色。验证和独立机器复现情况见[本批记录](progress/2026-11-28-unified-production-baseline.md)。
