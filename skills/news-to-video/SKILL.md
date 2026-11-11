---
name: news-to-video
description: 将已有分幕剧本、新闻稿、产品资料或口播稿制作成中文视频内容包，使用Remotion Editorial生成本地横屏成片；也支持只生成剧本指定图片。用于明确的视频制作、连续字幕、B版男声配音与音乐调整任务。不用于单纯查新闻、日报、普通润色或一般已有视频剪辑。
---

# 新闻与产品解说视频

**唯一视频生成方案为 Remotion Editorial。** 直接执行 `scripts/render.py 项目.json --output 成片目录`，默认即 `remotion_editorial`；显式同名参数也可用。默认且当前支持1920×1080、24fps，底部y904—1080为独立字幕轨。画面根据文稿使用hero、flow、chart构图；详见[Editorial制作](references/remotion-editorial.md)。不支持的画幅、布局或输入应在配音前明确报错，不能静默改用其他方案。

**一期一片：** 每日/每周的一份剧本默认含多个独立新闻板块，转换为一个项目、一条连续配音/字幕/镜头时间线和一个MP4。标题数、板块数及已有子目录数不能决定成片数。只有用户明确要求分集或逐条独立视频才拆片。旧稿拆片指令与最新用户要求冲突时，保留原稿快照并记录包装调整。

**声音与音乐：** 项目可显式选择公开内置男声 `qwen-uncle-fu-v1`（官方 Apache-2.0 Qwen 0.6B CustomVoice / Uncle_Fu，无需参考录音），或保留私人 `b-male-v1`。省略 ID 仍按旧 B 声处理；不得自动换声。项目与 runtime 的 ID 必须相同。二者默认1.15倍保留音高变速和轻度降噪；公开音色尚待维护者人耳认可。后端缺失明确停止。默认核验免费成品音乐池，原速，relative_db=-19、duck_db=2；未指定曲目时从voice-over-under、tech-live、inspired随机选一首，按实际人声活跃段RMS配平并平滑避让，输出署名。详见[配音与音乐](references/audio-production.md)和[公开声音配置](references/public-voice.md)。

## 执行流程

1. 明确目标、输入、事实、来源、时长要求及交付数量。用户已有分幕剧本时按[接入验收](references/script-handoff.md)沿用口播、顺序、数字、素材ID和证据ID，不默认重写。只有原材料时才编写口播与分镜。新闻保留发布方归属、阶段和证据限制；产品价值须有材料依据，不夸大性能或编造案例。
2. 逐幕规划叙事与构图。hero承载主标题和图像/主题文字；flow使用当前幕2—3个`editorial_nodes`表达有证据的顺序；chart保留数据、单位、来源和口径。代码图形优先解释精确关系；有必要的环境质感、对象或类比用真实素材或生成示意。一个镜头一个主要理解目标，图文与运动必须避开字幕轨。
3. 按[视觉评分](references/visual-selection.md)比较图片与文字/图解；内容相关性30%、观赏记忆30%、叙事25%、可读性15%，真实性、来源、布局和执行条件先过门槛。新制作设置visual_selection_version=1并运行score_visuals.py，交付报告。编辑评分不冒称观看效果测试；已有指定画面沿用时记录override_reason。
4. 按[项目格式](references/project-format.md)写UTF-8 JSON。`segments[].text`保留字幕，`spoken`给出中文朗读及缩写读法；按自然语义拆分，不切成单字。相对素材路径基于输入JSON所在目录。`visual_direction`、`image_prompt`和`negative_prompt`说明主体、构图、光色与边界；正负要求必须合并到实际`image_generation.prompt`。
5. 用户指定生成图片时按[生图规范](references/generated-images.md)执行唯一素材任务、看图后绑定本地路径。复用已有合适素材，记录真实照片、生成示意、原创图解的区别。只请求图片止于素材阶段；只请求剧本/制作计划不读密钥、不请求API、不启动配音。有效配置及已授权范围内直接执行，不重复索要权限。
6. 逐幕判断原创SVG是否更易解释关系、循环、阶段、冗余或闭环，适用时主动按[SVG标准](references/svg-standard.md)制作，保留源文件并转PNG供hero完整包含；简单流程也可由原生flow重绘同一关系。不要每幕强制SVG，不以图解冒充实拍、操作规程或链上执行。转换报告只证明源图，不证明最终构图安全。
7. 按[本地运行](references/local-runtime.md)预检Node、Remotion、FFprobe、中文字体及项目选定的声音环境。运行render.py，以实测配音长度创建一条时间线。硬性目标不足时缩稿或延长，不截断尾音、不靠过度加速凑时长。渲染只读本地素材，不联网生成新闻现场视频。
8. 检查validation.json、完整音视频解码、逐幕抽帧、字幕及音频。字幕从零开始连续替换，最后一条覆盖片尾；底部轨始终保留，素材与运动结束在y904之前。检查字形、来源、版本、日期、治理条件和图解关系；标题或字幕过长应合理换行/拆分，不能缩成不可读脚注。
9. 交付MP4、SRT、干声/混音、分镜预览、口播、production-plan.md、项目/时间线/验证JSON。已有剧本另交script-map.json与script-execution-report.md；用SVG时另交源稿、PNG、asset-manifest.json、使用时机和转换报告。只交付内容稿时不强行渲染。技术通过不代表人耳试听、事实、授权或美学验收；未完成项如实记录。

## 构图与素材边界

画面布局由Editorial镜头组件负责，默认hero/flow/chart有统一编辑配色；art_direction记录选择依据，不自动改写组件配色。需要题材专属构图或主题时修改本项目镜头组件并实际渲染验证，不把未消费字段当已实现功能。所有正文、来源与字幕对实际背景需清晰可辨，对比度至少4.5:1。

图片默认`editorial_image_fit=contain`，完整保留图解文字和对象轮廓；cover仅适合允许裁边的场景图，缩放限制在图片容器内。准确产品型号、包装与界面优先使用核实原图；生成素材不证明真实部署、采用率、安全或规模。日期标明原新闻/更新/制作类型，不补造未知日期。

原生流程节点来自当前幕，不沿用其他题材示例；箭头只表达证据支持的关系。AIDC对象保持工程中立，缺精确结构证据时用原创抽象示意，记录asset_id、类别、结构特征、动作语义、来源与授权。素材动画不同不等于对象不同。当前内置镜头不含自动人物层或visual_beats播放，不能承诺未实现的合成功能。

## 缓存与旧项目

同项目维护复用输出目录。原生干声、变速与降噪分别按实际身份缓存，音频处理后重测时间线；仅改音乐不改变画面身份。图片、字幕、镜头源码与字体内容改变时重建画面。仅修改music时复用Editorial画面并重新混音，不能把其他引擎历史缓存当候选。

旧项目先另存制作副本，移除已停用布局字段（layout、presenter、visual_beats、image_layout、header_style、background_focus、background_opacity、decoration），按Editorial重新规划构图并设置正确画幅；旧配音另按migrate_audio.py显式迁移。不得悄悄修改旧成片或声称旧版像素兼容。用户只要求旧版改音乐且未同意视觉迁移时，先说明当前入口已不支持该旧布局。

技能维持experimental/on-demand。回归提示见evals/evals.json；可执行检查、真实制作与独立模型评测分别报告。
