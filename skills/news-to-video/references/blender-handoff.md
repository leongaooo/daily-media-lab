# Blender 叙事镜头交接 v1

本协议独立于旧对象舞台 v2，不限制镜头、对象数量或画面职责。导演负责观察、解释和隐喻的内容关联、材质光照、调度与连续观看；代码只检查实际媒体契约，不能证明观看效果或用户认可。

## 执行入口

项目保留 `title/scenes[].segments[].text/spoken`。加入 `narrative_version:1` 与 `narrative_manifest:"shots.json"`，不设置旧 `visual_contract_version`。可以使用新合成口播，也可以使用下方冻结入口。画面仍由同一个 `render.py project.json --backend-only --output output --runtime runtime.json` 合成。运行环境只需渲染Python、Node/Remotion、字体与FFprobe；冻结入口不读TTS配置或私人参考。

先按 [建模前设计](visual-director.md#建模前参考与设计消费) 核对参考与可见候选，选定并记录用于造型、材质和摄影的具体特征，再制作可编辑 `.blend`。模型代表帧对照选定图，不能只登记图片路径或用运镜遮掩类型缺失。将源文件及所有外链、字体、贴图、模拟烘焙登记。源blend内容哈希同时覆盖相机、动作、材质、灯光。工具不替导演自动生成通用科技场景。

```powershell
python scripts/blender_render.py shots.json --blender "<blender executable>"
# 导入人工或其他受控任务已渲染的序列时，显式技术封存：
python scripts/narrative_media.py shots.json --seal
python scripts/narrative_media.py shots.json
python scripts/render.py project.json --backend-only --runtime runtime.json --output output
```

`blender_render.py` 从源blend启动固定版本，覆盖清单中明确的输出/引擎/色彩参数，不保存回源blend。逐帧成功后原子记回执；中断恢复仅跳过同身份且内容哈希相同的帧。新版本、引擎、依赖或源变动使相应镜头全部失效，绝不自动换引擎。`--seal` 只表示导入帧已解码并登记身份，操作者必须确保其来自所声明源及参数，不是渲染来源的密码学证明。

worker脚本本身的SHA256也参与执行及验证双方身份；修改实际渲染逻辑后不命中旧帧。若只是升级身份检查而明确保留已生成画面，可在记录原生成实现及此次仅技术重新登记的依据后显式`--seal`；这不表示旧帧已经由新实现重新渲染。

## shots.json

```json
{
  "schema_version": 1,
  "fps": 24,
  "shots": [{
    "shot_id": "s01", "story_world": "power-threshold",
    "start_frame": 0, "end_frame": 480,
    "source": {"path":"scene.blend","sha256":"SOURCE_SHA256"},
    "dependencies": [],
    "render": {
      "blender_version":"4.4.3", "engine":"BLENDER_EEVEE_NEXT",
      "seed":0, "samples":32, "denoise":false,
      "width":1920, "height":1080, "fps":24,
      "display_transform":"AgX", "look":"AgX - Medium High Contrast",
      "exposure":0, "gamma":1
    },
    "media": {
      "role":"master", "pattern":"frames/s01/%06d.png", "source_first_frame":1,
      "bit_depth":8, "color_space":"display-srgb", "alpha":"opaque"
    },
    "handles":{"head":0,"tail":0},
    "facts": {
      "kind":"metaphor", "label":"概念演绎 · 非项目实拍",
      "evidence_ids":["e01"], "prohibited_implications":["不表示已经投产或通电"]
    },
    "receipt":"receipts/s01.json"
  }]
}
```

全局零起点、左闭右开区间连续覆盖整片。局部Blender帧从1起，上例 `[0,480)` 对应局部1—480。`source_first_frame` 允许从明确的局部帧开始取核心画面。转场余量单独声明，不叠入可见时长；v1合成为硬切，非零余量留给导演管理，不能声称已经实现转场。

母版为完整1920×1080、不透明RGB、8/16位无损PNG，已应用一次声明的显示变换；合成不再套显示变换。代理可以使用不同尺寸并标 `role:proxy`，技术封存/预演管理可接受，正式合成拒绝代理。线性EXR与透明合成不在v1，需单独线性合成后交付显示母版。

Remotion逐字节暂存PNG，原1920×1080像素呈现，y904以下仅裁罩，不压成904高；不追加暗化、渐变或CSS运镜。事实身份标签独立置于左上，字幕公共层固定y904—1080。主体、文字、动作需在摄影阶段避开此保护区。实际灰阶、暗部和材质色彩往返仍需抽帧检查，标签本身不能证明色彩正确。

声明字体加载成功后，合成层以相同DOM排版逐条实测字幕高度及宽度；固定36px字号、176px轨道中的可用正文高度为131px。超出时在正式捕帧前停止并指出cue编号，要求按准确音频语义边界拆cue；不自动缩小字、不均分时间、不改冻结口播。`scripts/test_caption_layout.mjs --remotion-install <install> --browser <browser executable> --font <font>`执行真实浏览器边界回归，不下载浏览器。需要复用本机Edge/Chrome时设置`NEWS_TO_VIDEO_BROWSER`，渲染同时显式传入该CLI路径。

## 项目联合导演接入

需要三维与解释图形同屏联动的当前项目可使用 `narrative_directing:"directing.json"`。它是项目消费入口，不是自然语言motion_plan或全题材导演框架。少量事件共用全局24fps整数帧；Blender作者实际读取事件设置摄影关键帧，二维消费者按同一帧编译并显示板面／对象状态；声音制作将同一事件落实为实际声轨起止及包络。只写文件、只改哈希或工具提供API不等于做成动作。

`directing.json` 使用 `schema_version:1,fps:24,width:1920,height:1080`，`events` 保存有名的 `[start_frame,end_frame)`，`camera_events` 列出摄影真正消费的事件名，`projection` 引用逐帧锚点，`overlays` 保存板面内容与事件关联。当前具体消费者仅有 `cavern-flex-v3` 和 `idc-status-v3`：前者显示机制示意、同一任务改排与政策边界，后者显示未来／披露／待核／产品参考状态；不推成任何新闻都能自动编排。panel为 `[x,y,width,height]`，当前板宽至少800、高至少580、y至少100，右缘不超过1856、下缘不超过880；同帧板面不重叠，给字幕与身份标签留空间。真实字体包络不通过就改内容／布局，不缩字截字。

- `cavern-flex-v3` 的 `event_names` 关联panel、prediction、reschedule、result、policy；同一 `task.id` 保持标签、宽度与身份，只改变安排位置，原位轮廓和结果停留让前后能比较。假设曲线持续标“机制示意 · 非实测”，不加入实测刻度、效率或利用率结果；policy与有事件的caveats按语义依次收束。
- `idc-status-v3` 的 `cards` 通过事件显现，`status` 仅future／reported／pending／reference，分别表示未来安排、运营方披露、采购方待核、产品参考。最多三张卡；可选reference图片含路径、SHA256与身份标签，使用图片时最多两张卡。参考的事实与分发权仍由项目核验，不由消费者保证。没有数据时不生成性能趋势。
- 投影JSON逐镜保存shot_id、source_sha256、camera_sha256、camera_events_sha256及连续全局 `frame,x,y,visible`，原1920×1080像素坐标与manifest中的真实源／摄影身份匹配。shot可用camera_event_names覆盖项目摄影事件列表；manifest与投影都绑定该事件子集的内容摘要，接近时序改变而未重导时拒绝。visible不自动证明遮挡；引用线只是编辑解释层，不能冒称实体三维屏或电缆。

图形、参考图片、事件和投影内容进入合成身份，板面文字／图形修改不应重算有效Blender帧；三维仍按源及依赖封存。相机变化须保存新源、更新manifest源／摄影身份、重渲受影响镜头并重导投影，再查主体／图板／字幕全程边界；缺帧、陈旧或不匹配投影停止，不能只改camera_sha256沿用旧锚点。相机关键帧是否真实取自事件、投影是否来自对应模型，仍需检查作者脚本与实际预演。

先做最能暴露因果的低成本联合预演，再扩完整段落。本次洞室先第二句约8秒，再完整24.42秒；保留原干声，以实际可辨主体、同一任务移动、结果停留与政策收束检查联动。短段另记母版SHA256、样本窗口和时间偏移，它不等于完整原声文件；完整段落仍使用完整external_final身份、尾音和末帧。素材与配音技术成功不证明观察者已看懂，也不代表用户认可。

## 冻结最终口播

```json
"voice": {
  "mode":"external_final", "path":"final-vocal.wav", "sha256":"VOICE_SHA256",
  "sample_rate":24000, "samples":480000, "channels":1,
  "processing_identity":{"voice_id":"b-male-v1","tempo_applied":1.15,"denoise":"approved-mild"},
  "playback_rate":1.0, "cues":"cues.json"
}
```

`processing_identity` 记录实际已完成处理，公共示例可使用有分发依据的 `external_final`，不得借此公开私人B声音。文件、采样率、样本数、声道必须匹配；只收单声道干声，不把带音乐旧音轨当干声。源文件逐字节复制到输出voice.wav；混音为单独工作副本。此模式真正绕过make_voice/timeline/TTS/变速/降噪/分段重拼，无失败回退。

cue JSON为数组：`[{"scene":0,"text":"字幕原文","start":0,"end":20}]`。每项按顺序对应一条segments，必须连续覆盖原始音频样本时长，`text/scene` 完全匹配。秒数为实测句级边界，非按文字均分；工具只把绝对时间统一半帧向上转换为整数帧。视频总帧向上取整，末cue显示到最后帧，保留尾音。词级语义事件应另行实测，不从句内比例推断。

配乐显式选 `music.track_id` 并写 `selection_reason`，或者 `mode:off`。不随机选曲。独立 `sound_tracks` 事件有track_id/path/sha256/kind(ambience|effect)/start/duration/gain_db/source_url/license/attribution/purpose，可选fade_seconds/duck_db；保持原速，不隐式循环，设计声音必须标明非现场录音。

交付验收分别记录：媒体身份/完整解码与帧数、色彩往返、抽帧、连续观看、耳机/普通扬声器试听、事实复核、用户方向认可。没有完成的层次保持未验收。
