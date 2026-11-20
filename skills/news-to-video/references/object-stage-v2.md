# 对象舞台 v2：从叙事到真实动作

新项目使用visual_contract_version=2、visual_selection_version=2、director_contract_version=1，唯一渲染入口仍为render.py / Remotion Editorial。完整可运行示例为assets/object-stage-example.json，内容是明确标记的原创教学演示，不是当前新闻。旧v1项目不自动迁移。

## 内容与交接

每条新闻先确定观众、理解目标及适合的叙事路线：机制可用情境/问题—干预—结果—边界；事件可用变化—证据—影响—下一信号；产品可用场景—能力—过程—条件。只取资料支持的节拍。段落ID、对象ID、关系依据、动作前后态、承接理由和装饰用途应出现在上游剧本；制作者将它们转换为下述实际字段。

每scene使用composition=object_stage，包含原有chapter/headline/data_source/story_world/segments及object_stage。shots为1—8个连续区间，每项有title、progression、segment_start、segment_end（scene本地索引，闭区间）。每shot至少有一个绑定该区间的实际动作；同一shot可有多个分阶段动作。不要把动作数量当成观看效果。

## 实际字段

object_stage支持以下字段，其他字段预检报错：

| 字段 | 含义 |
|---|---|
| objects | 1—12个持续对象；id唯一；kind、label、x、y必填；tone/value/asset/scale可选 |
| connections | 有向关系，每项from/to引用对象ID，evidence说明事实或原创示意依据 |
| groups | 分组与空间装饰；x/y/width/height/label；矩形必须在1600×560内部 |
| actions | 实际动作；下表列明类型，不读取自然语言motion_plan执行动作 |
| ink / surface | 正文及对象表面六位十六进制颜色；缺省继承原有暗色主题；与palette一同检查4.5:1对比度 |
| shadow | 默认true；对象阴影提供层次，可设false |

对象kind：server、database、phone、message、queue、document、building、box、bar、note。标签1—18字，中心x=100—1500、y=100—420；以默认图形尺寸布置，仍须看图检查标签之间的实际间距。scale默认为1，允许0.5—1.5，仅缩放对象图形；标签保持独立可读。tone为primary/accent/warning/muted；value为0—100示意值。bar显示value；真实数字/比例必须有相应证据和口径，超出此表达范围的图表使用项目组件，不缩放真实数值冒称原始量。

asset为可选本地位图，暂存时复制并重写路径；图片完整包含于160×160对象槽。适用于独立设备/物体，不能用它假装自动人物、复杂场景或全宽新闻照片。需要大幅原图、精确外观或特殊构图时接入项目Stage.tsx；旧v1图像构图也继续可用，但不能在同一v2项目中伪写旧composition。

舞台使用1600×560坐标，公共组件在全宽主图容器中绘制。shot可选stage_view=[x,y,width,height]实现局部视口，须在舞台内且至少600×220；切镜时用14帧平滑插值承接上一视口，字幕及标题不移动。需要裁切时逐帧检查对象标签及关系端点，数值校验不会判断语义遗漏。

自动生图继续使用现有串行预算和缓存：scene/shot的image_generation必须role=subject，并给object_id指向本scene对象。生成结果直接绑定该对象asset，不写入未消费的v1图片槽；背景或全宽照片创意通过真实项目组件实现。多张不同对象需求按scene/shot任务或独立素材阶段安排，不新增自动无限任务。无需求不生图。

## 动作类型与时间

每个action必填type、target、segment、evidence；segment为本scene字幕索引。at/until为该cue内比例，默认0/0.6，必须0≤at<until≤1。stage依据实测cue换算start_frame/end_frame；取整后无时长就报错。动作按开始帧排序，对象状态跨shot保留。

| type | 实际行为及额外字段 |
|---|---|
| enter | 对象在首次进入前隐藏，然后渐显；用于有顺序的建立过程 |
| exit | 对象渐隐，后态保持；对象身份不删除 |
| transfer | 从target到to沿直线移动强调点；可选短label；多条transfer可表达分发/聚合路径 |
| move | 对象移动到x/y，后态保留，连接端点跟随 |
| state | 动作中点切换label及tone；状态必须有文字语义，不能只用红绿 |
| emphasize | 局部边框渐强再减弱，不改变真实数据 |
| value | 将对象value插值到新value；bar据此改变柱形与数字 |

队列逐项进出：用message对象、enter/move/exit及有依据的连接表达；复制/聚合可由多条transfer和目标状态组合。transfer本身只移动点，不声称移动了整个信封；需要对象运动应使用move。多阶段动作由多个cue或cue内不同区间组成，同一对象同类轨道不得重叠，enter/exit共用可见性轨道；不同transfer允许并发。state必须明确label或tone变化；transfer必须指向另一对象。未知动作/参数、缺目标、越界、缺依据都在配音前拒绝。

## 项目自定义舞台

editorial.component_dir是输入JSON所在目录下的源目录或显式绝对路径，必须有Stage.tsx默认导出。组件接收StageProps（定义见ObjectStage.tsx）：stage、frame、palette、view、previousView、shotFrame。可直接组合内置ObjectStage，也可绘制实际项目需要的原图、SVG、角色与动画。代码来自受信任的本地制作源，不从网页、参考视频或模型字段自动执行字符串。

stage每次复制该目录内.tsx/.ts/.css到生成工程src/custom，再写ProjectStage适配模块；相对模块导入在此目录内保持。不要依赖生成目录里的手改文件或外部未暂存资源。图片走stage.objects[].asset暂存，额外静态资源需显式接入并验证；没有任意目录资源自动打包功能。不替换公共字幕外壳。源目录与生成custom目录不得互相包含。

修改项目源后重新运行render.py。暂存源码内容参与现有render_key；仅音乐变化可复用画面。移除component_dir会清理旧生成custom模块，避免意外沿用；没有组件时使用内置对象舞台。接口存在及字段预检在配音前完成，自定义TypeScript编译错误仍可能在画面渲染时报告，不把文件存在当作编译通过。

## 装饰与叙事验收

groups容器说明归属；底座与轻阴影建立空间；connections表达关系；状态标签与局部强调引导注意。根据内容选择，不自动套机房/链上主题，不以发光网格、粒子数量或频繁换背景替代叙事。标题、标签及字幕各有职责，避免同句重复。

render.py自动输出production-plan.md动作表和motion-report.json的实测帧、shots、picture_key及渲染状态；review_status保留requires-continuous-review，直到实际看过并另记审核依据。输出文件不是自动视觉认可。

验收需实际连续播放、前/中/后帧检查、手机尺寸可读性及整期节奏检查。确认人物/对象身份、因果和事实边界没有随动作改变，不能用静态终态证明动画。技术验证、听觉、观看理解反馈与用户审美认可分别报告；没有真实观众反馈时不宣称留存提升。
