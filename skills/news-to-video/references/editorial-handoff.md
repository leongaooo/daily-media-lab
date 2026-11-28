# 领域编辑包与节目编排 v1

适用于以 `news-to-video` 要求近期 IDC／Web3 资讯成片的任务。领域技能只负责采编包，不递归启动制作；主执行者继续完成节目。独立领域调用仍交付剧本／明确文字版。显式仅文字、剧本、计划或图片的范围优先；流程讨论与引用示例不执行媒体步骤。

## 编辑包

可执行结构例见 [editorial-package-example.json](../assets/editorial-package-example.json)，其中资料是合成测试，不是新闻。`scripts/episode.py validate-package package.json` 只检验结构、唯一身份和引用，不能证明新闻真实、近期或原文已读。

- 根：`schema_version:1`、`package_id`、`domain:idc|web3`、`coverage:{start,end,timezone,limitations}`、`news`。
- 新闻：`news_id`、`title`、`topic_key`、`canonical_url`、`delta`、`claims`、`evidence`、`paragraphs`、`limitations`、`material_constraints`。可加 `project`、`version`、`category`。
- 证据：`evidence_id,url,publisher,published_at,event_date,readable_excerpt,source_type`。原始日期与事件日期分开，未知明确 `null`；摘录短而可核对，完整必要事实以自己的话概括，遵守引用限制。source_type 保留维护方／厂商、运营者、规范或独立分析等归属。
- 主张：`claim_id,text,evidence_ids`。段落：`paragraph_id,text,claim_ids`，必要时另加 `spoken` 说明读法，含义保持一致。
- 所有新闻、证据、主张和段落ID在包内唯一；混合节目不同包的新闻／主张／证据／段落ID、package_id、topic_key及canonical_url也不得重复；不假定上游总会加领域前缀。同一跨领域事件合并为一个新闻并记录两侧证据，不能重复计数。

领域包中的口播是可编辑草案。主执行者可以在音频冻结前调整节目角度、语序和节奏；改动事实与判断时回到具体证据。新段落必须保留 claim_ids，制作镜头以 news_id/paragraph_id/claim_id 回查。不要让领域包机械填满对象舞台槽、逐shot前后态或每幕生图提示词。

已有确认稿件直接接入并保留快照与内容身份，不重选整期新闻、不为视觉改稿；有来源缺口时只补核关键事实，不能直接标“已核验”。确认最终音频遵循 [Blender与最终音频交接](blender-handoff.md)，不调用新配音路径。

## 节目清单与CLI

`episode.py` 是本地收据与写入工具，不是自动网页采编器或自动导演。技能执行者使用当前网页工具采编、进行事实审查和创作，再调用工具记录真正完成的阶段。相对CLI文件参数按当前工作目录解析，存入清单的文件路径解析为绝对路径。

日更在建立节目清单前先按 [日更编辑工作流](daily-editorial-workflow.md) 形成编辑计划。计划绑定观众问题、观众收获、探索切入点、表达方式、交付标题、可选互动、价值意图和手动复盘边界。`episode.py init --editorial-plan` 会保存计划文件身份，`verify` 会在计划变化时停止恢复。

```powershell
python scripts/episode.py validate-package package.json
python scripts/daily_editorial.py validate-plan editorial-plan.json
python scripts/episode.py init episode.json --episode-id issue-20261120 --request "近期IDC资讯成片" --package package.json --editorial-plan editorial-plan.json
python scripts/episode.py draft episode.json --revision 1 --paragraphs paragraphs.json --output draft.json
python scripts/episode.py stage episode.json --revision 2 --name editorial_locked --output draft.json --evidence "事实、归属、段落映射已逐项审查"
python scripts/episode.py verify episode.json
```

已有确认稿件用 `init --confirmed-script confirmed.md`，该输入即受身份保护。内部新稿用 `draft` 反复编辑，直至 `editorial_locked`；之后不能覆盖锁定稿。`draft` 只可创建新文件或覆盖本节目的未锁定草案，不能覆盖源证据、旧稿、节目清单或任意已有文件。不是任意Markdown自动导入器。

清单含 `schema_version,episode_id,revision,request,packages,editorial_plan,stage_receipts,delivery_receipts,adoption_receipts,failure_receipts`。`editorial_plan` 是可选的日更编辑层输入，写入节目清单时保存 `{path,sha256,bytes}`，不把标题或互动文案当成自动发布命令。写入要求当前 `--revision`，邻接 `.lock` 通过独占创建阻止竞争写者；锁不按超时自动删除，遗留锁先核验PID与实际写者已停止。原子替换使用同目录临时文件。并行采编只返回资料，由主执行者单写清单和台账。

用户对关键幕审片版本的放行记录在本期审片记录中。正式制作阶段按证据就绪 → 稿件锁定 → 声音与视觉并行 → 有声技术预演 → 母版、合成、复核推进。对应 stage 名为 `evidence_ready`（init生成）、`editorial_locked`、`audio_locked`、`visual_ready`、`animatic_reviewed`、`masters_ready`、`composed`、`reviewed`。阶段记录 `--input/--output` 的真实内容哈希及 `--evidence`；输出不能是零字节占位。音频和视觉的具体格式由执行契约负责。记录证据时分别注明技术解码、实际连续观看、试听和用户认可，不以一句“通过”代替未完成层。

相同阶段、相同收据重试幂等；不同身份不能覆盖完成阶段。`verify` 复核已登记证据、确认稿和阶段产物的内容身份。上游改变时停止复用；若确需有授权的改稿或新音频，另建关联的节目修订目录，不偷偷解除旧锁。失败时继续同一节目及有效缓存，不重复检索、配音或因台账去重拒绝自己的恢复。用 `episode.py fail episode.json --revision N --name composed --reason "真实失败原因" --resume-from "明确恢复位置"` 记录可恢复失败；可加--input捕获当时输入。失败回执是历史证据，不推进成功阶段，也不将历史失败输入当作当前成功依赖。

## 实际交付与采用恢复

内部草案、冻结音频和成功渲染都不是用户交付。实际给用户提供文件后，记录带时区的时间、真实目的地和交付证据：

```powershell
python scripts/episode.py deliver episode.json --revision 9 --kind video --artifact delivery/video.mp4 --to "当前用户聊天" --at "2026-11-20T18:00:00+08:00" --evidence "实际交付消息或应用附件引用"
python scripts/episode.py adopt episode.json --revision 10 --domain idc --ledger ../../news/idc-compute-weekly-ledger.md --delivery-id ACTUAL_DELIVERY_ID
```

命令只是格式示例，revision与delivery-id以实际回执为准。reviewed阶段必须通过--input登记实际检查过的合成文件内容身份，空输入或任意无关文件被拒绝。video交付要求文件同时属于composed.outputs和reviewed.inputs，复核A不能授权交付B；text/script属于稿件锁定输出。工具记录执行者声明的真实交付证据，不具备自动观察用户是否已收到文件的能力。

两领域分别沿用现有台账。IDC不迁移历史表头，交付关联写入 Why Included；Web3写入交付状态／文件。通过topic_key关联已有事件，剧本改编视频补充同一行的交付，不制造新新闻；实质新进展使用新的事件身份与delta。写入含稳定adoption标记，产物先落地、台账后提交、清单最后记回执；台账落盘后回执失败时，重试识别标记补回执，不重复追加。可用 `--ledger-sha256` 做预期内容冲突检查；冲突后重读再试。

混合节目逐领域提交，保留独立回执；一个完成而另一个失败时只补失败侧，不宣称两个Markdown具有原子事务，不为补台账重渲染。恢复采用时先重读当前清单revision与台账。Web3 tracker仍记录项目原生状态，按采用证据或用户专题核验更新；不把渲染失败写成项目状态倒退。工具不自动改tracker或归档历史，执行者按领域规范处理，不能清空使用者记录。

## 关键幕集中审片

整期精修前，技能主导节目内容，按脚本节奏和预计时长编排关键幕。无正式配音时直接交付静音粗动态，必要的画内标注照常保留。用户集中审核关键视觉呈现，按自己方便的时间提出问题和下达制作指令。

1. **把所有关键幕放进同一个板块。** 按成片顺序提供可连播的关键幕预演，并用稳定幕号和连播时间点定位。选入决定理解或主要视觉效果的幕，例如因果、方向、空间归属、动作转折、数据与对象绑定。普通过场由制作侧检查，关键幕缺少过场就无法判断时保留所需上下文。
2. **每幕提供标注构图图和真实粗动态。** 图上标主体、次要元素、位置与标注归属。动态呈现前态、触发、响应、结果和停留，配一句观众预期可推断的关系或行动。影响判断的色彩、二维层级、三维质感、动效或镜头节奏，在该幕先做到接近成片。其余部分可保留粗排。若已有冻结口播，可原样复用辅助计时，用户审片范围仍为视觉。
3. **把反馈落到具体版本和幕。** 板块顶部给出审片版本、连播入口和逐幕定位。用户可在同一会话陆续提问题，也可发总评。记录原话、受影响幕号、共享问题及处理结果，并将确认绑定所见版本和范围。批注、沉默及技术检查都不能推定放行。
4. **按用户的指令接续制作。** 用户针对当前板块说「通过」或明确下达制作指令后，直接在获准范围内并行启动视觉精修与新配音。已有冻结口播直接复用并保护源文件。配音、听感和声画同步由技能自验。用户只放行部分幕或仍要求修改时，按其指令推进已授权范围，未放行的关键幕继续修改。整期配音随整期制作放行启动，明确范围另有指令时按指令执行。返修后若关键关系、观众可能推断或主要视觉效果实质改变，只提交有影响的幕复看；常规制作收尾由技能复核。新的明确指令优先。

可直接使用的板块结构：

> **关键幕集中审片 · [节目／版本]**
>
> [连播预演，注明静音或声音来源]
>
> **[幕号] [标题] · [连播时间]**
>
> [标注构图图] · [逐幕短预演]
>
> [一句话说明这一幕希望观众看清的关系或动作结果]

将实际送审板块、媒体版本、反馈原话和放行范围留在本期审片记录中。放行后待口播和视觉均就绪，使用实测 cue 收敛镜头、动作、字幕和尾音，再登记下文 `animatic_reviewed` 技术回执。

## 日更成片回执

新节目由 `episode.py init` 默认启用 `daily-v1`。在正式项目声明 `acceptance_contract: "daily-v1"`、`episode_id`、本期适用的 `baseline_id`、`production_baseline` 文件路径和 `animatic_review_receipt` 路径。先读取基线的实际验收范围，记录本期沿用的做法，按本期内容另作设计。旧清单仍可核验，低层渲染可用于历史重现和预演。新节目正式交付要求审阅绑定到当前正式渲染报告。独立 Blender narrative 继续使用自己的镜头和母版契约，简单图解在正式项目使用时需声明 `visual_contract_version: 1` 及 `simple_diagram_reason`。

1. `animatic_reviewed` 是正式制作阶段的有声技术检查，依赖 `audio_locked` 和 `visual_ready`。先按冻结声样本与完整语义制作代表段。使用 `review_window.py` 取样，保留母版、窗口的独立身份以及句级时间。短片使用 `render.py` 合成有声 MP4。正式入口复核预演项目与整期所选场景，并核验已经冻结的母版和对应 cue。
2. 预演回执使用 `schema_version: 1` 与 `kind: "animatic_review"`。文件身份统一使用 `{path, sha256, bytes}`。记录 `episode_id`、`baseline_id`、`baseline`、`scope.scenes`（整期零起点序号）、`scope.evidence_ids`、`scope.semantic_goal`、`visual_path` 和 `consumer`。关联 `preview`、`project`、`motion_report`、`validation`、`playback` 及 `voice_window.source/window/start_sample/end_sample`。播放器记录写入实际媒体 SHA-256、原速、静音状态、尾帧和连续播放事件。对象舞台观察用生成报告的 `action_id`、三个对应的帧号、PNG 身份和具体可见变化。Blender 使用实际渲染的 `shot_id`。逐项填写 `checks` 与 `limitations`，见 `episode.py` 校验及回归。
3. 记录 `animatic_reviewed` 时，把 MP4 和预演回执登记为输出，以 `--review-receipt` 指向该回执，把基线、预演项目、运动报告、验证报告、播放器记录、母版、窗口和真实消费源码登记为输入。正式合成后，`reviewed` 用同一选项登记 `kind: "delivery_review"` 的回执文件，关联 `episode_id`、由 `composed` 登记并实际检查的 `video`、`captions`、`validation`、逐幕 `scene_reviews` 及 `limitations`。每幕描述所见并附抽帧文件身份。
4. 两类回执分别保留完整解码、画面抽查、连续播放、技能执行的观看与试听，以及实际收到的用户认可范围。核对读音、口播清晰度、混音、声画同步和尾音完整性。用户的集中审片确认按该视觉版本和范围记录。播放器到尾只登记播放证据。资料或消费者变化后重做受影响的预演，已登记产物的内容身份受原阶段校验保护。

### 稳定日更门槛

需要声明稳定日更结论的新项目在项目 JSON 中加入 `stability_gate_version: 1`，并在预演回执中填写 `stability_gate`。门槛按 `technical_decode`、`actual_visual`、`continuous_av`、`manual_viewing`、`manual_listening`、`phone_viewing`、`headphone_listening`、`speaker_listening`、`audience_recall`、`cross_machine` 和 `user_approval` 分层记录。每层只能使用 `passed`、`not_run` 或 `blocked`，通过层必须给出证据引用，未通过层必须给出原因。

`stable_daily`、`status` 与 `blocking_layers` 由这组层级共同决定。播放器 `ended`、抽帧、一次人工认可或单机回放都不能代替缺失层级。早期视觉放行只证明该版关键幕获准制作。稳定日更声明按各层实测记录，日常制作按实际技术回执继续。没有 `stability_gate_version` 的历史 `daily-v1` 项目继续按原回执契约核验。
