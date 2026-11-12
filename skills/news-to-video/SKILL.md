---
name: news-to-video
description: 将通用资讯、产品资料、研究稿或已有分幕剧本制作成中文横屏新闻视频；使用固定底部字幕轨和固定B版男声，其他画面由AI按故事世界、图片生成、SVG、数据图形和动画自主创意。用于日更资讯视频、已有稿件成片、图片与图解制作；不用于单纯查新闻、普通润色或一般已有视频剪辑。
---

# 新闻与产品解说视频

**唯一视频生成方案为 Remotion Editorial。** 直接执行 `scripts/render.py 项目.json --output 成片目录`，默认即 `remotion_editorial`；显式同名参数也可用。当前只有一个用户可见制作模式：`daily_editorial`，固定1920×1080、24fps和底部y904—1080字幕轨。hero、flow、chart、story只是底层组件，AI根据每条资讯的故事世界自由组合，不是固定栏目模板。详见[Editorial制作](references/remotion-editorial.md)。不支持的画幅、布局或输入应在配音前明确报错，不能静默改用其他方案。

**一期一片：** 每日/每周的一份剧本默认含多个独立新闻板块，转换为一个项目、一条连续配音/字幕/镜头时间线和一个MP4。标题数、板块数及已有子目录数不能决定成片数。只有用户明确要求分集或逐条独立视频才拆片。旧稿拆片指令与最新用户要求冲突时，保留原稿快照并记录包装调整。

**声音与字幕固定：** 正式技能默认声音为用户认可的B版男声`b-male-v1`，本地Qwen3-TTS参考条件生成，默认1.15倍保留音高变速及已认可轻度降噪。已有口播接入时不得改写`spoken`，字幕和配音构成主时间轴，画面跟随语义时间切换；除非用户明确要求，不因画面创意重新生成配音。模型、参考与采样身份参与缓存；后端缺失明确停止，无其他音色回退。默认核验免费成品音乐池，原速，relative_db=-19、duck_db=2；未指定曲目时从voice-over-under、tech-live、inspired随机选一首，按实际人声活跃段RMS配平并平滑避让，输出署名。详见[配音与音乐](references/audio-production.md)。

仓库公开扩展继续支持显式选择 `qwen-uncle-fu-v1`，不改变默认 B 声、不自动换声。项目与 runtime 的声音 ID 必须一致；已有公开项目保留声音身份。见[公开声音配置](references/public-voice.md)。

## 执行流程

新制作先读[通用资讯视觉导演](references/visual-director.md)。项目设置`director_contract_version: 1`，按[项目格式](references/project-format.md)填写故事世界；旧项目没有该版本时只报告未按新契约评估，不冒称已迁移。仅更新技能不启动生图、配音或重做旧成片。

1. 明确目标、输入、事实、来源、时长要求及交付数量。用户已有分幕剧本时按[接入验收](references/script-handoff.md)沿用口播、顺序、数字、素材ID和证据ID，不默认重写。只有原材料时才编写口播与分镜。新闻保留发布方归属、阶段和证据限制；产品价值须有材料依据，不夸大性能或编造案例。
2. 先写视觉节拍和`story_world`，再逐幕规划构图。每条新闻默认按“Hook—Mechanism—Impact—Boundary”组织，可省略不适用节拍；一个镜头只承担一个主要理解目标。同一新闻的场景必须共享地点、角色、对象、色彩、空间关系和镜头逻辑，不能把无关图片拼成幻灯片。hero、flow、chart、story由AI按内容选择；story使用2—4个`shots`表达连续场景。`visual_strategy`、`motion_plan`、`story_world`和`shots`必须在制作报告或Editorial组件中实际消费，不能只写进JSON后声称已实现。代码图形优先解释精确关系；有必要的环境质感、对象或类比用真实素材或生成示意。图文与运动必须避开字幕轨。
3. 按[视觉评分](references/visual-selection.md)比较图片与文字/图解；内容相关性30%、观赏记忆30%、叙事25%、可读性15%，真实性、来源、布局和执行条件先过门槛。新制作设置visual_selection_version=1并运行score_visuals.py，交付报告。编辑评分不冒称观看效果测试；已有指定画面沿用时记录override_reason。
4. 按[项目格式](references/project-format.md)写UTF-8 JSON。`segments[].text`保留字幕，`spoken`给出中文朗读及缩写读法；按自然语义拆分，不切成单字。相对素材路径基于输入JSON所在目录。`visual_direction`、`image_prompt`和`negative_prompt`说明主体、构图、光色与边界；正负要求必须合并到实际`image_generation.prompt`。
5. 按[生图规范](references/generated-images.md)规划并执行图片任务。每期最多10张新的付费生成图片，10张是上限而不是配额；每张图片必须有`visual_goal`和`story_world`归属。优先复用长期栏目资产，保持同一新闻的连续角色、环境和色彩。记录真实照片、生成示意、原创图解的区别。只请求图片止于素材阶段；只请求剧本/制作计划不读密钥、不请求API、不启动配音。有效配置及已授权范围内直接执行，不重复索要权限。
6. 逐幕判断原创SVG是否更易解释关系、循环、阶段、冗余或闭环，适用时主动按[SVG标准](references/svg-standard.md)制作，保留源文件并转PNG供hero完整包含；简单流程也可由原生flow重绘同一关系。节点入场、箭头绘制和状态高亮必须对应事实关系或阶段变化。不要每幕强制SVG，不以图解冒充实拍、操作规程或链上执行。转换报告只证明源图，不证明最终构图安全。
7. 按[本地运行](references/local-runtime.md)预检Node、Remotion、FFprobe、中文字体及项目显式选定的声音环境。运行render.py，以实测配音长度创建一条时间线。硬性目标不足时保留已确认口播并延长画面；若用户不允许延长，再报告冲突，只有明确授权才改稿。不截断尾音、不靠过度加速凑时长。渲染只读本地素材，不联网生成新闻现场视频。
8. 检查validation.json、完整音视频解码、逐幕抽帧、字幕及音频。字幕从零开始连续替换，最后一条覆盖片尾；底部轨始终保留，素材与运动结束在y904之前。检查字形、来源、版本、日期、治理条件、故事世界连续性和图解关系；标题或字幕过长应合理换行/拆分，不能缩成不可读脚注。
9. 交付MP4、SRT、干声/混音、分镜预览、口播、production-plan.md、项目/时间线/验证JSON、`story-world-report.json`和长期资产清单。新增故事镜头时另交`motion-report.json`；已有剧本另交script-map.json与script-execution-report.md；用SVG时另交源稿、PNG、asset-manifest.json、使用时机和转换报告。只交付内容稿时不强行渲染。技术通过不代表人耳试听、事实、授权或美学验收；未完成项如实记录。

## 构图与素材边界

画面布局由Editorial镜头组件负责，默认hero/flow/chart有统一编辑配色；art_direction记录选择依据，不自动改写组件配色。需要题材专属构图或主题时修改本项目镜头组件并实际渲染验证，不把未消费字段当已实现功能。所有正文、来源与字幕对实际背景需清晰可辨，对比度至少4.5:1。

图片默认`editorial_image_fit=contain`，完整保留图解文字和对象轮廓；cover仅适合允许裁边的场景图，缩放限制在图片容器内。准确产品型号、包装与界面优先使用核实原图；生成素材不证明真实部署、采用率、安全或规模。日期标明原新闻/更新/制作类型，不补造未知日期。

原生流程节点来自当前幕，不沿用其他题材示例；箭头只表达证据支持的关系。所有领域对象都保持事实边界，缺精确结构证据时用原创抽象示意，记录asset_id、类别、结构特征、动作语义、来源与授权。素材动画不同不等于对象不同；同一`story_world`中的对象必须保持视觉连续。当前内置镜头不含自动人物层或visual_beats播放，不能承诺未实现的合成功能。

## 缓存与旧项目

同项目维护复用输出目录。原生B干声、变速与降噪分别按实际身份缓存，音频处理后重测时间线；仅改音乐不改变画面身份。图片、字幕、镜头源码与字体内容改变时重建画面。仅修改music时复用Editorial画面并重新混音，不能把其他引擎历史缓存当候选。

旧项目先另存制作副本，移除已停用布局字段（layout、presenter、visual_beats、image_layout、header_style、background_focus、background_opacity、decoration），按Editorial重新规划构图并设置正确画幅；旧配音另按migrate_audio.py显式迁移。不得悄悄修改旧成片或声称旧版像素兼容。用户只要求旧版改音乐且未同意视觉迁移时，先说明当前入口已不支持该旧布局。

技能维持experimental/on-demand。回归提示见evals/evals.json；可执行检查、真实制作与独立模型评测分别报告。
