# 生成图片：时机、构图与执行

2026-10-30 用户确认：让图片承担场景与物体表达，逐步提高视频的可理解性、记忆点和观看趣味。不能将制作检查或接口成功当作传播效果证据。

先按[逐幕视觉评分](visual-selection.md)评估并记录候选，再决定是否生成。图片承担观赏、环境和记忆价值，数字/关系仍独立合成；不可因需要SVG而排除场景图。

收到已有剧本时按[剧本接入](script-handoff.md)逐张执行指定图片需求，保留asset_id对应关系。将image_prompt与negative_prompt合并至image_generation.prompt后发送，当前接口没有自动读取独立负向字段。同一asset_id只建立一个生成任务，复用幕绑定同一本地路径；失败、缺配置或不合格时明确标记缺口，不静默回退为文字并声称完成。

## 逐幕判断

先写清“观众这一幕要理解或感受到什么”，再选择视觉：

| 内容 | 图片目标 | 形式 |
| --- | --- | --- |
| 具体物体 | 认识对象、看清轮廓和关键特征 | 单物体特写，role=subject |
| 段落重点 | 建立一个可记住的视觉锚点 | 关键动作或场景 |
| 规模、距离、密度、环境 | 增强感受，帮助理解抽象描述 | 场景铺底，role=background |
| 抽象概念 | 使用贴近口播的类比增加理解与趣味 | 类比插画，明确不是真实工程结构 |
| 数字、比较、拓扑、流程 | 准确展示关系和口径 | 独立图表/SVG，图片仅辅助 |
| 真实品牌、型号、事件现场 | 证明具体对象是什么 | 优先核实过的真实素材，生成图不能替代证据 |

不按每条字幕生成图片。一段先建立环境，再按语义切特写或图解；保留配色、光线、设备外观和人物风格的连续性。已有合适素材优先复用。需要用户人物素材时保留其身份与来源；当前内置Editorial镜头不自动叠加人物，须明确实现后验证。

## 尺寸与画面分工

以Editorial 1920×1080构图为准，底部y904—1080是独立字幕轨。根据hero图片槽与叙事选择接口支持的横向或方形尺寸，不把成片画幅当API保证。完整对象与图解默认contain，场景图可显式cover；记录实际返回尺寸、裁切余量和轮廓检查。背景图在当前模板中同样进入单一图像槽，不声称自动全屏铺底、透明度或多图叠加。文字、数字、Logo与精确关系由代码独立绘制；图片不能侵占字幕轨。

提示词先规定主体位置、完整轮廓、裁切余量、留白、与口播对应的单个动作、风格、光线和非现场性质。仅写“科技感”或“好看”不够。文字、Logo、数字和数据关系由后期绘制。泛用示意不能冒充某厂商产品，单张轻推近不声称物体真的运动。

## 接口与独立密钥

### 技能内本机配置（2026-11-04迁移）

本机可复用配置已迁移到 `$skill/config/image-generation/`，实际目录为 `./skills/news-to-video/config/image-generation/`：`connection.json` 为连接文件，`api-key.local.json` 为独立凭据文件。先检查两者存在、连接协议与模型字段有效、凭据含非空 `api_key`，不要输出密钥。当前连接使用 aiyuhub 的 OpenAI兼容 Images API、模型 `gpt-image-2`；文件存在不代表当次接口必然成功，以生成报告为准。

使用此技能在本机制作时，只检查上述技能内目录或用户当次显式提供的其他路径；配置失效时明确报告并询问，不再回退到旧 Codex 目录。旧 Codex `image-demo` 目录仅为历史来源，不再是技能的查找或运行依赖。路径是本机适配信息，其他机器不照抄。

已实测的适配为OpenAI兼容Images API：POST base_url + /images/generations，单张b64_json响应。当前只实现这一协议，不自动切平台、切模型或退回Responses。base_url和Key必须来自同一签发平台。

connection.json示例（不含密钥）：

```json
{"base_url":"https://YOUR-RELAY.example/v1","api_mode":"images","image_model":"gpt-image-2"}
```

独立api-key.local.json：`{"api_key":"由用户本地填写"}`。配置与凭据统一保留在技能内 `config/image-generation/`；凭据不得复制到素材目录、清单、日志、成片工程或交付压缩包。分享技能时排除凭据文件，由接收方在本机重新填写。没有有效配置时仅输出生成计划，不能隐性使用其他凭据或云端服务。

分镜示例：

```json
{
  "image_generation": {
    "enabled": true,
    "asset_id": "datacenter-opening",
    "role": "background",
    "prompt": "原创机房场景，中部为通用机柜，上部与下部低细节，左侧给主持人留空，无文字和品牌，非现场照片",
    "size": "1536x1024",
    "quality": "medium"
  },
  "editorial_image_fit": "contain"
}
```

使用运行时Python执行：

```powershell
# 只检查和规划，不读取Key、不联网
& $runtime.python "$skill/scripts/generate_images.py" project.json --connection "$skill/config/image-generation/connection.json" --output assets/generated
# 用户已授权生成时才执行；默认最多3张新图，串行单次请求
& $runtime.python "$skill/scripts/generate_images.py" project.json --connection "$skill/config/image-generation/connection.json" --credentials "$skill/config/image-generation/api-key.local.json" --output assets/generated --generate --max-new-images 3
```

生成后读取generation-report.json并逐张看图，检查口播对应、异常结构/手指、品牌、文字、水印、误导性关系和裁切。标注sidecar reviewed=true及检查意见。失败或超时不自动重试；保留submitted标记，先检查上游任务和账单，再人工决定是否清除标记重新提交。

缓存按端点、模型、提示词、尺寸和质量指纹保存，并校验图片SHA256。重复执行命中缓存不计费请求。脚本默认仅规划；--generate为显式执行开关。现有会话已经授权的图片生成无需反复问同一权限。

## 合成和交付

resolved-project.json已绑定生成图路径，可直接传给render.py。生成脚本不调用TTS或渲染。渲染器只读取本地素材，不调用图片API。整理工程时将路径改成工程内相对路径，并带走全部图片、sidecar、生成报告、独立主持人和SVG；不能带走Key。

render.py读取image或background_image，默认contain且缺图/损坏停止；所有图片内容进入画面缓存身份。没有文字回退或旧图片层字段。resolved-project中的subject绑定image并设置editorial_image_fit=contain；background绑定background_image，具体构图由Editorial镜头负责。

验收：逐张看图、手机尺寸看分镜、检查字幕和人物全程边界、完整视频解码、声音/字幕时间线检查。背景变化不要求重新生成语音。不要宣称完成了未实施的人耳试听或平台发布检查。

## 改善观看体验的反馈

交付简短对照说明：这一处图片解决了什么理解问题；有没有新增视觉干扰。经用户授权发布后才记录真实反馈，可比较开头留存、平均观看时长/完播率、收藏及评论中“没看懂”的问题。分开记录平台、样本量、发布时间和视频长度；不把不同内容之间的波动直接归因为图片。每轮只优先改一个明确问题，不追求用生成图填满每一幕。

未来选题与口播优先在开头3–5秒给出观众能理解的具体问题或反常结果；正文每段围绕一个理解目标，结尾给出可带走的判断方法。不使用无依据的惊叹、夸大危机或机械求赞。修改已有项目时尊重当前任务范围，不能为了优化开头擅自重写整篇。
