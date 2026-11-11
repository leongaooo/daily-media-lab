# Editorial项目格式

唯一画面方案为Remotion Editorial，详见[镜头与运行](remotion-editorial.md)。使用UTF-8 JSON，相对图片路径基于输入文件所在目录。`assets/example-project.json`为可改写示例。输出目录与源素材分开；输出project.json是快照，移动时必须带走素材并修正相对路径。

一期默认一份项目，多条新闻为有独立证据的scenes板块，一次生成一个MP4。已有剧本先按[接入规则](script-handoff.md)记录幕号、片段、资产与来源映射。

| 字段 | 实际用途 |
|---|---|
| title / date_label | 节目名与日期类型元数据；需要片内日期时写入chapter/headline |
| editorial | width=1920、height=1080、fps=24；captions默认bottom_rail，可显式off；SRT总是独立输出 |
| width / height / fps | 可省略；写出时必须与1920/1080/24一致 |
| visual_engine | 可省略；只接受remotion_editorial |
| duration | 可省略，按实测配音定长；硬性目标不足时报错，不截音 |
| voice | id支持b-male-v1或显式qwen-uncle-fu-v1，必须匹配runtime；speed默认1.15，接受0.5—2.0有限数值；变速后默认轻度降噪 |
| music | mode=pool/off；style=business/news/documentary；relative_db=-19、duck_db=2；省略track_id时从核验的三首随机选择；start_seconds可选 |
| font | 可选中文字体文件；优先于运行环境字体 |
| art_direction / sources / footer | 制作意图、证据/素材来源、必要披露；不自动成为画面层 |
| visual_selection_version | 新制作设1；每幕visual_selection按视觉评分规范填写 |
| scenes | 按顺序排列的镜头，同一新闻可有多幕 |

每幕实际支持：

| 字段 | 实际用途 |
|---|---|
| chapter / headline / center_text | 章节、主标题和中心说明；日期等需片内显示的内容写在这些字段 |
| editorial_kind | hero、flow或chart；建议显式指定 |
| editorial_summary | hero标题下的简短说明，省略时用首条字幕 |
| image / background_image | 本地位图；二者都写时image优先，只有一个图片槽；不存在或损坏时停止，无文字回退 |
| editorial_image_fit | 默认contain完整包含；cover允许裁边，容器外不扩张 |
| editorial_nodes | flow必需，2—3个含非空title及可选detail的节点，不能混入其他题材样例 |
| data / unit / data_source | chart需1—5行label/value非负有限数值与来源；data_source也在hero/flow显示 |
| segments | 自然语义片段：text为字幕，spoken为中文读法；事实相同、顺序不变，缩写保留在字幕中 |
| visual_direction / background_direction / image_prompt / negative_prompt / video_prompt | 逐幕制作记录；提示词本身不触发API，也不自动播放外部动画 |
| image_generation | 独立生图阶段配置：enabled、asset_id、role、prompt、size、quality；由generate_images.py执行，render.py只读本地文件 |
| visual_selection | 当前幕的候选、门槛、评分与理由，详见visual-selection.md |

`mode=product_image/theme_text/chart`仅作素材分类与缺省镜头推断，不是其他渲染方案。SVG先经svg_to_png.py转PNG，绑定image并使用hero/contain；简单顺序可用flow原生节点重绘。motion_assets、主题色等额外元数据不会自动成为动画或配色，不得报告为已执行。

字幕轨y904—1080；镜头、来源与运动结束在y904之前。人物、复杂设备动画等需在本项目Editorial组件中明确实现并验证，当前内置模板无自动人物层。长文本需通过抽帧检查，不承诺任意长度自动适配。

不支持的布局字段会在配音前报错：layout、presenter、visual_beats、image_layout、header_style、background_focus、background_opacity、decoration。旧项目需另存副本后按Editorial重新规划，不隐式恢复退休方案或旧坐标。

输出video.mp4、voice.wav、mix.wav、captions.srt、storyboard.jpg、narration.txt、production-plan.md、project.json、timeline.json、validation.json，以及可编辑的remotion源码目录。新项目另交视觉评分；已有剧本另交script-map与执行报告；SVG项目保留源稿/PNG与素材清单。缓存、模型、私有参考与API密钥不进入技能或交付包。公开发布需附音乐署名.txt。
