# 可执行视觉契约

新Blender序列路径为独立 `narrative_version:1`，执行契约见 [blender-handoff.md](blender-handoff.md)。本页v1/v2保留旧图解兼容，不将旧对象数、图片槽或镜头数强加给三维。序列必须验证真实帧、位深、色彩身份、源依赖和内容回执，不能只写规划元数据。

## v2：连续对象与叙事动作（旧图解兼容）

旧v2图解使用visual_contract_version: 2，具体可运行字段和示例见[对象舞台协议](object-stage-v2.md)。导演流程、画幅、声音、图片预算及一期一片沿用主技能；director_contract_version仍为1。旧项目不自动迁移。

composition=object_stage，以稳定对象、关系、动作、分组与视口组织机制、数据和证据。每scene有1—8个连续字幕绑定shots，每shot写title、progression及本scene的segment_start/segment_end，覆盖全部字幕。每shot至少关联一个实际动作；动作可在镜头内按语义分阶段执行。不同新闻可共享构图语法，内容与空间安排应按题材设计，不能只换标题。

同一场景允许保留背景和对象；不再用换背景数量或构图枚举数量代替叙事推进。环境、主体、支持是职责，可由原生对象、分组、标签、真实素材或生成图承担；不强制三张位图。可靠且适合的新闻/产品原图仍须按事实需求使用，不借原生图形取消已指定素材。图片与代码图形按理解目标选择，visual_selection_version: 2比较至少两种有意义的方案，不给图片近分优先。

object_stage.actions将字幕片段索引及cue内比例转换为实测帧，舞台跨shot保留对象状态。动作类型、引用、几何边界、配色及时间先预检，帧取整后再检查零帧动作。输出motion-report.json实际动作帧表与picture_key；它证明已编译/渲染，不证明连续播放或观看效果已验收。

顶部章节/标题、底部字幕及来源由公共外壳控制；主图采用全宽对象舞台。主题不固定浅色；stage.ink和surface必须与palette配对检查实际可读性。项目自定义Stage.tsx由editorial.component_dir指定的源目录每次重新暂存，其内容参与画面缓存；禁止把生成输出目录当源目录。

## v1：原构图与素材检查（显式保留兼容）

以下规则只适用于visual_contract_version: 1，不用于评估v2；无版本仍为legacy-not-assessed。v1构图、背景差异、素材职责与2—4镜头规则保留，不对旧项目静默放宽。


显式v1制作设置visual_contract_version: 1。旧构图无版本时报告legacy-not-assessed；object_stage必须显式指定v2，不能借省略版本绕过对象检查。旧项目不自动迁移。

composition 支持 hero_scene、timeline、system_map、evidence_board、workbench、comparison、story；保留 hero/flow/chart 兼容入口。先选视觉语法再规划主题；一期多条新闻至少两种主构图，相邻新闻主构图不能相同。

每条新闻2—4个shots，每个shot有title、detail、segment_start/segment_end（本新闻字幕索引，零起始，闭区间）。shots必须连续、不重叠、覆盖全部字幕。按实测cue边界取整到24fps，不用固定八秒。shot可覆盖composition、focus（节点索引）、camera_language（none/slow-push/slow-pan-right）和三类素材。相同对象保留同一story_world.id、主体与空间位置，通过局部高亮、构图或镜头距离推进。

scene.palette提供background/primary/accent/warning/muted，六位十六进制颜色。也可从story_world.palette继承，场景值优先。固定顶部信息区与y904—1080字幕轨不随主题移动。

background_asset是环境位图、subject_asset是主体位图、supporting_asset是支持位图。每个shot必须能继承或覆盖三类素材，三者职责不能复用同一文件。背景仅允许环境图裁切；主体默认contain完整保留。相邻镜头不得使用相同背景（按内容散列比较，改名无效）；同世界通过不同视角保持物体与环境连续。可靠图片可用时至少一幕实际使用背景或主体图。无核实素材时用明确标记的原创示意，不能伪造产品截图、Logo或网络部署。

原生图形负责精确标签、版本、数字与关系；图片负责环境、对象质感；支持素材负责状态提示。timeline/flow/workbench使用2—3个editorial_nodes；comparison使用恰好2个有证据的状态；system_map/evidence_board使用2—5个节点。shot.nodes可覆盖本镜头节点，focus为当前节点索引。system_map是抽象关系，不能冒称真实拓扑；workbench是原创编辑示意，不能冒充CLI真实输出；comparison仅在有证据的前后状态中使用。

visual_direction、background_direction、visual_strategy与image_prompt是导演依据；必须把意图翻译到上述结构化字段，不会仅凭文本自动改变画面。image_generation.enabled且未resolved时，render.py要求--image-connection及所需--image-credentials，调用现有预算/缓存/失败记录保护的generate_images.py后再预检和配音。negative_prompt合并进实际请求；仅image_prompt不发起付费请求。新增图每期至多10次付费尝试，不自动重试。scene或shot都可配置image_generation；shot级请求自动继承故事世界并共享当期串行预算和缓存，生成结果写回对应shot素材槽。生成背景需逐shot规划不同视角，不能用一个生成结果覆盖全条新闻。

render.py在配音前检查计划、素材、文字主题对比度，stage再检查实际帧边界并产出visual-diversity-report.json。该报告不证明图片语义、事实关系或审美通过；最终仍需看成片与边界帧。SVG保留源稿及转PNG报告，SVG/原生箭头只表达有来源支持的关系。无需精确关系时不强制SVG，不把每条新闻画成三矩形。
