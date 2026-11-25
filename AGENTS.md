# Daily Media Lab · 会话接续入口

目标：把有来源的技术资料制作成可检查、可交接的媒体内容。

新会话依次读取本文件、[唯一任务表](ROADMAP.md)、[当前交接](docs/HANDOFF.md)，再按任务 ID 读取相关实现与证据。

> 在当前仓库根目录继续，读取 AGENTS、ROADMAP 和 HANDOFF，推进下一个依赖已满足的任务。

## 工作规则

- 开始先检查 Git 状态、分支、远程，保留他人未提交改动；只处理本仓库。
- 先说明目标、行动计划、验收方法；在已有授权内推进，遇到缺少授权或关键决策再询问。
- ROADMAP 是唯一任务状态表；接手任务更新负责人及状态，优先推进依赖已满足的任务。
- 状态使用待开始、进行中、待验证、已完成、阻塞。只有实际验收证据齐备才能标记已完成；旧结果注明日期和来源。
- 每次实施写入 `docs/progress/YYYY-MM-DD-主题.md`，记录任务 ID、文件、命令/页面/样本、结果、限制和下一步，同步 HANDOFF。
- HANDOFF 仅指引当前焦点、未解决事项与下一步，不复制第二份任务状态表。
- 每次形成可公开的里程碑，在同一批完成 `README.md` 与 `README.en.md` 的成果介绍更新。把最新获验收且具备公开分发权限的代表性预览放到成果区，标明日期、成果范围与素材身份，并链接对应里程碑证据。授权仅覆盖文字时使用文字介绍与可公开证据。收尾检查双语内容和媒体引用，推送后验证 GitHub 实际页面及预览加载。
- 代码保持可读格式；注释解释约束、失败策略和协作边界，并与实现同步校准。
- 保留证据 ID、幕号、asset_id 与原始来源；生成图片不能冒充实拍或事实验证。
- 静态检查、单元测试、解码、浏览器看图、人耳试听、新机器安装、真实发布分别记录，不能相互替代。
- 同一任务由协调者分配文件与共享协议写者，保留并发改动。重型测试、TTS、GPU和渲染同时最多一个；不能让子任务各自启动重任务。
- 三个媒体技能任一内容的新批更新，在第一次写入前询问是否同步维护者配置的公开目标；同批已有明确答复沿用，正常采编、采用登记和媒体生成不触发。遵循[媒体维护约定](skills/news-to-video/references/media-maintenance.md)，本批同步答复不是永久授权。

## 发布边界

- Key、私人声音参考/文字、模型权重、运行时、客户资料和 `local-review/` 不纳入 Git；发布前检查索引与全部待推送历史。
- 自有代码及文档采用 MIT；第三方素材适用各自许可，见 THIRD_PARTY_NOTICES。维护者已于 2026-11-11 确认现有预览图片可公开分发；不能将此授权延伸到未来素材或私人声音。
- 私人声音仍无公开授权，禁止为了展示而提交有声样片。新素材逐项记录来源、许可和分发范围。
- GitHub 页面、远程 ref 与预览需要实际检查后再报告成功；不创建新凭据或削弱安全设置来绕过登录问题。
- `skills/` 是公开导出副本；canonical维护源与同步目标由维护者配置，不能据此反向改写其私人配置或治理规则。
- 公开项目的新配音显式选择 `qwen-uncle-fu-v1` 与匹配的独立runtime；已有合法最终单声道干声用 `external_final`。保留公开声音policy、setup、身份校验与专有测试，不将默认B声强写进公开项目，不自动回退音色。
- `.blend`、贴图、声音、字幕及母版各自核验来源与分发权限；技术通过、视觉被拒绝、返修、试听与用户认可分别保留。被用户拒绝的样片不能成为质量基准，也不因可播放而标为已认可。

## 实现与验证入口

- 近期IDC／Web3成片总入口：[news-to-video](skills/news-to-video/SKILL.md)。只按需加载[IDC](skills/idc-compute-news-digest/SKILL.md)或[Web3](skills/web3-tech-news-digest/SKILL.md)采编规范；领域独立调用保留剧本／明确文字版，混合一期才加载两领域。领域返回证据编辑包，不递归启动新制作任务。
- 来源与采用：`news/`的领域来源、独立ledger与Web3 tracker。内部包、草案、冻结稿不提前采用；已有台账／tracker不因同步重置，缺表头只能在核实空模板时定向补齐，不能覆盖用户历史。
- 编排：[editorial-handoff](skills/news-to-video/references/editorial-handoff.md)与`skills/news-to-video/scripts/episode.py`。新稿可编辑至锁定；确认稿受内容身份保护。阶段与实际交付分开，复核绑定实际合成输入；台账先写而回执失败时幂等恢复，混合领域逐侧提交。
- 三维与音频：[Blender交接](skills/news-to-video/references/blender-handoff.md)。真实`.blend`与依赖→`blender_render.py`→母版核验→`check_runtime.py --project`→`render.py`。完整镜头采用独立narrative_version=1，旧v1/v2图解兼容；冻结最终音频跳过TTS／再变速／再降噪／重拼。没有TTS的环境不要调用省略--project的默认声音检查。
- 示例：[最小合成输入](examples/three-media-minimal/README.md)、[公开声音短样本](examples/public-voice-smoke/README.md)与历史`examples/web3-daily/`。最小JSON不是真实新闻成片，旧私声样例不能充当公开声音复现。展示：`previews/`；发布记录：`docs/RELEASE_PREPARATION.md`。
- 制作回归：在 `skills/news-to-video` 执行 `python -m unittest discover -s scripts -p 'test_*.py'`。
- 文档检查本地链接、任务依赖、状态证据和 `git diff --check`；媒体改动再按范围验证解码、视觉与试听。
