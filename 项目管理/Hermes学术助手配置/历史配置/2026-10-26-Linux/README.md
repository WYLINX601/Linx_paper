---
type: infrastructure-guide
status: configured
updated: 2026-10-26
---

# Hermes 学术助手使用说明

Linux 的独立 `academic` 档案已建立，桌面显示为 **学术助手**。Mac 的 Paper 库继续是研究资料与正式成果主源；Linux 保存会话、运行记忆、技能及计算工作副本。本次没有迁移或改写研究数据库，也没有搬走 Mac 资料。

在 Hermes 桌面左下方选择 Linux 网关下的“学术助手”，新建会话即可。已留下一条 **只读核对学术档案配置** 验收会话，模型为 `openai-codex / gpt-5.6-luna`，使用原有登录机制，没有复制认证令牌。

可直接说：“读取最新项目上下文，继续讨论 V01 的候选规则”，或“通过 Zotero 阅读某条目的 PDF 第几页，并保留来源和页码”。助手会先读取 Mac 的项目规则、入口和上下文，再按任务取用主源。

详细结果见 [验收清单](验收清单.md)、[技能迁移清单](技能迁移清单.md) 与 [恢复说明](恢复说明.md)。这些文件是配置与验收记录，不是研究成果或研究有效性证明。

## 工作入口

| 项目 | 位置或方式 |
| --- | --- |
| Linux 学术档案 | `/home/linx/.hermes/profiles/academic` |
| Linux 运算工作区 | `/home/linx/.hermes/profiles/academic/workspace` |
| Mac 研究主源 | `/Users/wangyuelin/Desktop/Obsidian/Paper` |
| Mac SSH 入口 | Linux 上的 `mac-agent`，走 Tailscale；同局域网也可继续使用它 |
| Linux 命令行入口 | `/home/linx/.local/bin/hermes -p academic`，或已有 `academic` 包装入口 |
| 项目启动技能 | `academic-workspace` 自动加载；每项 Paper 任务先运行 `mac-paper status` 与 `mac-paper context` |
| 学术身份与运行记忆 | 档案内 `SOUL.md`、`memories/USER.md`、`memories/MEMORY.md` |
| 可追溯验收证据 | 档案内 `verification/`；本目录 `evidence/` 保留主要脱敏结果 |

`kahn`、`builder`、`coo` 均保留，其原有配置、身份说明与元数据校验值未变，网关仍运行。没有全局卸载 Codex 插件，也没有把无关账户、旧会话或其他项目记忆导入学术档案。

## 文件写回

学术终端在 Linux。本机 `/Users/...` 路径必须通过 SSH 操作，不能当作 Linux 路径。每次命令可设置：

```sh
export PATH=/home/linx/.hermes/profiles/academic/bin:/home/linx/.hermes/profiles/academic/runtime/venv/bin:/home/linx/.local/bin:$PATH
mac-paper status
mac-paper context
mac-paper read context/PROJECT_CONTEXT.md
mac-paper search 'BOT基准'
```

`mac-paper read` 返回内容与 SHA-256。覆盖时传入刚读到的 `--expected-sha256`；新文件必须传入 `--expect-missing`。`write` 接收标准输入，`upload LOCAL REMOTE` 传输文件，`download REMOTE LOCAL` 会同时生成来源、时间和摘要的 `.provenance.json`。完整参数以 `mac-paper --help` 为准。

既有文件覆盖前保存到 Mac 的 `.hermes-academic-backups/`，写完回读验证。该目录已加入 Git 忽略。桥接自己的并发写入会串行化，旧摘要会被拒绝；Obsidian 等普通编辑器不参与该锁，所以同时编辑时仍须重新读取、核对和合并。SSH 中断时若写入结果不明，先回读后重试。

Mac 专用命令用 `mac-run -- COMMAND ARG...`；draw.io 导出复用 Mac 已安装应用。SSH 使用现有普通用户权限；项目目录约定不是系统级沙箱。

## 文献、Obsidian 与图谱

- **Zotero**：通过 SSH 在 Mac 启动既有本地 MCP，读取 Mac 文献库与 PDF。学术档案专用启动文件是 `/Users/wangyuelin/.local/share/hermes-academic/zotero_compat.py`。现有 `pdf-inspector 0.2.6` 对两份有效 PDF 报解析错误，因此增加仅本进程的 PyMuPDF 回退；原 Zotero 安装、原 PDF 和 Codex 启动配置不变。返回结果保留条目键与页码，并标注回退。纯文本不代表图表版式正确，也不执行 OCR。升级 Zotero MCP、pdf-inspector 或 PyMuPDF 后须重新核对兼容层。
- **Obsidian**：安装官方仓库稳定版 **Local REST API with MCP 5.5.2**，保留 Simple Mind Map。HTTP 只监听 Mac `127.0.0.1:27123`，Linux 专用 SSH 隧道映射为 `127.0.0.1:37123`，MCP 路径 `/mcp/`。当前笔记、搜索、打开文件、命令等走该 MCP；正式文件覆盖仍优先使用带备份的桥接。API 自身也支持版本条件写入。
- **Neo4j**：复用 Linux `/home/linx/.local/share/neo4j-paper/tools/MCP启动.py`。实际暴露 `get-schema`、`read-cypher`、`write-cypher`；它不是只读权限配置。本次仅调用前两者。案例 JSON 仍为维护主源，数据库仅为投影；后续变更须符合任务授权、现状核对和可恢复要求。

API 密钥仅保存在 Mac 插件受限配置及 Linux 档案 `.env`，文件权限均为 `0600`，不放入本说明、笔记或验收日志。

隧道服务为 `hermes-academic-obsidian-tunnel.service`，已启用用户级自启动及失败重连。Mac 离线、睡眠、Tailscale 断开，或 Zotero/Obsidian 未运行时，相应功能不可用；恢复后重新读主源。没有修改 Mac 睡眠设置。

## 技能与依赖

迁入 **28 个本地学术目录 + 3 个文档技能**，保留 `nature-shared` 共享依赖。加上项目桥接技能和 Hermes 必要核心技能，共发现 **33 项**。文献方法、来源规则、模板与必要脚本保留；Codex 专属在线编辑改为本地文件生成及渲染检查。更新采用显式迁移，已关闭自动后台技能改写和创建提示。

Python 使用档案内 `runtime/venv/bin/python`；Node 使用现有用户运行时。Word、PPT、表格使用 Python/Node 库与用户级 LibreOffice **26.2.6.3**；程序依赖在 `opt/libreoffice/`，运行包装及配置在 `bin/`，没有修改系统 LibreOffice。

网页检索与浏览器已通过实际对话验收。转录等需要额外供应商密钥的能力仅迁移技能，未复制凭证或发送音频。OpenReview、Scopus 等特定来源及可选 Bayesian/Plotly 静态导出环境，须按具体技能补齐依赖/授权后再用，不能从技能可见推断服务已接通。

## 维护检查

以下命令在 Linux 执行：

```sh
/home/linx/.local/bin/hermes -p academic gateway status
systemctl --user status hermes-academic-obsidian-tunnel.service
/home/linx/.hermes/profiles/academic/bin/mac-paper status
/home/linx/.local/bin/hermes -p academic tools list --platform api_server
```

修改学术 MCP 配置后，空闲时执行 `hermes -p academic gateway restart`，仅重载常驻网关中的该档案。桌面还可能持有独立的 SSH 后端连接；本次确认单独重载网关和新建会话不足以替换它的旧 MCP 子进程，须让桌面重建该连接后再验收。桌面菜单的“重启共享网关”会影响多个档案，操作前核对活动任务。运行中的旧连接不会仅因配置文件变更立即换用新进程。

配置依据：[Hermes profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)、[MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)、[skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)、[Obsidian 插件 5.5.2 发布](https://github.com/coddingtonbear/obsidian-local-rest-api/releases/tag/5.5.2)。版本与可用性以上述机器的本次实际验收为准。
