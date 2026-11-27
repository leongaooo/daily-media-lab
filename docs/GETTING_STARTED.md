# 开始使用

当前适合能使用本地代理技能、愿意记录环境问题的早期参与者。先体验预览和剧本流程，再决定是否配置完整制作环境。

## OPS-01 生产预检与可搬迁源包

完成一个本地作业后，可从仓库根目录运行 `ops/preflight.py` 检查磁盘余量、临时目录、项目／镜头清单、真实母版、冻结音频、Blender 和 render-only runtime。`ops/cache_audit.py` 只读统计可再生缓存与重复哈希，`ops/recovery_drill.py` 在内存回执副本中演练缺帧拒绝和恢复，`ops/portable_package.py` 生成不含 runtime、权重、字体、Key、缓存和日志的相对源包。具体命令与边界见 [OPS-01 入口](../ops/README.md)。

这些检查不会替代新机器安装、GPU／Blender实际运行、连续观看、耳机／扬声器试听或远程发布；报告必须分别记录已做和未做的层。

仓库推送和 PR 会由 `.github/workflows/python-tests.yml` 运行渲染侧 Python 回归及 OPS 纯工具回归；CI 不下载模型，不调用 GPU/TTS/Remotion 或付费生图。

## 无制作环境也能开始

从仓库根目录打开代理。近期IDC／Web3成片请求读取 `skills/news-to-video/SKILL.md`，按需加载对应领域；独立剧本／文字任务读取 `skills/idc-compute-news-digest/SKILL.md` 或 `skills/web3-tech-news-digest/SKILL.md`。根目录 `news/` 是来源地图、可写采用台账与Web3 tracker，不能只搬SKILL.md。新增IDC台账提供清洁模板；已有使用者台账、tracker与公开历史证据不得重置。

剧本流程需要可用的公开检索/网页阅读工具。仓库提供技能指引，不附带通用代理宿主、搜索服务或一键执行新闻采集的 CLI。

## 只准备图片

复制 `skills/news-to-video/config/image-generation/connection.example.json` 为同目录 `connection.json`，填自己的服务地址与图片模型；复制 `api-key.example.json` 为 `api-key.local.json`，在本地填写 Key。二者已被 Git 排除，禁止把 Key 写入工程。

实际适配是 OpenAI 兼容 `POST /images/generations`、单张 `b64_json` 返回，不保证任意平台/模型兼容。仅在项目明确启用生图且提供已授权的连接配置时，渲染入口才调用生图；否则读取已有本地素材，缺少所需配置会停止。

```powershell
# 在仓库根目录执行。先自行准备 Python 及技能 requirements.txt 所列依赖。
$skill = './skills/news-to-video'
$project = './examples/your-project.json' # 替换为自己的真实工程；此路径是示意。
python "$skill/scripts/generate_images.py" $project `
  --connection "$skill/config/image-generation/connection.json" `
  --output './outputs/images'
```

默认只规划，不读取 Key 或联网生成。确认该次生成范围和费用后，在同一命令添加 `--credentials "$skill/config/image-generation/api-key.local.json" --generate --max-new-images 3` 才会发起请求。生成后读取报告并逐张看图。

## 完整制作的实际条件

| 部分 | 当前要求 |
| --- | --- |
| 合成 | Node、固定版本Remotion、浏览器、FFmpeg/FFprobe、中文字体；1920×1080 / 24fps、固定y904—1080字幕轨 |
| 三维镜头 | 自行安装Blender并提供实际可执行路径；版本／引擎和设备以本机检查与shot清单为准，不要求作者盘符 |
| Python | 依赖见 `assets/requirements.txt`；Qwen 独立环境见 `assets/requirements-qwen.txt` |
| 新配音 | 固定Qwen3-TTS模型、CUDA；显式qwen-uncle-fu-v1走独立公开runtime；私人B声不随库提供 |
| 已有最终音频 | external_final所需合法单声道干声、hash、样本率／样本数／声道、处理身份及准确cue；这条分支不需TTS或私人参考 |
| 配乐 | 技能内音乐池及清晰的署名输出 |
| 生图 | 可选；已有本地合法素材可直接使用 |

公开入口为[公开声音配置](../skills/news-to-video/references/public-voice.md)：显式选择 `qwen-uncle-fu-v1`，运行独立 setup 并使用 `examples/public-voice-smoke/project.json`。它无需私人录音，但仍需自行安装依赖与下载模型。新机器安装由 REP-02 单独验收。

旧 `voice-policy.json` 和 `setup_runtime.py` 继续服务私人 B 声，不接受任意替代录音；不带参考音频、私有 profile 或模型权重。

如果你已经具备匹配的授权私有环境，可参照技能的 [本地运行](../skills/news-to-video/references/local-runtime.md) 与 [Editorial 依赖](../skills/news-to-video/references/remotion-editorial.md)，使用自有 `runtime.json`：

```powershell
python './skills/news-to-video/scripts/check_runtime.py' --runtime '<your-private-runtime.json>'
python './skills/news-to-video/scripts/render.py' '<project.json>' `
  --runtime '<your-private-runtime.json>' --output './outputs/episode'
```

其中 `python` 必须指向准备好的渲染环境。输出可包括 MP4、SRT、voice.wav、mix.wav、分镜和验证记录；缓存与输出目录不纳入版本库。新机器安装尚未实测，不能将作者已有本机成功当作首装验证。

## Blender与冻结最终音频

已有最终干声可在仓库外准备仅含渲染依赖的runtime.json，避免使用或覆盖任何私人runtime：

```json
{
  "font": "<readable-Chinese-font>",
  "remotion_install": "<pinned-Remotion-install>",
  "ffprobe": "<ffprobe-executable>"
}
```

选择external_final时不填tts_python、voice_profile或私人参考。project.voice必须包含mode/path/sha256/sample_rate/samples/channels/processing_identity/cues，playback_rate为1.0；路径相对project.json，cue准确对应segments并覆盖原始样本时长。只收有合法使用依据的最终单声道干声，不把带音乐旧音轨冒充干声，不用测试音冒充口播。完整JSON见 [最终音频与镜头交接](../skills/news-to-video/references/blender-handoff.md)。

先按依赖说明准备渲染Python、Node／Remotion、FFprobe、字体和Blender，检查各工具版本与文件路径。这是环境准备，不是针对尚无母版项目的完整预检。check_runtime在项目模式会校验镜头母版；新三维项目应先生成母版，再执行--project检查：

```powershell
$renderPython = '<render-env>/Scripts/python.exe'
# 先准备真实.blend、shots清单和输出目录，生成并封存有效母版。
& $renderPython './skills/news-to-video/scripts/blender_render.py' '<shots.json>' `
  --blender '<your-Blender-executable>'
& $renderPython './skills/news-to-video/scripts/narrative_media.py' '<shots.json>'
# 母版已就绪，再检查external_final项目；这条分支不读取TTS配置。
& $renderPython './skills/news-to-video/scripts/check_runtime.py' `
  --runtime '<render-only-runtime.json>' --project '<project.json>'
& $renderPython './skills/news-to-video/scripts/render.py' '<project.json>' `
  --runtime '<render-only-runtime.json>' --output './outputs/episode'
```

仅渲染／external_final环境不要运行省略--project的check_runtime：其默认分支会检查TTS，而不是一个纯渲染环境检测。准确干声和cue可提前准备；针对三维项目的完整检查则要等母版存在，不用零字节图片或proxy绕过。

Blender可执行路径通过--blender显式给出，无默认E盘要求。制作.blend时先核验本机版本和GPU／引擎，shot清单固定实际Blender版本、引擎、尺寸、采样、色彩和依赖；不默默换引擎。主视觉按完整1920×1080摄影，关键主体／动作在y904上方。PNG母版和低成本proxy分开，正式合成拒绝代理／缺帧／不匹配身份；中断恢复只跳过同身份有效帧。序列不是一个静态图片槽。

### 项目联合预演

先按[视觉导演](../skills/news-to-video/references/visual-director.md#建模前参考与设计消费)准备参考和必要设计候选，选定后才精修模型；当前Images路径仅单张文本提示生成，不支持像素参考输入、编辑或多视锁。设计图与成片图共用同一期串行预算，候选也不自证真实产品细节。

需三维与旁板共同解释时，在自己的项目加入 `narrative_directing:"directing.json"`，按[接入格式](../skills/news-to-video/references/blender-handoff.md#项目联合导演接入)提供事件、实际图形和逐帧投影，摄影作者及声轨使用同一帧源。改板面／声音分别复用缓存，相机改变必须重导锚点、更新实际源并复查边界。该入口目前覆盖两种具体项目板面，不会自动创建场景或适配任意题材；不要只填事件文件就认为联动完成。

先做短段带声预演并保留母版样本窗口身份，再检查完整成片，冻结口播不重录或重复处理。本批消费者回归、实际预演和未验范围见[当前返修记录](progress/2026-11-20-joint-directing-v3.md)，新机器与听感验收仍各自独立；新私声媒体和生成候选不随公开代码入库。

公共声音仍可按上文独立setup使用qwen-uncle-fu-v1，项目显式声音ID与runtime必须匹配。所有模型与runtime放仓库外；external_final不意味着有权分发原人声，公开示例不含私人声音。以新配音产生最终音频后再冻结也必须保留实际处理身份，不能重复1.15倍变速。

## 看测试与示例

[三媒体最小示例](../examples/three-media-minimal/README.md) 提供明确非新闻的证据包、可移植节目输入和显式公开声音project；默认只做JSON／编排检查，不生成声音或视频，不写真实采用台账。真实节目清单由episode.py在自己的outputs目录生成，避免把作者绝对路径和伪造完成哈希写入公开样例。

`skills/news-to-video/assets/example-project.json` 与旧Web3示例保留格式／历史身份，旧私声ID不能当公共可复现入口。公开声音短样本继续见examples/public-voice-smoke，其既往许可和认可范围保留。新项目若选三维使用独立narrative_version=1，不同时套旧visual_contract_version。

可执行回归在技能scripts/test_*.py，提示词规格在各evals；二者不同。完整测试需准备requirements中的依赖；无GPU行为检查不调用模型，不等于真实GPU制作、完整连续观看、耳机／普通扬声器试听或用户审美认可。本批公开适配结果由 [进度记录](progress/2026-11-20-three-media-blender.md) 单独列明，REP-02／REP-02-01新机器验证仍未完成。

每批更新三个媒体技能任意内容前询问是否同步维护者配置的公开目标，同批明确答复沿用；正常使用不额外确认。详见 [维护约定](../skills/news-to-video/references/media-maintenance.md)。
