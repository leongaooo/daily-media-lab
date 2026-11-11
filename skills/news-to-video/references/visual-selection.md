# 逐幕视觉选择与评分

用于新视频或用户明确要求改画面的项目；只改音乐、字幕错字等局部维护不重选画面。先读本文件，再写 image_prompt，不能先统一填“无需生成”。

已有剧本时按[剧本接入](script-handoff.md)将指定画面作为候选，评估其落地质量而非重新策划。保留候选比较与四项门槛；合格的指定画面未获最高分时用override_reason说明沿用剧本的依据，不为追求分数擅自换主体或改成文字。门槛未过时报告具体缺口，不能以剧本指定为由强行执行。

## 选择路径

1. 先写本幕观众需要看懂或感受到的一个目标。
2. 首尾主持可作为指定布局；每个正文镜头至少比较一个图片方案和一个纯文字/图解方案。图片方案包括核实照片、已有素材、原创生成示意，以及“场景图＋独立数字/SVG”；图片与图解不是互斥类别。
3. 每个方案检查四个门槛：facts（不虚构型号、现场和工程关系）；source（来源明确且用途可接受，生成图标注示意）；layout（能遵守字幕及人物保护区）；execution（素材可用，或生成配置及授权预算已落实）。未过门槛的候选仍记录，但不能选入执行。
4. 对候选给出四项0–5分和具体理由，计算加权分。评分是编辑判断，不是模型自动识图、事实核验或观看效果预测。无证据时不编造观众偏好数据。

| 项目 | 权重 | 0分 / 3分 / 5分锚点 |
|---|---|---|
| relevance 内容相关性 | 30% | 无关 / 能对应话题 / 直接对应本段对象与重点 |
| appeal 观赏与记忆价值 | 30% | 单调或干扰 / 有具体视觉锚点 / 主体鲜明、尺度或环境感有助记忆 |
| narrative 叙事推进 | 25% | 重复字幕 / 辅助解释 / 建立场景后自然推进到重点或细节 |
| readability 手机可读性 | 15% | 保护区冲突 / 手机尺寸可认 / 主次清楚且数字标签有独立空间 |

总分=sum(单项分/5×权重)，范围0–100。成本不与观赏性争权重，作为执行门槛与素材复用条件；不能因文字便宜默认文字。

5. 在合格候选中默认选最高分；最高分相同或差距不超过5分时，有具体对象/环境表达的图片候选优先。选择其他方案需填写 override_reason。阈值为初始编辑规则，尚未通过平台数据校准。
6. 没有可执行图片时，记录具体障碍及可补齐的方案。不能仅写“新闻是数字/流程，所以无需图片”。没有配置或授权时只给图片计划，不隐性调用付费接口。图解必要时保留，图片可以承担环境或先导镜头。
7. 整片回看：连续三幕只有文字或SVG时重新审查图片机会。没有张数或覆盖率硬配额；不得为分数凑图或把同一泛用机房图机械铺满。

## 工程与检查

新制作项目添加 visual_selection_version: 1，每个分镜添加 visual_selection：

```json
{"visual_selection":{"goal":"让观众感受云端基础设施规模，再读增长数字","selected":"scene-data","candidates":[{"id":"scene-data","uses_image":true,"gates":{"facts":true,"source":true,"layout":true,"execution":true},"scores":{"relevance":5,"appeal":4,"narrative":5,"readability":4},"reason":"非现场通用机房场景建立规模感，增长数字独立叠加"},{"id":"text","uses_image":false,"gates":{"facts":true,"source":true,"layout":true,"execution":true},"scores":{"relevance":5,"appeal":2,"narrative":2,"readability":5},"reason":"数字清楚但缺少对象和环境锚点"}]}}
```

首尾指定主持镜头可使用 `{"visual_selection":{"exempt_reason":"用户指定首尾主持，保留已认可人物"}}`，不扩展到普通正文。

执行 `scripts/score_visuals.py project.json --output visual-selection-report.json`。脚本不读密钥、不联网，不生成语义分数，只核算已填写评分、门槛、选中方案及遗漏；正文需提供两类候选。报告中 warning 提醒图片机会与连续单调镜头；错误需修正再生图/渲染。旧项目无 version 时独立评分命令输出 legacy-not-assessed，不谎称已评分。generate_images.py 与 render.py 对带 version 的新项目自动运行同一检查，并在读取连接/启动配音前拒绝缺失评估；旧项目无version时不强制追补评分，但仍只允许Editorial入口，旧布局必须显式迁移。

选中需生成的候选，再写 image_generation 并按 generated-images.md 执行；已有图片直接绑定路径。数字/拓扑独立合成；先看代表镜头再整片渲染。交付 visual-selection-report.json；production-plan.md 说明图片解决的理解/观赏问题。生成接口成功或全片解码不代表观赏性通过，最终仍需看图和发布反馈。
