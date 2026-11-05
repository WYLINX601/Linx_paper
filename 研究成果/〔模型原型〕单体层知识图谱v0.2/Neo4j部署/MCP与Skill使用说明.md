# Neo4j MCP 与三个 Skill 的接入记录

日期：2026-10-22。本轮完成三个skill安装、官方MCP接入，以及真实数据库读取测试。当前采用只读模式，未重新导入或修改研究图谱。

## 已安装内容

| 组件 | 版本／位置 | 本轮用途 |
|---|---|---|
| neo4j-mcp-skill | 1.0.2，`~/.codex/skills/neo4j-mcp-skill` | 配置连接、验证协议、读取结构 |
| neo4j-modeling-skill | 1.0.7，`~/.codex/skills/neo4j-modeling-skill` | 先读取实际图结构、唯一约束和索引 |
| neo4j-import-skill | 1.0.11，`~/.codex/skills/neo4j-import-skill` | 检查已有导入的数量、标识、索引状态；没有执行新导入 |
| 官方 Neo4j MCP | v1.6.1，Linux用户目录 | 提供 `get-schema` 和 `read-cypher` |
| APOC Core | 5.26.32，Neo4j发行包自带 | 只启用结构元信息过程和版本函数 |

Skills来自 [neo4j-contrib/neo4j-skills](https://github.com/neo4j-contrib/neo4j-skills)，固定提交 `39247b9c4ab20062aefd1cfe83c040167ef9ee83`，保留上游内容。本轮没有安装Cypher 25 skill或其他未选择的skill。三个技能包合计约59KB。

MCP来自 [neo4j/mcp v1.6.1](https://github.com/neo4j/mcp/releases/tag/v1.6.1)，Linux压缩包约8.4MB，已核对官方发布的SHA-256。完整文件指纹和配置见 [安装记录](验收/MCP安装记录.json)。

## 怎样使用

可以直接向Codex提出研究问题，例如：

- “用Neo4j查询文献案例和演示分别有哪些实体。”
- “查看堂屋与前廊之间的关系，列出界面、通行情境和证据。”
- “周湖1号的屋面判断有什么冲突？分别依据哪些证据？”
- “周湖8号为什么没有满足原型判据？”
- “按照建模skill检查现有图谱，先给建议，不修改数据。”

新安装的skill会在下一轮供系统发现。本轮已直接读取三个SKILL.md并按其相关流程完成操作。MCP已登记到Codex全局配置，名字为 `neo4j-paper`；当前这轮的工具目录未热加载它，因此本轮测试通过**同一SSH命令、实际官方MCP进程及JSON-RPC协议**完成，不是以HTTP脚本冒充MCP测试。若后续对话仍看不到它，可在MCP服务器设置里重启该连接；必要时重开Codex。

连接路径为：Mac Codex → SSH标准输入输出 → Linux官方MCP → 现有Neo4j。保持Linux开机、Tailscale在线即可。MCP随连接启动，不增设HTTP监听端口；数据库密码由Linux私有文件读取，不写入Codex配置或Obsidian。遥测已关闭。

## 本次实际使用结果

[MCP实际查询记录](验收/MCP实际查询.json)保存全部11次调用的原始结果：

| 检查 | 结果 |
|---|---|
| 连接与结构 | 返回connected；get-schema成功 |
| 唯一约束 | `KGItem(uid)`唯一约束存在 |
| 索引 | 3项均ONLINE、100% |
| 数据集隔离 | 文献14个领域实体、演示7个 |
| 记录数量 | 94总节点、55条断言、4条分类 |
| 堂屋—前廊 | 两条有向通行断言；保留开放分界与“正常时段、可独立行走成人、普通步行”情境 |
| 文献中的通行 | 0条，未从演示补造文献事实 |
| 屋面争议 | 原值和disputed状态保留；支持、冲突证据分别返回 |
| 分类 | 两条criteria_match、两条criteria_not_match，判据完整返回 |
| UID | 未检出缺失或重复 |

[接入后完整性核验](验收/MCP接入后完整性/最近运行.json)另通过现有验证器核对全部94节点的属性、标签和216条关系，与原始JSON保持一致。它是额外的完整性校验，不替代上面的MCP协议测试。

本次只完成现有模型的结构检查，没有开展新的学术模型评估，也未新增建筑事实。

## 版本与研究约束

上游skill是通用操作资料，需要结合本项目使用：

1. 服务器保持 **Neo4j 5.26.32 Community**。部分上游示例使用Cypher 25、2026功能或Enterprise约束；不能直接复制，也不因示例而升级数据库。
2. 本机为单机Community部署。导入skill中的集群PRIMARY检查不适用于这里；以实际部署和可写性核查为准。
3. `KGItem`、`Entity`是辅助标签，同时存在Dwelling、Space、Interface等具体类别。上游命名风格建议不能成为删除这些标签或批量改名现有关系的理由。
4. 本项目JSON是维护源。当前kgv02命名空间绑定源文件哈希；后续导入必须依照既有版本迁移规则，不能绕开验证器直接覆盖。
5. 文献、演示、分类判断、支持证据和冲突证据继续分开。软件操作skill不能代替建筑学理论或原文证据。
6. 原始PDF与图片仍在Mac资料库。MCP能够查询其引用与证据记录，不代表它自动读过论文全文。
7. v1.6.1实际启动参数使用 `NEO4J_MCP_*`；skill中的旧变量仍在其示例中，本轮按实际程序帮助完成适配。真实工具参数是 `query` 和 `params`，以工具发现返回的schema为准。

## 权限与变更记录

APOC配置曾被自动审批拒绝。用户随后明确同意“允许最小权限配置并重启”，才执行以下配置：

```text
dbms.security.procedures.allowlist=apoc.meta.schema,apoc.version
dbms.security.procedures.unrestricted=apoc.meta.schema
```

配置备份为Linux的 `~/.config/neo4j-paper/conf/neo4j.conf.before-mcp-20261022`；已校验配置、重启并查询验证。仅启用这一元信息过程，没有启用APOC文件导入、网络加载等功能。对应 [官方MCP源码](https://github.com/neo4j/mcp/blob/v1.6.1/internal/tools/cypher/get_schema_handler.go) 仅调用 `apoc.meta.schema`；[官方过程文档](https://neo4j.com/docs/apoc/current/overview/apoc.meta/apoc.meta.schema/)说明自托管实例须解限该过程。

写入权限是另一个审批事项：自动审批拒绝持久开放 `write-cypher`，用户尚未对该项单独授权。因此服务端设置 `NEO4J_MCP_READ_ONLY=true`，Codex只允许 `get-schema`、`read-cypher`；本轮实际工具清单也只有这两项。后续需要新增、修改、删除数据时，须先明确授权写入范围，再启用对应能力并执行可追溯迁移。

Codex配置变更前已在Mac的 `~/.config/neo4j-paper/` 留存私有备份，其他MCP与设置保留。[OpenAI MCP文档](https://developers.openai.com/codex/mcp/)是本轮连接配置依据。
