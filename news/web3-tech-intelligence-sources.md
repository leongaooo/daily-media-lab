# Web3 技术与行业资讯来源地图

核验日期：2026-11-09，Asia/Shanghai。当前准入 **12个入口**；仅表示本轮公开网页的“入口＋至少两篇不同正文”抽样读取通过，不代表跨日稳定率、资料独立性或新闻时效。

## 使用规则

- 每期仍打开当篇原文，核对原始发布时间、版本、状态及适用范围。样本是读取能力证据，不自动成为近期资讯。
- 以规范、维护团队发布、版本记录和安全公告作关键事实依据；官方效果声明保留归属，必要时查项目使用、独立复现和方法。媒体及社交摘要只作线索。
- GitHub同一列表的锚点不是两篇正文；下表使用独立Release详情页。正文虽可读，Assets、比较、动态组件报错不代表相关附件已验证；Tag和签名不证明代码绝对安全。
- 同机构、多域名、联合稿及转载不算独立交叉验证。Ethereum Foundation博客、Solidity团队、EIP维护分别标主体，但本轮机构广度保守合并为一个Ethereum相关来源组；具体候选再核验维护及利益关系。
- 连续两次正文读取失败的入口暂停默认使用，复核“入口＋两正文”后恢复。未准入名单放审计文档，不用首页成功或搜索摘要补足数量。
- 只覆盖公开HTML文本；PDF、链上执行、动态图表、付费资料、登录资料和附件需要另行核验。新发现的原始材料可现场核验用于本期，成为固定入口仍须完成准入。

## 准入入口与样本

| 来源与维护主体 | 已测入口 | 范围和边界 | 两篇不同正文 |
|---|---|---|---|
| Ethereum Foundation Blog | https://blog.ethereum.org/ | 网络升级、研究与应用；公告与实网状态分开，不以路线图代替激活证据 | [Glamsterdam 8037/8038](https://blog.ethereum.org/2026/11/06/glamsterdam-8037-8038)、[数字公共基础设施](https://blog.ethereum.org/2026/11/03/digital-pub-infra) |
| Ethereum EIP/ERC维护社区 | https://eips.ethereum.org/ | 提案正文、状态、规范及安全考虑；Created不是近期发布，Final不是某链已激活 | [EIP-1](https://eips.ethereum.org/EIPS/eip-1)、[ERC-4337](https://eips.ethereum.org/EIPS/eip-4337) |
| Bitcoin Core维护团队 | https://bitcoincore.org/en/releases/ | 客户端兼容性、升级、修复；本轮样本正文未见明确发布日期，不凭列表排序认定新闻时间 | [32.1说明](https://bitcoincore.org/en/releases/32.1/)、[31.2说明](https://bitcoincore.org/en/releases/31.2/) |
| Solidity Team | https://www.soliditylang.org/blog/ | 编译器、语言路线、安全公告；版本、优化器和IR配置分别核对 | [Yul优化器公告](https://www.soliditylang.org/blog/2026/10/22/yul-optimizer-knowledge-base-stale-bookkeeping-bug/)、[0.8.38发布](https://www.soliditylang.org/blog/2026/10/22/solidity-0.8.38-release-announcement/) |
| Solana Foundation Media | https://solana.com/news | 非EVM协议、钱包、支付及机构应用；月报中的旧事件不是新进展，设备覆盖不等于活跃用户 | [Samsung Wallet](https://solana.com/news/samsung-wallet-solana)、[2026年10月回顾](https://solana.com/news/solana-ecosystem-roundup-october-2026) |
| OpenZeppelin Contracts维护团队 | https://github.com/OpenZeppelin/openzeppelin-contracts/releases | 合约库版本、破坏性变更及修复；审计另查版本和范围，不由库品牌推断安全 | [v5.7.0](https://github.com/OpenZeppelin/openzeppelin-contracts/releases/tag/v5.7.0)、[v5.6.1](https://github.com/OpenZeppelin/openzeppelin-contracts/releases/tag/v5.6.1) |
| Foundry维护团队 | https://github.com/foundry-rs/foundry/releases | Forge/Cast/Anvil、测试工具和迁移；nightly与稳定版分开，性能数值是维护方特定案例 | [v1.9.0](https://github.com/foundry-rs/foundry/releases/tag/v1.9.0)、[2026-11-08 nightly](https://github.com/foundry-rs/foundry/releases/tag/nightly-7bff443b45b93efecfeae1779404d12a20f4c225) |
| Nomic Foundation / Hardhat | https://github.com/NomicFoundation/hardhat/releases | 工具链与插件；同repo不同包版本不能互换，alpha插件不算Hardhat稳定版能力 | [Hardhat 3.21.2](https://github.com/NomicFoundation/hardhat/releases/tag/hardhat@3.21.2)、[slang alpha.1](https://github.com/NomicFoundation/hardhat/releases/tag/@nomicfoundation%2Fhardhat-slang@0.1.0-alpha.1) |
| wevm / viem维护团队 | https://github.com/wevm/viem/releases | DApp SDK、RPC、签名和链适配；核对包、Tag、链范围与breaking/patch实际影响 | [2.57.17](https://github.com/wevm/viem/releases/tag/viem@2.57.17)、[2.57.16](https://github.com/wevm/viem/releases/tag/viem@2.57.16) |
| ChainSecurity | https://www.chainsecurity.com/blog/index.html | 审计方原始技术研究和复盘；自身参与项目不能自动算无利益关系的独立证明，漏洞与资产规模不等于已损失 | [Glamsterdam gas](https://www.chainsecurity.com/blog/glamsterdam-gas/)、[MPC钱包研究](https://www.chainsecurity.com/blog/please-try-again-stealing-keys-from-mpc-wallets-via-selective-abort-attacks/) |
| Base Engineering / Coinbase相关发布 | https://www.base.org/blog | L2升级、RPC与应用案例；官方上线声明与独立节点观测分开，客户指标保留公司口径及时间 | [Denim](https://www.base.org/blog/denim)、[Spiko案例](https://www.base.org/customers/spiko) |

## 扫描和拓展

GCSA固定扫描入口为 https://gcsa.com/forums （页面名称“GCSA日常动态”）。跟随列表实际文章链接抓取标题、原始发布日期、正文、发布主体及原始证据链接；不猜测RSS/API，不扩展为全站爬取。仅选择Web3、智能合约、链上安全与数字金融实际应用相关的实质变化。自有公告是一手披露，转载追原文；自报基准、排名和安全效果保留归属并补查评测方法与独立证据。无产品进展的合作、研究中心成立和一般网络安全宣传不独立入选；同机构的主站、媒体站与联合稿不重复计独立来源。读取失败按既有暂停规则处理。

| 来源与维护主体 | 已测入口 | 范围和边界 | 两篇不同正文 |
|---|---|---|---|
| GCSA / Global Cybersecurity Alliance | https://gcsa.com/forums | Web3与数字金融安全相关原始披露及候选线索；页面是机构日常动态，不按开放社区论坛认定；可读不代表主张已获独立验证 | [研究中心公告（2026-11-04）](https://gcsa.com/forums/cr-longdation-gcsa-ai-cybersecurity-research-centre)、[CyberGym自报成绩（2026-08-29）](https://gcsa.com/forums/gcsa-agent-cybergym-913) |

标准日报尝试至少8入口、5家独立机构、4条领域线，候选中含至少3个一手发布主体；只记录实际成功覆盖。当前来源偏开发与协议，监管、标准以外的行业应用、其他非EVM和独立量化研究覆盖仍需按候选补查，不能声称全行业覆盖。

建议扫描顺序为协议/路线图、合约/安全、工具/钱包、L2/应用。非EVM和行业应用根据实质新闻选择，不按链配额。进入主新闻的每个论断须找到正文、日期、状态与适用边界；没有新变化宁可少报。

详细准入与失败证据见 [2026-11-09审计](../docs/agents/source-audits/2026-11-09-web3-source-readability.md)。本文件不存采用记录；新闻和路线图分别写入独立台账。
