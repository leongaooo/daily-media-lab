# Editorial项目格式

唯一画面方案为Remotion Editorial，详见[镜头与运行](remotion-editorial.md)。使用UTF-8 JSON，相对图片路径基于输入文件所在目录。`assets/example-project.json`为可改写示例。输出目录与源素材分开；输出project.json是快照，移动时必须带走素材并修正相对路径。

一期默认一份项目，多条新闻为有独立证据的scenes板块，一次生成一个MP4。已有剧本先按[接入规则](script-handoff.md)记录幕号、片段、资产与来源映射。

| 字段 | 实际用途 |
|---|---|
| title / date_label | 节目名与日期类型元数据；需要片内日期时写入chapter/headline |
| production_mode | 当前只接受`daily_editorial`；用户不选择其他制作模式 |
| director_contract_version | 新制作设1；预检故事世界、视觉目标和固定声音参数；旧项目未设置时标为legacy-not-assessed |
| editorial | width=1920、height=1080、fps=24；captions默认bottom_rail，新导演契约固定bottom_rail，旧项目可显式off；SRT总是独立输出 |
| width / height / fps | 可省略；写出时必须与1920/1080/24一致 |
| visual_engine | 可省略；只接受remotion_editorial |
| duration | 可省略，按实测配音定长；硬性目标不足时报错，不截音 |
| voice | 默认b-male-v1；仓库扩展允许显式qwen-uncle-fu-v1且必须匹配runtime；speed默认1.15，新导演契约固定1.15，旧项目接受0.5—2.0有限数值；变速后默认轻度降噪 |
| music | mode=pool/off；style=business/news/documentary；relative_db=-19、duck_db=2；省略track_id时从核验的三首随机选择；start_seconds可选 |
| font | 可选中文字体文件；优先于运行环境字体 |
| art_direction / sources / footer | 制作意图、证据/素材来源、必要披露；不自动成为画面层 |
| visual_selection_version | 新制作设1；每幕visual_selection按视觉评分规范填写 |
| scenes | 按顺序排列的镜头，同一新闻可有多幕 |

每幕实际支持：

| 字段 | 实际用途 |
|---|---|
| chapter / headline / center_text | 章节、主标题和中心说明；日期等需片内显示的内容写在这些字段 |
| editorial_kind | hero、flow、chart或story；建议显式指定 |
| editorial_summary | hero标题下的简短说明，省略时用首条字幕 |
| image / background_image | 本地位图；二者都写时image优先，只有一个图片槽；不存在或损坏时停止，无文字回退 |
| editorial_image_fit | 默认contain完整包含；cover允许裁边，容器外不扩张 |
| editorial_nodes | flow必需，2—3个含非空title及可选detail的节点，不能混入其他题材样例 |
| data / unit / data_source | chart需1—5行label/value非负有限数值与来源；data_source也在hero/flow显示 |
| segments | 自然语义片段：text为字幕，spoken为中文读法；事实相同、顺序不变，缩写保留在字幕中 |
| visual_direction / background_direction / image_prompt / negative_prompt / video_prompt | 逐幕制作记录；提示词本身不触发API，也不自动播放外部动画 |
| image_generation | 独立生图阶段配置：enabled、asset_id、role、prompt、size、quality；由generate_images.py执行，render.py只读本地文件 |
| visual_selection | 当前幕的候选、门槛、评分与理由，详见visual-selection.md |
| story_world | 当前新闻的连续视觉世界；必填id、setting、continuity_notes、facts_boundary，可补充roles、objects、palette；同一新闻的镜头和图片必须归属同一世界 |
| visual_strategy | establishing_scene、evidence_diagram、animated_flow、data_reveal、source_card、boundary_scene等视觉意图；必须由组件消费或在报告中明确未实现 |
| motion_plan | entrance、emphasis、camera等受支持动效预设；只表达语义关系或阶段变化 |
| shots | story镜头的2—4个连续节拍；新契约每项必须含segment_start、segment_end（本幕字幕索引，从0起，闭区间），实际起止由实测字幕换算；另可含title、detail、image、role |
| image_budget | 可选的项目预算记录；`max_paid_generated_images`固定不超过10，10是上限而非生成配额 |

`mode=product_image/theme_text/chart`仅作素材分类与缺省镜头推断，不是其他渲染方案。SVG先经svg_to_png.py转PNG，绑定image并使用hero/contain；简单顺序可用flow原生节点重绘。`motion_assets`、主题色等额外元数据不会自动成为动画或配色，不得报告为已执行；当前已消费的动效字段是`motion_plan`，故事镜头字段是`shots`。`story_world`用于故事连续性、图片提示词和制作报告；不自动改变组件布局，除非组件明确消费其字段。

字幕轨y904—1080；镜头、来源与运动结束在y904之前。人物、复杂设备动画等需在本项目Editorial组件中明确实现并验证，当前内置模板无自动人物层。长文本需通过抽帧检查，不承诺任意长度自动适配。

新契约的最小场景规划（仍须补齐segments及现有视觉评分）：

```json
{
  "director_contract_version": 1,
  "production_mode": "daily_editorial",
  "scenes": [{
    "visual_goal": "理解公交调度调整如何影响换乘",
    "story_world": {
      "id": "city-transit",
      "setting": "同一抽象城市的站点与调度中心",
      "roles": ["乘客", "调度员"],
      "objects": ["同一辆公交", "同一换乘站"],
      "palette": ["#183747", "#E9F1F0"],
      "continuity_notes": "保持车辆外观和地图方位，先整体后局部",
      "facts_boundary": "生成示意，非真实城市现场；关系以资料为准"
    }
  }]
}
```

同一world id的定义必须一致。元数据校验不能证明出图连续性。render.py输出story-world-report.json；reusable-assets.json由制作代理根据实际看图、来源和用途编制，字段见visual-director.md。已有同目录项目的口播、voice和duration变化会被拒绝；明确授权改稿时另存制作副本。首次合成及缓存缺失仍可能启动B声后端，不宣称已支持任意外部音频原样导入或仅凭字段冻结二进制音轨。

不支持的布局字段会在配音前报错：layout、presenter、visual_beats、image_layout、header_style、background_focus、background_opacity、decoration。旧项目需另存副本后按Editorial重新规划，不隐式恢复退休方案或旧坐标。

输出video.mp4、voice.wav、mix.wav、captions.srt、storyboard.jpg、narration.txt、production-plan.md、project.json、timeline.json、validation.json，以及可编辑的remotion源码目录。新项目另交视觉评分；已有剧本另交script-map与执行报告；SVG项目保留源稿/PNG与素材清单。缓存、模型、私有参考与API密钥不进入技能或交付包。公开发布需附音乐署名.txt。
