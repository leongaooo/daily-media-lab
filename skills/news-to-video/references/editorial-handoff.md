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

```powershell
python scripts/episode.py validate-package package.json
python scripts/episode.py init episode.json --episode-id issue-20261120 --request "近期IDC资讯成片" --package package.json
python scripts/episode.py draft episode.json --revision 1 --paragraphs paragraphs.json --output draft.json
python scripts/episode.py stage episode.json --revision 2 --name editorial_locked --output draft.json --evidence "事实、归属、段落映射已逐项审查"
python scripts/episode.py verify episode.json
```

已有确认稿件用 `init --confirmed-script confirmed.md`，该输入即受身份保护。内部新稿用 `draft` 反复编辑，直至 `editorial_locked`；之后不能覆盖锁定稿。`draft` 只可创建新文件或覆盖本节目的未锁定草案，不能覆盖源证据、旧稿、节目清单或任意已有文件。不是任意Markdown自动导入器。

清单含 `schema_version,episode_id,revision,request,packages,stage_receipts,delivery_receipts,adoption_receipts,failure_receipts`。写入要求当前 `--revision`，邻接 `.lock` 通过独占创建阻止竞争写者；锁不按超时自动删除，遗留锁先核验PID与实际写者已停止。原子替换使用同目录临时文件。并行采编只返回资料，由主执行者单写清单和台账。

阶段依赖：证据就绪 → 稿件锁定；稿件锁定后声音和视觉可并行；两者完成后正式预演；再到母版、合成、复核。对应 stage 名为 `evidence_ready`（init生成）、`editorial_locked`、`audio_locked`、`visual_ready`、`animatic_reviewed`、`masters_ready`、`composed`、`reviewed`。阶段记录 `--input/--output` 的真实内容哈希及 `--evidence`；输出不能是零字节占位。音频和视觉的具体格式由执行契约负责。记录证据时分别注明技术解码、实际连续观看、试听和用户认可，不以一句“通过”代替未完成层。

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
