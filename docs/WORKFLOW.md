# 三个技能的节目协作

`news-to-video` 是近期IDC／Web3成片的总入口。按需领域技能核验事实与日期、七日去重并返回证据编辑包；总入口负责整期编辑、叙事与美术、音频、Blender镜头和Remotion合成，持续到实际视频交付。代理宿主提供检索和创作能力，技能不是自动新闻爬虫或任意Markdown导入器。

独立使用领域技能仍交付剧本，明确文字请求输出简报；仅文字／剧本／计划／图片的范围优先。现成确认稿／最终干声直接接入，不重选整期新闻、不为视觉重录。混合一期分域核验与台账，一个节目、一条时间线、一个MP4；独立新闻不强造共同因果。

## 从主题到实际交付

1. 按主题读取IDC或Web3技能、其来源及七日台账，Web3保留专业规则、固定扫描和tracker。打开当篇原文核验，记录原始日期与事件日期、发布主体、版本／项目阶段、影响和限制；覆盖不足如实减项。
2. 编成 [证据编辑包v1](../skills/news-to-video/references/editorial-handoff.md)：稳定package/news/paragraph/claim/evidence ID、canonical_url、topic_key、delta及引用。新口播是内部草案，定稿前可以校订，实质事实变化回查证据；已确认稿件保持内容身份。
3. 用episode.py建立节目及回执，锁定稿件后再生成／冻结音频。公开新配音显式选qwen-uncle-fu-v1；已有最终单声道干声用external_final与准确cue，核验hash和样本身份，倍率1.0，跳过TTS、变速、降噪及重拼。干声母版不混入音乐。
4. 设计观看命题、视角、视觉母题与事实边界，组合观察、解释和隐喻。先核对对象类型及参考、制作必要的可见细节／构图候选并实际看图，把选定图的特征／比例／材质／机位消费到模型；不凭生成设计证明产品或现场。再用冻结最终音频和少量共享语义事件联合编排摄影、对象、图形、灯光与声音，先短段预演再扩完整段落和精修。不强制对象数／镜头数、逐幕生图、旁板或曲线；见[视觉导演](../skills/news-to-video/references/visual-director.md)。
5. 按 [Blender交接v1](../skills/news-to-video/references/blender-handoff.md) 保留.blend与外链依赖，输出明确源／代理／母版身份的PNG序列。统一24fps整数全局[start,end)区间，局部帧从1开始；共享边界只帧化一次。以源、依赖、引擎、参数、色彩与每帧哈希检查恢复，缺帧和代理不能作为正式母版。
6. 正式合成经 `production.py new` 或 `production.py revalidate`，消费已冻结口播和narrative_version=1/narrative_manifest。新作业默认继承已生效基线，已有节目可向复验入口显式提供候选与SHA-256。需同屏联动时按[项目联合导演](../skills/news-to-video/references/blender-handoff.md#项目联合导演接入)接入narrative_directing，由真实覆盖层消费事件／对象状态，必要引用线消费逐帧相机锚点；不能只交motion_plan。完整1920×1080主视觉保持原比例，公共y904—1080字幕轨独立保护，不压缩画面、不默认暗化或CSS运镜。相机变更更新源／摄影身份、帧与投影，并复查全程版面；显示变换只应用一次，旧v1/v2图解保持显式兼容。
7. 从联合预演开始选择音乐及其叙事用途，进入／退出和留白与视觉共用事件；独立sound_tracks承载必要环境音／音效并记录来源、许可、哈希与设计身份。图形、音频与三维分别缓存；只改板面或声音不无故重算有效三维，牵动摄影的事件更改须重查投影。设计声音不冒充现场，不每次动作都加提示音。
8. 核对事实与视觉禁止暗示、完整解码、帧映射、末帧字幕与尾音、字体、保护区和材质色彩。实际看图／带声预演检查主体可辨、同一对象及变化因果、结果停留与边界；完整连续观看、耳机／扬声器试听、技术和用户认可分别记录。短段登记母版样本窗口和偏移，不冒称完整原声；发现问题返修对应层，播放器ended不等于观赏通过。
9. 实际给用户MP4、SRT及简短来源／边界说明，提供可编辑源、冻结音频、镜头清单／母版和必要记录。随后单写节目交付及领域采用回执；内部包／冻结稿不提前记为用户采用。视频交付不等于用户认可或平台发布。

## 可执行入口

下列命令从仓库根执行，使用准备好的渲染Python；文件路径是自己的实际项目。首先参照 [安装与分支](GETTING_STARTED.md)。

```powershell
python './skills/news-to-video/scripts/episode.py' validate-package '<package.json>'
python './skills/news-to-video/scripts/episode.py' init '<episode.json>' `
  --episode-id '<stable-episode-id>' --request '<actual request>' --package '<package.json>' `
  --editorial-plan '<editorial-plan.json>'
# 依实际计划起草并锁定稿件，准备冻结干声、字幕cue和对应镜头。
python './skills/news-to-video/scripts/blender_render.py' '<shots.json>' --blender '<blender executable>'
python './skills/news-to-video/scripts/narrative_media.py' '<shots.json>'
python './skills/news-to-video/scripts/check_runtime.py' --runtime '<render-runtime.json>' --project '<project.json>'
python './skills/news-to-video/scripts/production.py' new --episode '<episode.json>' `
  --project '<project.json>' --runtime '<render-runtime.json>' --output './outputs/episode'
```

编辑包校验只证明引用结构。独立后端预演和校色示例使用 `render.py --backend-only`，示例只产生技术合成产物。导演设计、镜头与证据由制作人员准备。具体字段与命令以随库参考和--help为准，不复制另一套未消费参数。仅导入已渲染帧时的--seal只做技术封存，不证明帧的真实制作来源。

## 稿件、采用与恢复

| 权威资料 | 负责内容 | 恢复约束 |
| --- | --- | --- |
| 领域编辑包 | 新闻事实、归属、日期、delta与引用 | 锁定后内容身份变化停止复用；只补核相关缺口 |
| 节目清单 | request、阶段、稿件／音频身份、失败原因与恢复位置 | 当前revision、独占写锁、同目录原子替换；遗留锁先核验写者停止 |
| 领域ledger | 实际交付采用及文件关联 | 幂等标记；旧剧本改编视频更新同事件，不冒新 |
| Web3 tracker | 有证据的项目原生状态 | 提案／版本／测试网／主网分开，渲染失败不是项目状态倒退 |
| 镜头／音频回执 | 媒体内容及依赖身份 | 只恢复同身份且可解码帧；最终音频不重处理 |

台账先落盘而节目回执失败时，恢复先检查稳定采用标记并补回执，不重复追加。混合节目逐领域提交，保留部分成功，不假称跨Markdown原子事务，不为补台账重渲染。reviewed必须绑定实际检查的合成输入，复核A不能交付B。失败回执保留reason/resume_from，不推进成功阶段；节目工具记录执行者的实际交付证据，不能自动证明用户已收到。

根目录news中的使用者台账和tracker不能随技能更新清空。IDC新增来源和清洁模板，Web3历史与许可保留。每批修改任一媒体技能前询问是否同步维护者配置的公开副本，同批明确答复沿用；正常新闻与视频使用不增加该确认。详见 [维护约定](../skills/news-to-video/references/media-maintenance.md)。
