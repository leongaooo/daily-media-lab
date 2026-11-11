# 零预算成品音乐池

当前保留 3 首 Kevin MacLeod 在 incompetech 官方站发布的原始 MP3：Voice Over Under、Tech Live、Inspired。按官方页面的 CC BY 4.0 条款免费使用，需署名。`manifest.json` 是素材与授权记录的入口；未指定曲目时由这三首中随机选择。不要把“免费”理解为无需保留作者与许可证信息。

| 曲目 | 候选方向 | 作者描述依据 |
|---|---|---|
| Voice Over Under | 新闻、资讯、连续口播 | 明确为大量说话的新闻和评测片段设计，便于循环 |
| Tech Live | 节奏稍快的新闻与评测 | 明确定位为 review / interview segments 的背景 |
| Inspired | 产业建设、企业与工程解读 | 作者明确列举 corporate films / intricate industrial processes |

标签是基于作者描述、乐器和用途做出的编辑初选，不是人耳试听结论。全部文件完成 FFmpeg 全量解码；音乐本身的风格、混音后的舒适度与手机外放效果仍应试听确认。

`evidence/` 保存官方曲库 JSON、曲目页面、免费授权页面、Creative Commons 4.0 说明页、每首曲目的官方目录条目及解码日志。页面使用 JavaScript 从 `official-pieces.json` 渲染曲目信息，因此同时保存了页面模板和目录条目。

制作输出应复制所用曲目的 `attribution`，并根据实际处理追加改动说明，例如“节选并与口播混音；调整音量、淡入淡出及人声避让”。可放在发布文案、片尾或能够合理承载署名的位置；单独保存在本地工程文件里不等于已向成片观众提供署名。不要移除许可证链接，也不要把此素材池当作对平台 Content ID 情况的保证。

原始 MP3 未转码、未调速、未做音量处理。混音与循环由制作流程负责。增加曲目时保持作者、官方来源、授权证据、文件哈希与实际改动说明可追溯。
