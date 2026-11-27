# 日更编辑工作流

这份契约把《Daily Media Lab 下一阶段总方案》的日更约束落到 `news-to-video` 的正常入口。它只记录编辑选择和人工决策，不自动采编网页、判断受众或替用户发布。

## 每期入口

每个新的 IDC／算力日更先建立一份 `daily_editorial` 计划，再把它交给 `episode.py init --editorial-plan`。领域技能仍负责来源、日期、阶段、指标口径、七日去重和证据编辑包。日更计划负责把一个已核验候选变成可执行的节目选择。

```powershell
python scripts/daily_editorial.py validate-plan editorial-plan.json
python scripts/episode.py init episode.json `
  --episode-id idc-20261128-example `
  --request "近期IDC资讯成片" `
  --package source/editorial-package.json `
  --editorial-plan editorial-plan.json
```

`episode.json` 保存计划文件的内容身份。计划文件变化时，`episode.py verify` 会停止恢复，要求重新确认当前节目修订。旧节目和明确的 `legacy` 兼容路径不被追溯改写。

## 计划必须回答的问题

计划至少包含以下内容。

- 一个观众问题和一句可复述的观众收获。
- 一个探索切入点，使用 `engineering_progress`、`technology_operations` 或 `procurement_supply_chain`。
- 一种表达方式，使用 `fact`、`why`、`how_to`、`comparison`、`choice` 或 `follow_up`。
- 一个可以直接交付的抖音标题。标题准确对应片中答案，不使用悬念、夸张比较或空泛判断。
- 价值意图。五个价值方向分别写重点、辅助或本期不主张的理由，并写栏目识别线索如何沿用、调整或新建。
- 文字、画面、声音和结构各自承担的职责。新增事实必须回到编辑包的主张和证据。
- 可选的一个互动动作。可以邀请点赞、选择后续问题、补充工作经验或提供可核验线索。没有值得回答的动作时使用 `none`。
- `review_policy: "user_requested_only"`。只有用户明确说“复盘”才读取抖音导出、评论或投入记录。

日更先选一个问题讲完整。其他有证据、但本期没有足够篇幅或制作余量的问题放入 `follow_up_questions`，不能在片中暗示已经回答。

## 方向研讨

观众建议进入单独的方向板，不直接改写日更计划。每条建议保留原意、提出时的作品和工作场景、可核对的证据机会及人工决定。方向研讨委员会只使用以下四种状态。

| 状态 | 含义 |
| --- | --- |
| `proposed` | 已登记，尚未决定是否投入 |
| `accepted` | 证据和栏目方向足够，允许进入一期独立内容 |
| `revise_after_evidence` | 方向有价值，先补指定证据再议 |
| `parked` | 当前证据、用途或制作成本不足，保留原建议 |

每个决定必须写理由。`accepted` 只代表进入一期独立内容候选，后续是否做成系列要等到实际追问、回访或工作使用反馈出现。方向板可以用 `daily_editorial.validate_suggestion` 做结构检查，委员会的判断仍由人工完成。

## 手动复盘

复盘记录必须包含用户明确发起的时间、导出文件身份、匹配作品和发布时间范围、观察到的具体行为、未知项和下一次复评条件。比较优先选择相近题材、相近时长和相近发布后时点。播放、留存、点赞、收藏、分享和关注只说明对应作品在对应条件下的行为，不能单独证明理解、审美、情绪或栏目记忆。

```powershell
python scripts/daily_editorial.py validate-review review.json
```

没有“复盘”请求时，不读取私人抖音导出，不创建定时复盘，不把日更入口的技术回执当作观众反馈。

## 方案与制作回执的关系

日更计划是编辑层输入。`episode.py` 继续负责证据包身份、稿件锁定、音频和视觉阶段、预演回执、正式复核、交付和幂等采用。计划中的标题和互动文案需要在实际交付消息中一起提供，互动文案是可选的编辑提示，不是自动发布动作。

公开新稿显式选择公开声音或合法 `external_final`，沿用 1920×1080 横屏、短句字幕和现有母版契约。公开副本不包含维护者私人声音、参考文字、权重、运行时和账号数据。
