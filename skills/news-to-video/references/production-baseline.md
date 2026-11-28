# 新闻视频制作基线

`scripts/production.py` 负责新一期与旧片复验。领域技能提供核验过的新闻及证据包。卡亚尼仅用于回归，用其实际成片核对原速冻结干声、短语义字幕、数据和镜头验收。每期按来源与故事选择对象、动作、阶段和空间关系。

## 日常制作

1. 通过 `episode.py` 将编辑包、计划和最终稿登记到新一期。编辑时保留新闻、证据与声明 ID，锁稿前切好语义短句。
2. 运行 `production.py new --episode EPISODE --project PROJECT --freeze --runtime RUNTIME`。入口读取已启用基线并按它选择声音，输出干声、实测 cue、冻结回执以及可复制到项目的 voice 配置。已有同一期合法干声可用同一冻结回执契约接入。
3. 以首版配音的实测 cue 编排 [关键幕集中审片](editorial-handoff.md#关键幕集中审片)，交付按成片顺序的连播、每幕标注构图和粗动态。影响判断的视听部分做到接近成片。按实际收到的反馈修订，用户明确通过当前审片版本后直接进入整期精修。保留字幕轨，按实测帧区间和证据封存 `narrative_manifest`，随后核对旁白、数据和动作。
4. 运行 `production.py new --episode EPISODE --project PROJECT --output OUTPUT --runtime RUNTIME`。入口复核锁稿、证据、基线的声音和短字幕条件，验证母版和完整解码，写出 MP4、SRT 及 production-receipt.json。下次新一期运行时重新读取已启用基线，节目和项目无需指定版本。

## 旧片复验

运行同一入口的 `revalidate`。使用原 episode 及新的可编辑项目和输出目录。入口核对旧成片内容身份。已启用基线默认适用。升级评审可使用候选工作区中随入口提供的文件，传入 `--baseline FILE --baseline-sha256 SHA256`。项目以原计划和证据为依托重剪，保留原期稿件、采用记录与交付。复验回执绑定该期 ID、revision、新项目、基线、干声、cue、封存母版回执和编码产物。

`render.py` 是合成后端。正式新作和复验从 `production.py` 进入。技术演示和预演可显式调用 `render.py --backend-only`，输出用于排查与短段审查。合成回执核验画幅、音频、字幕及解码。画面中的事实、切换节奏、读音和跨设备听感通过实际看片和试听判定。候选启用与公开同步走 `scripts/upgrade.py`，所需验收绑定已交付媒体的内容身份。
