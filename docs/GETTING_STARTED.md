# 开始使用

当前适合能使用本地代理技能、愿意记录环境问题的早期参与者。先体验预览和剧本流程，再决定是否配置完整制作环境。

## 无制作环境也能开始

从仓库根目录打开代理，让它读取 `skills/web3-tech-news-digest/SKILL.md`。根目录 `news/` 是配套来源地图与可写台账，不能只搬走 SKILL.md。公开台账从空白开始，原作者历史采用记录没有复制进来。

剧本流程需要可用的公开检索/网页阅读工具。仓库提供技能指引，不附带通用代理宿主、搜索服务或一键执行新闻采集的 CLI。

## 只准备图片

复制 `skills/news-to-video/config/image-generation/connection.example.json` 为同目录 `connection.json`，填自己的服务地址与图片模型；复制 `api-key.example.json` 为 `api-key.local.json`，在本地填写 Key。二者已被 Git 排除，禁止把 Key 写入工程。

实际适配是 OpenAI 兼容 `POST /images/generations`、单张 `b64_json` 返回，不保证任意平台/模型兼容。渲染不会自动调用生图接口。

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
| 画面 | Node、固定版本 Remotion、浏览器、FFmpeg/FFprobe、中文字体；1920×1080 / 24 fps |
| Python | 依赖见 `assets/requirements.txt`；Qwen 独立环境见 `assets/requirements-qwen.txt` |
| 配音 | 固定 Qwen3-TTS 模型、CUDA、本地私有 B 参考及匹配哈希 |
| 配乐 | 技能内音乐池及清晰的署名输出 |
| 生图 | 可选；已有本地合法素材可直接使用 |

当前最关键的限制是：`voice-policy.json` 锁定私人参考，`setup_runtime.py` 不接受任意替代录音。本仓库不带参考音频、私有 profile 或模型权重。因而这不是陌生用户克隆后即可运行的完整配音包。公开声音适配见 ROADMAP 的 P0。

如果你已经具备匹配的授权私有环境，可参照技能的 [本地运行](../skills/news-to-video/references/local-runtime.md) 与 [Editorial 依赖](../skills/news-to-video/references/remotion-editorial.md)，使用自有 `runtime.json`：

```powershell
python './skills/news-to-video/scripts/check_runtime.py' --runtime '<your-private-runtime.json>'
python './skills/news-to-video/scripts/render.py' '<project.json>' `
  --runtime '<your-private-runtime.json>' --output './outputs/episode'
```

其中 `python` 必须指向准备好的渲染环境。输出可包括 MP4、SRT、voice.wav、mix.wav、分镜和验证记录；缓存与输出目录不纳入版本库。新机器安装尚未实测，不能将作者已有本机成功当作首装验证。

## 看测试与示例

`skills/news-to-video/assets/example-project.json` 是格式示例，不是可绕过声音环境限制的成片演示。具体可执行测试在技能 `scripts/test_*.py`，提示词回归规格在各自 `evals/`；二者不是同一种证据。
