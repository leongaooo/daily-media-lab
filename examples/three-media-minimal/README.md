# 三媒体最小公开格式示例

这是合成资料，不是近期新闻、部署证据或Blender叙事成片。example.test为保留测试域名，没有访问原文或采用新闻的声明。此目录只含自写文本／JSON，没有音频、视频、私人参考、权重、runtime或密钥。

## 文件与身份

- evidence.json：v1领域编辑包，包含新闻／主张／证据／段落ID和清楚的合成身份；只能检验结构与引用，不能当作事实核验。
- episode-request.json：可移植节目输入说明，不是已完成episode回执。真正episode.json含当前工作区实际文件身份，按下方命令在outputs内创建，不能提交作者绝对路径或伪造完成哈希。
- paragraphs.json：内部新稿输入，保留claim_ids；可在editorial_locked前编辑。已有确认稿不应用本例的可改稿规则。
- project.json：显式选择公开qwen-uncle-fu-v1的旧图解兼容最小项目，音乐关闭；没有运行输出。它用于说明节目到媒体输入映射，不冒充完整Blender示例，也不包含假母版／伪cue。

## 只检查结构与编排

在仓库根目录运行，准备Python即可；episode工具仅依赖标准库。下列命令不TTS、不GPU、不Blender、不生成媒体、不联网和不写真实ledger。

```powershell
$example = './examples/three-media-minimal'
$request = Get-Content "$example/episode-request.json" -Raw | ConvertFrom-Json
python './skills/news-to-video/scripts/episode.py' validate-package "$example/evidence.json"
python './skills/news-to-video/scripts/episode.py' init './outputs/three-media-minimal/episode.json' `
  --episode-id $request.episode_id --request $request.request --package "$example/evidence.json"
python './skills/news-to-video/scripts/episode.py' draft './outputs/three-media-minimal/episode.json' `
  --revision 1 --paragraphs "$example/paragraphs.json" --output './outputs/three-media-minimal/draft.json'
python './skills/news-to-video/scripts/episode.py' stage './outputs/three-media-minimal/episode.json' `
  --revision 2 --name editorial_locked --output './outputs/three-media-minimal/draft.json' `
  --evidence '合成格式练习：仅确认ID引用与草案内容，不声明真实新闻核验'
python './skills/news-to-video/scripts/episode.py' verify './outputs/three-media-minimal/episode.json'
```

init拒绝覆盖已有episode；重复练习用新的输出目录，真实中断则读取现有revision继续，不能把命令中的固定1／2当所有项目的正确revision。不要对本样例运行deliver/adopt，它不是实际新闻或媒体交付。

## 明确需要声音／视频时

仅在用户实际要求制作并完成自己的公开运行环境后，才用project.json运行render.py；本次格式练习不执行这一步：

```powershell
python './skills/news-to-video/scripts/render.py' './examples/three-media-minimal/project.json' `
  --runtime '<your-public-voice-runtime.json>' --output './outputs/three-media-minimal-media'
```

运行环境按 [公开声音配置](../../skills/news-to-video/references/public-voice.md) 独立setup。project显式qwen-uncle-fu-v1，不能被默认B声替换；匹配失败停止，绝不寻找或提交私人参考。需要真实新闻时先替换合成证据、核验来源及日期，不把这段文案当真实采编示例。格式校验不等于声音好听、完整解码或新机器安装通过。

## 实跑作业预检

可用同一合成模板与两秒本地静音验证作业预检、字幕和完整解码。命令需要已安装的合成运行环境。下列路径只作示例，换用尚未创建的作业目录。

```powershell
$job = './outputs/jobs/2026-11-27/storage-smoke'
python examples/three-media-minimal/prepare_storage_smoke.py $job
python skills/news-to-video/scripts/render.py "$job/project.json" --output "$job/output" --min-free-bytes 536870912 --runtime '<render-only-runtime.json>'
```

确认输出含 48 帧、`validation.json` 和 `storage-preflight-*.json`。静音在本机生成，随代码分发的是 MIT 源码和合成文字。

若已有合法最终单声道干声，按 [Blender／external_final交接](../../skills/news-to-video/references/blender-handoff.md) 提供真实hash/sample_rate/samples/channels/processing_identity及准确cue，播放1.0；本目录不伪造这些字段，不用测试音冒充口播。新的Blender项目还需真实可编辑.blend、依赖与有效PNG母版，采用narrative_version=1，不套本例旧图解槽。

本样例使用项目MIT文本／代码许可，不引入第三方媒体；官方公开声音模型另遵守其原许可。实际运行结果与未验收层见 [本批进度](../../docs/progress/2026-11-20-three-media-blender.md)。

## 画内数据与同画面对照

通过源代码生成两段合成审查片。120 kW 徽标和连线跟随模块沿路径进入接收台，接入待核状态在停稳后出现。带字幕审查版用合成文本覆盖底部 y904–1080 区域，静音对照保留主体、路径和数据牌。两份示例均无音轨。需要带 libass 和 libx264 的 FFmpeg。

```powershell
python examples/three-media-minimal/render_integrated_visuals.py './outputs/integrated-visuals' --ffmpeg '<ffmpeg>'
```

依次抽查 0.25、1.5 和 3.25 秒。三个时点分别覆盖出发前、运输中和落位后。作业回收入口的隔离回归用 `python -m unittest discover -s skills/news-to-video/scripts -p test_cross_day_storage.py -v` 检查。该回归只在临时夹具上删除，并检查锁、同日和未确认目录的保护。
