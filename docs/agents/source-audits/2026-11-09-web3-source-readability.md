# Web3 来源可读性审计

检查日期：2026-11-09，Asia/Shanghai。工具：会话内web公开网页读取；没有绕过登录、付费墙或安装爬虫。检查14个候选入口，11个准入，3个暂不准入。准入不是跨日稳定性测量，也不等于独立事实复核。

同日增补：按用户“https://gcsa.com/forums 放入技能爬取资讯”请求，新增检查1入口及2篇不同正文，均通过公开网页读取。累计15候选、12准入、3暂不准入；原轮次结果保留，下述11入口分组数字仅描述原轮次。

所有链接与正文样本完整列于 [来源地图](../../../news/web3-tech-intelligence-sources.md)。下表记录实际可辨认正文，而非只凭HTTP成功、标题或摘要。

## 通过样本

| 入口 | 正文样本A与可读内容 | 正文样本B与可读内容 | 判定及限制 |
|---|---|---|---|
| Ethereum Blog | 2026-11-06 Glamsterdam 8037/8038：测试发现gas不变量兼容问题，征集排查，Hoodi延迟 | 2026-11-03数字公共基础设施：新网站、不丹身份案例与人道援助PoC | 入口＋两正文通过；PoC不能写成生产部署，EF不是独立客户验收 |
| EIP | EIP-1：提案流程、状态和格式要求 | ERC-4337：UserOperation、bundler、EntryPoint等规范及安全考虑 | 两正文均可读；规范持续演进，Created不是本期时效 |
| Bitcoin Core | 32.1：升级、兼容性与P2P等变更，有说明32.0未完全公告发布 | 31.2：维护修复和兼容性说明 | 两正文可读；正文未找到明确发布日期，本轮不将其认定近期新闻 |
| Solidity Blog | 2026-10-22优化器安全公告：受影响0.8.19—0.8.37、Yul配置条件及修复 | 同日0.8.38发布：修复、代码生成与保留标识符变化 | 两正文可读；这些是历史样本，不自动写入近期采用台账 |
| Solana News | 2026-11-05 Samsung Wallet：上线事件11月2日、美国资格与地区限制、托管及费用边界 | 2026-11-06十月回顾：协议与应用活动，含历史激活日期和指标链接 | 两正文可读；月报指标仍需追原方法，覆盖设备不等于用户 |
| OZ Contracts releases | v5.7.0：EIP712等破坏性变更、功能及修复 | v5.6.1：InteroperableAddress解析溢出修复 | 已打开两独立Tag正文；GitHub部分Assets/比较组件报错，不影响已读Release notes，不证明附件可下载 |
| Foundry releases | v1.9.0：调试器、fork复用、迁移注意与维护方基准 | 2026-11-08 nightly：Pre-release标记及状态机重构记录 | 已打开两独立Tag正文；nightly非稳定版，未执行基准或代码 |
| Hardhat releases | hardhat@3.21.2：项目模板依赖更新 | hardhat-slang@0.1.0-alpha.1：新编译器实验支持 | 已打开两不同包Tag正文，保留包边界；没有把alpha说成正式编译器支持 |
| viem releases | 2.57.17：交易填充错误重试hook、链专用修复等 | 2.57.16：RPC错误重试、ABI selector缓存、实验Gateway等 | 已打开两Tag正文；包标记和各能力实验状态分开，不声称本地验证 |
| ChainSecurity blog | 2026-10-13 Glamsterdam gas：状态gas与失败处理假设、当日提案状态 | 2026-10-21 MPC钱包：选择性中止与集成风险的披露说明 | 两正文可读；参与审计的研究方有项目关系，不能当完全独立的市场共识 |
| Base blog | 2026-11-05 Denim：200ms区块、Flashblocks迁移、入块与最终性区别 | Spiko案例：公司披露AUM/流量，明确全公司范围和2026年9月窗口 | 两正文可读；案例正文未单独列发布日期，入口11月4日只作入口日期，指标不算Base独占规模 |

GitHub列表内侧边锚点最初只回到同页，未计作两篇正文；之后打开`/releases/tag/...`才准入。保留这些限制以避免后续把“多次点列表”误记成多正文。

## 未准入与暂停

| 候选入口 | 实际结果 | 决定 |
|---|---|---|
| https://l2beat.com/scaling/summary | 工具报500并重定向https://ethbeat.org/scaling/summary不可访问；非可读研究正文 | 不准入，不从搜索摘要搬指标；不是对网站权威性的否定 |
| https://www.openzeppelin.com/news | 入口可读；Stellar confidential与ONCHAINID两篇首次曾返回正文页面，后续重开连续timeout（400），正文稳定抽测未通过 | 暂不准入此新闻栏目；不影响另行通过的Contracts Release入口。失败样本：https://www.openzeppelin.com/news/openzeppelin-brings-confidential-balances-and-transfers-to-stellar 与 https://www.openzeppelin.com/news/openzeppelin-and-t-rex-network-rebuild-onchainid-as-a-smart-account-for-regulated-assets |
| https://blog.oplabs.co/ → https://optimism.io/blog/ | 入口重定向后可读；Whitechain正文可读。Upgrade20首次返回正文页面，随后连续两次timeout（400） | 按连续失败规则暂停，固定来源地图不计该入口；可对当期具体可读原文现场核验。样本：https://optimism.io/blog/whitechain-moving-to-ethereum-layer-2-op-stack 与 https://optimism.io/blog/upgrade-20-preparing-the-fault-proof-system-for-interop |

## 覆盖判断与后续

11入口按Ethereum相关三入口合并、其余独立维护主体保守计算为9组；这是本轮维护来源分组，不是公司所有权或利益关系尽调结论。GitHub不是统一发布机构；Base相关与Coinbase材料遇到同一事件合并，ChainSecurity的EF合作内容不作独立事实的重复票数。

已覆盖协议/客户端、智能合约/安全、DApp SDK/钱包、L2/应用；非EVM以Solana为主，监管及独立统计研究仍有缺口。入口抽样完成不代表本期所有领域均存在近期新闻，也不代表已经完成日报的编辑选稿。

恢复暂停来源须重新完成入口和两篇正文检查。长期稳定性需跨日运行记录；本轮不计算可用率、不宣称长期稳定。样本正文不自动写入采用台账，只有最终交付时才记实际采用。

## GCSA增补核验

- 入口：https://gcsa.com/forums 。可读取“GCSA日常动态”、6条文章链接及各自日期；实际为机构动态栏目，不因URL含forums就认定开放社区论坛。
- 正文A：https://gcsa.com/forums/cr-longdation-gcsa-ai-cybersecurity-research-centre 。标题、2026-11-04日期及联合研究中心正文可读，包含未来联合研发方向；不能据此认定产品已落地。仅准入样本，未作为新闻采用。
- 正文B：https://gcsa.com/forums/gcsa-agent-cybergym-913 。标题、2026-08-29日期及基准说明正文可读；91.3%为GCSA自报。本次未核验评测平台、方法或复现，不能当独立性能证明；日期超出近期窗口。仅准入样本，未作为新闻采用。
- 结论：满足入口＋两不同正文可读的固定来源门槛；加入技能每期固定扫描，仍须按主题、日期和实质变化筛选，不保证每期入选。不新增爬虫程序、定时任务或未经确认的API/RSS，ledger及roadmap tracker不写入这些样本。
