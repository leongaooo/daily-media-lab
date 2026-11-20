# 已有剧本：接入、执行与验收

视频总入口受托采编时先接收 [证据编辑包](editorial-handoff.md)，新草案可在音频冻结前内部校订；已有用户确认稿/最终口播保持原身份。已有最终音频按 [Blender交接](blender-handoff.md) 跳过TTS及重拼。下方旧剧本的固定素材/镜头要求只在源稿明确指定或选择旧图解路径时适用；不要求领域采编先填对象槽。

适用于各类资讯主题和已有视频剧本。目标是保留已确定的事实、口播和字幕时间轴，在用户授权范围内创意制作画面。没有剧本的原材料任务仍沿用原流程。

## 1. 输入检查与范围

保留原剧本快照（如 `source-script.md`），不覆盖上游稿件。检查标题、目标、幕号与顺序、逐幕口播、图片/图表需求、素材编号、关键事实及来源。剧本内缺少普通制作参数可按技能默认补齐；关键数字冲突、事实缺口、不可取得的指定真实素材不能猜测。日期是原新闻日期或制作日期时要标明类型。

只请求计划时不读密钥、不请求生图、不启动TTS。只请求图片时止于图片、预览、绑定清单及生成报告。请求完整视频且已授权的素材生成直接执行；接口或预算障碍时说明具体缺口及可执行部分，不用重复确认代替工作。

允许不改变含义的标点、缩写读法和字幕语义拆分。合并、删除、重排原幕，删改口播、改变数字或替换已指定画面均属于偏差，记录理由；超出制作适配而改变主线/判断的改稿需取得用户认可。目标时长容不下原稿时提出具体缩稿或延时方案，不静默删句、过度加速或截断音频。

## 交付基数与板块

每日/每周默认一期一片：一份剧本中的多条新闻、独立主线或章节都映射到同一项目的scenes，保留独立的主题和证据，一次生成连续时间线与一个MP4。不要把文件夹数或新闻标题数当成输出数量。仅用户明确要求拆分时才建立多个项目。用户最新要求合为一期而旧稿写明拆分时，保存原稿快照，并在script-map和执行报告记录此项已授权的包装调整；不因此删改事实或伪造新闻之间的因果。

## 2. 转为现有项目格式

按[项目格式](project-format.md)选择实际路径。Blender叙事使用narrative_version:1和narrative_manifest，镜头源、帧与冻结音频按[Blender交接](blender-handoff.md)执行；不同时套旧visual_contract_version。只有显式选择旧v2图解时才启用director_contract_version:1、visual_contract_version:2与visual_selection_version:2，并按[旧图解执行契约](executable-visuals.md)检查。以下映射由制作代理执行，不存在自动解析任意Markdown剧本的导入器。画幅及安全区以当前下游契约为准；旧稿画幅冲突先明确报告，不沿用旧坐标。

v2对象/动作映射：对象表→object_stage.objects；有证据关系→connections；分组/空间装饰→groups；段落中的前态—动作—后态→actions；原稿段落ID→scene本地segment；实测cue内比例→at/until。图像直接绑定objects[].asset；自动生图需image_generation.role=subject及object_id，保持原asset_id与正负提示词。静态PNG不会自己运动，超出内置能力通过editorial.component_dir接入项目Stage.tsx。完整字段见[对象舞台v2](object-stage-v2.md)。

下表中旧image/background/subject/supporting槽、chart和七类构图字段为v1映射，不能原样塞入v2；共有的口播、来源与映射规则继续使用。

| 剧本内容 | 制作项目/交接记录 |
|---|---|
| 标题、日期类型、视觉方向 | title、date_label、art_direction，勿将长片名直接硬塞短栏目标题 |
| 新闻板块、幕号与顺序 | 同一新闻的分幕默认合入一个scene，多个叙事节拍由shots承接；原始news_id/幕号/段落ID保存在script-map.json，scene_index从0开始 |
| 章节、屏幕短标题 | chapter、headline |
| 口播与读法 | segments[].text / spoken；一幕可对应多个自然语义片段，顺序不变 |
| 主构图、景别、环境和留白 | composition及shot覆盖、camera_language；visual_direction/background_direction保留依据但不能代替实际字段 |
| 共享世界与主题 | story_world的id、setting、objects、关系边界、连续性与palette；场景palette可覆盖继承值 |
| 连续镜头及口播段落ID | v2每条新闻1—8个shots，镜头内可有多个对象动作，段落ID转换为本scene的segment_start/segment_end，覆盖全部片段且无重叠；实测cue决定start/end |
| 原图需求正/负提示词 | image_prompt、negative_prompt保留原文；实际请求使用合并后的image_generation.prompt |
| 环境背景图 | scene或shot的image_generation.role=background，生成后绑定相应background_asset；background_image为兼容槽，不代替新版独立背景层 |
| 持续主体图 | scene或shot的image_generation.role=subject，生成后绑定相应subject_asset；image为兼容槽，主体默认完整包含 |
| 支持素材 | supporting_asset绑定核实或原创的本地位图；当前生图role只支持background/subject，不能凭空增加supporting接口role |
| SVG、图表 | v2精确关系由原生对象/连接绘制；需要SVG位图时转PNG绑定objects[].asset或项目组件；v1简单chart继续用data/unit/data_source；来源与数字不烘焙进生成图 |
| 图片编号、证据编号 | script-map.json、素材清单、sources；不是自动渲染功能 |
| 预计时长 | 保留为交接估算，不直接写成duration硬限制；用户硬性目标单独记录并核对实际配音 |

`script-map.json` 是制作代理维护的旁路记录，不给渲染器增加虚构字段。最小示例：

```json
{"version":1,"script_file":"source-script.md","scenes":[{"script_scene_id":"M1","scene_index":0,"segment_indices":[0,1],"asset_ids":["power-context-01"],"source_ids":["S1"]}],"assets":[{"asset_id":"power-context-01","kind":"generated_illustration","scene_indices":[0],"path":null,"status":"planned"}],"changes":[]}
```

生成并检查后将path改成实际路径，status改成reviewed；失败写failed和原因。同一新闻多幕合入一个scene时，多条script-map记录可共享scene_index，并分别保存对应segment_indices。只有内容确实需要拆scene时才建立一对多映射、记录理由并逐scene满足契约，不为每一幕或每一句机械新建scene，不丢失或重复口播。合成结束再依据实际timeline.json登记对应时间；不能拿预计时长充作实测。

## 3. 已指定图片的执行

逐张核对主体、数量、状态、环境、构图、镜头、色彩、保护区、参考来源和非现场性质。沿用剧本asset_id（合法字符为字母/数字/下划线/连字符，最多80字符）；不合法时建立原ID到执行ID的显式对应，不能丢失关联。

生成适配器使用image_generation.prompt（缺省取image_prompt），附加共享story_world约束，并将scene/shot的negative_prompt合并到实际请求文本。制作代理仍须核对生成报告中最终payload.prompt包含原正向要求、负向边界与本镜头视角，避免在覆盖prompt时漏掉原稿。接口不接收独立负向参数；仅填写image_prompt不会自动发起付费请求。改变实际prompt会改变缓存指纹，不能假称沿用旧图。

请求尺寸按背景/物体槽选择，最终1920×1080是成片构图，不是所有图片的接口尺寸。预检裁切余量，实际出图后检查返回尺寸、完整轮廓、字幕和人物区域。静态图片的推近不等于真实物体运动；video_prompt仅为规划，现有后端不会生成视频片段。

同一asset_id只建立一个生成任务；适配器拒绝多个生成任务重复ID。scene和shot都可各配置一个image_generation任务，共用当期串行预算、缓存和失败记录；多张图可分配给不同shots或先独立生成后绑定，不能在一个对象里塞入多任务数组。生成脚本产出resolved-project.json后，将同一素材路径绑定到复用位置：v2为对应objects[].asset，v1为subject_asset/supporting_asset；复用位置不重复启用image_generation。v1环境图写入background_asset并保留旧背景差异检查；v2允许背景持续保留，生图用role=subject及object_id绑定对应objects[].asset，不能把生成结果写入未消费的旧槽。多个素材槽不代表单次任务会生成多张图；当前role只支持background和subject，支持素材可原创或独立准备。更新script-map.json；需要独立视角时使用不同ID。

已有图仅在语义与外观适合时复用。需要真实现场/精确型号的镜头须核实素材，不以通用生成图证明投产或产品结构。生成后逐张看图、记录sidecar检查意见及实际使用位置；API成功、reviewed字段或文件可读不能替代看图。

## 视觉交接检查

Blender叙事检查完整镜头母版、源依赖身份、事实标签、帧区间、色彩往返、字幕保护、动态预演和连续观看；镜头可跨越句级字幕，不要求对象动作/1—8镜或固定图片槽。下列对象舞台检查仅约束显式旧图解。

显式旧v2图解按对象舞台落实理解目标、持续对象、关系、cue绑定动作与1—8个连续shots；scene不是原稿“幕”的机械翻译。不同题材按内容安排空间、重点及叙事，不用换背景或构图枚举配额替代推进。v1显式保留原七类构图与旧检查。图片有需求时必须有实际可读路径，planned asset_id和自由文本不能冒充资产。

同世界的主体外观、空间锚点和语义颜色保持连续，环境可持续保留，换视角须有承接理由；图片负责环境/对象，原生文字与SVG负责精确数字、单位及有证据关系。SVG保留源稿并转PNG；不要每幕强制三矩形。v2环境、主体、支持职责可由原生对象及标签承担，不强制三张位图。缺指定素材时保留缺口，不静默取消资产或新版检查。

执行当前视觉预检，检查palette对比度、素材存在、构图和shot覆盖；配音后stage再检查取整后的实际帧边界，查看visual-diversity-report.json，并按真实渲染抽帧检查保护区与可读性。legacy-not-assessed只表示未评估，不能当作passed。不能为通过预检而改写已确认口播、数字或判断。

## 4. 视觉评分与缺口

显式旧v2图解使用visual_selection_version=2，比较至少两种有意义的视觉方法，保留四项门槛及指定素材；v1保留旧图片/非图片比较。已有剧本的图片方案是指定候选，不借评分擅自换主线。若选定方案合格但未获最高分，填写override_reason说明沿用剧本及适用依据；真实性/布局/来源/执行门槛不因剧本指定而豁免。

发现更合适的裁切、景别或叠加方式可制作适配并记录；替换主体、改用纯文字等偏离指定画面的调整需说明。缺配置、生成失败、图片不合格时保留缺口，报告未完成项；不把文字回退当按剧本完成。

指定图片缺失或损坏时Editorial预检/素材阶段明确停止，不再使用文字回退。渲染前逐项核对本地路径并看图，渲染后按实际字幕轨与图片容器检查构图。替代指定图片须记录偏差与依据，不能把未完成素材当作按剧本完成。

## 5. 语音、时机与交付

首次生成按原文顺序配音，英文缩写在确认前收口为明确的中文spoken读法；已有确认读法不再替换。改画面时保持spoken、B声参数及配音缓存，按timeline.json的语义片段索引安排镜头。不能按估算秒数提前切掉关键图或下一幕提前显示，也不恢复已停用的visual_beats字段。片内准确数字、单位、来源与生成示意说明由后期独立合成。

交付script-map.json及script-execution-report.md，后者至少记录：

- 原幕到实际场景、段落与时间的映射是否完整，口播是否有遗漏、重复、数字/判断偏差；文本逐项核对与实际试听分开报告，未试听不声称已听音确认。
- 每张指定图片的生成/复用/失败、看图结果、绑定路径，真实素材与生成示意有无混淆。
- 关键画面/数字是否与同幕语义同步，移动与裁切是否遵守保护区域。
- 所有制作调整、替代方案、遗留缺口及用户认可情况；额外报告完整解码、字幕覆盖等原有技术验证。

这两份交接文件由代理根据源稿、实际项目、素材报告、timeline与验证结果整理，不是渲染器自动产物。未完成项如实标记；没有实际运行时只能交付规范/计划，不能声称已完成生图、配音或成片验收。
