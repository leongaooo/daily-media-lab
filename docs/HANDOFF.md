# 当前交接

更新：2026-11-12（Asia/Shanghai）。先读AGENTS和ROADMAP，任务状态仅在ROADMAP维护。

## 当前焦点

正式 `news-to-video` 技能已同步到仓库副本，登记为 REP-05。当前副本包含统一横屏 Editorial、固定底部字幕与 B 声、故事世界/连续镜头、导演契约、视觉评分和每期最多 10 次付费生图边界；合并保留仓库公开声音实现、显式选择和运行时匹配校验；56 项回归通过。实施与验证见 [技能同步记录](progress/2026-11-12-news-to-video-sync.md)。

公开声音REP-01已收口。维护者于本轮试听默认1.15倍样本后反馈“挺好的”，仅认可当前样本整体听感；原速、逐词和跨设备未单独验收。技术证据见[公开声音实施](progress/2026-11-11-public-voice.md)，样本见[试听入口](../examples/public-voice-smoke/README.md)。私人B声仍不公开，独立公开runtime不覆盖旧配置。

COM-04已发布三类Issue模板及五个社区任务入口（Issue #1—#5）。发布验证及实际链接见[社区启动记录](progress/2026-11-11-community-launch.md)与[贡献任务](community/README.md)。父任务不因发布Issue自动完成；认领和讨论在Issue，状态只在ROADMAP。

## 下一步

1. 检查实际Git状态与远程ref，按本轮技能同步记录确认 REP-05 发布结果。
2. 优先推进REP-02独立环境安装，或REP-03完整公开Web3示例；也可接手REP-04回归。先检查Issue认领，避免与贡献者重复实施。
3. 五个社区子任务均需实际证据才能标记完成。新机器失败也应保留环境/命令/修复记录；不以本机成功代替首装。
4. 旧Web3示例仍含私人B声ID；其有声成片及参考不提交。`outputs/rep-01-public-voice/`为忽略的本机短样片输出。
