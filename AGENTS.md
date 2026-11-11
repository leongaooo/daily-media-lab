# Daily Media Lab · 会话接续入口

目标：把有来源的技术资料制作成可检查、可交接的媒体内容。

新会话依次读取本文件、[唯一任务表](ROADMAP.md)、[当前交接](docs/HANDOFF.md)，再按任务 ID 读取相关实现与证据。

> 在 `D:\Dreamwork\daily-media-lab` 继续，读取 AGENTS、Roadmap 和 HANDOFF，推进下一个依赖已满足的任务。

## 工作规则

- 开始先检查 Git 状态、分支、远程，保留他人未提交改动；只处理本仓库。
- 先说明目标、行动计划、验收方法；在已有授权内推进，遇到缺少授权或关键决策再询问。
- ROADMAP 是唯一任务状态表；接手任务更新负责人及状态，优先推进依赖已满足的任务。
- 状态使用待开始、进行中、待验证、已完成、阻塞。只有实际验收证据齐备才能标记已完成；旧结果注明日期和来源。
- 每次实施写入 `docs/progress/YYYY-MM-DD-主题.md`，记录任务 ID、文件、命令/页面/样本、结果、限制和下一步，同步 HANDOFF。
- HANDOFF 仅指引当前焦点、未解决事项与下一步，不复制第二份任务状态表。
- 代码保持可读格式；注释解释约束、失败策略和协作边界，并与实现同步校准。
- 保留证据 ID、幕号、asset_id 与原始来源；生成图片不能冒充实拍或事实验证。
- 静态检查、单元测试、解码、浏览器看图、人耳试听、新机器安装、真实发布分别记录，不能相互替代。

## 发布边界

- Key、私人声音参考/文字、模型权重、运行时、客户资料和 `local-review/` 不纳入 Git；发布前检查索引与全部待推送历史。
- 自有代码及文档采用 MIT；第三方素材适用各自许可，见 THIRD_PARTY_NOTICES。维护者已于 2026-11-11 确认现有预览图片可公开分发；不能将此授权延伸到未来素材或私人声音。
- 私人声音仍无公开授权，禁止为了展示而提交有声样片。新素材逐项记录来源、许可和分发范围。
- GitHub 页面、远程 ref 与预览需要实际检查后再报告成功；不创建新凭据或削弱安全设置来绕过登录问题。
- `skills/` 是导出副本，不因此改写本机 `C:\Users\xc_sc\.agents` 或其维护源/治理规则。

## 实现与验证入口

- 采编：`skills/web3-tech-news-digest/`、`news/`；制作：`skills/news-to-video/`。实施前读对应 SKILL 与任务所需 reference。
- 示例：`examples/web3-daily/`；展示：`previews/`；发布记录：`docs/RELEASE_PREPARATION.md`。
- 制作回归：在 `skills/news-to-video` 执行 `python -m unittest discover -s scripts -p 'test_*.py'`。
- 文档检查本地链接、任务依赖、状态证据和 `git diff --check`；媒体改动再按范围验证解码、视觉与试听。
