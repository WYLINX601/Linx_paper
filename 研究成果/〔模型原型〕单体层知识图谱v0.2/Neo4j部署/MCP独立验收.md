# Neo4j MCP有限独立验收

**结论：本次指定范围内未发现阻断问题。** 本地配置、SSH stdio实测、只读工具范围、11次查询响应及接入后完整性报告相互一致，可验收为官方MCP只读接入完成。该结论不表示新连接已经在当前Codex工具目录热加载或完成原生工具调用，也不扩展为建筑学模型效度审查。

复核时间：2026-10-22 21:08（Asia/Shanghai）。只读指定本地资料；Codex配置仅提取`mcp_servers.neo4j-paper`表，没有读取凭据文件、远程操作或执行受审脚本。只新增本文件，不修改原独立验收、配置、代码或研究JSON；没有启动子agent。参考已安装的`neo4j-mcp-skill/SKILL.md`，以本轮实际工具发现及脚本为版本行为依据，不照搬其中旧变量或`apoc.*`通配示例。

## 独立核对结果

| 核对项 | 证据与结论 |
|---|---|
| 实际MCP协议 | `MCP实测.py:12–14、73–84`使用SSH标准输入输出发送initialize、initialized、tools/list及tools/call。`验收/MCP实际查询.json`记录服务名neo4j-mcp、版本v1.6.1、协议2024-11-05、工具schema和原始文本响应。没有以HTTP验证冒充MCP调用。 |
| Codex连接一致性 | 只读取当前`mcp_servers.neo4j-paper`表，逐字段与安装记录codex对象比较相等；command与args拼接后，和实测报告command完全相等。实际命令为`/usr/bin/ssh -T -o BatchMode=yes`连接既定Linux主机，运行远端`/usr/bin/python3 …/tools/MCP启动.py`。 |
| 只读能力范围 | 当前enabled_tools恰为get-schema、read-cypher；`MCP启动.py:9–20`固定v1.6.1二进制路径、stdio、`NEO4J_MCP_READ_ONLY=true`、关闭遥测。实测tools/list也仅返回两项，没有write-cypher。11次调用仅含get-schema及RETURN/MATCH/SHOW只读查询，未发现研究写入语句。 |
| APOC最小配置 | `APOC最小权限启用.py:18–35`拒绝已有冲突配置，只复制发行包内APOC Core 5.26.32，并写入allowlist=`apoc.meta.schema,apoc.version`、unrestricted=`apoc.meta.schema`；配置校验后重启，异常时回退配置及禁用新JAR。`验收/MCP-APOC启用.json`记录版本5.26.32、schemaEntries=39及唯一列出的APOC过程apoc.meta.schema。没有使用skill中的apoc.*通配解限。 |
| 查询定义与实测对应 | 独立读取查询定义与报告，11条purpose/name/arguments逐项完全一致；各响应均为可解析JSON且无isError。连接返回connected；约束为KGItem(uid)唯一；3项索引均ONLINE、100%；14/7实体、94节点/55断言/4分类；UID异常查询为空，文献通行断言为0。 |
| 研究语义返回值 | 独立将MCP结果与本地JSON深比较：ACCESS_HV/VH两条方向、空间标签、界面和完整情境一致；F_1_roof_layered保留true/disputed，E_Z1为EVIDENCED_BY，E_COMMON为CONFLICTING_EVIDENCE；四次分类decision及全部criteriaResults一致。没有把演示通行转为文献事实，或把不匹配分类转成肯定结论。 |
| 数据未变的支持证据 | 接入后verify时间为2026-10-22T12:59:56.723631Z，报告94节点、1305属性值、298标签、216关系，原始JSON及快照哈希匹配。独立重算五份维护JSON的SHA-256，与报告逐项一致；导入验证器SHA-256仍为88989e12…2810000，与先前独立验收的最终版本一致。这支持“研究图谱与当前维护源保持一致”，不是仅凭只读工具名称推断未变。 |
| 来源与版本追溯 | 安装记录保存skill仓库、固定提交39247b9c4ab20062aefd1cfe83c040167ef9ee83、三个skill的文件指纹，以及MCP发布来源、v1.6.1和压缩包SHA-256。独立重算所列9个本地skill文件，全部与记录一致。MCP initialize版本与启动器版本目录一致，APOC JAR哈希留存在启用记录。 |

本次还只读解析三份Python脚本AST，语法均通过；没有执行它们的联网、配置、重启或凭据读取逻辑。上述逐项比对由独立核查脚本在内存完成，不仅转述受审测试的passed字段。

## 声明与限制

`MCP与Skill使用说明.md:29–31`明确当前工具目录未热加载，测试通过同一SSH命令及实际官方进程完成；这一表述与实测证据相符。应继续保留该边界，后续Codex原生调用是否可用，需在连接加载后另行验证。

`MCP实测.py:81–85`把协议调用无错误标为passed，没有在程序中断言业务返回值。本次独立比对确认当前11次结果正确，因此不构成本轮阻断；若日后重复运行，该passed本身只能证明这些调用成功，不能单独证明研究答案未变化。

来源和哈希记录提供可回溯入口。本次未联网验证GitHub发布物、上游提交内容或官方checksum来源，也没有读取远端二进制/JAR；“官方来源已下载并核对”的部署事实以主会话安装记录为证据，本次独立确认的是本地记录一致性、安装skill文件指纹及进程自报版本。

只读状态由服务端配置、客户端工具允许列表及实际工具发现共同支持；本次没有提交写入反例来测试拒绝行为，也没有审计官方二进制内部实现。APOC解限授权及持久write-cypher被自动审批拒绝的历史，由本轮任务提供的授权边界和安装记录交叉对应；没有替用户追加任何写权限。

get-schema返回39项结构摘要，启动器使用sample size 100。它用于结构发现，不替代完整性验证或数据库约束定义。接入后完整性另由既有验证器检查，说明文档已区分二者。原论文PDF与图片仍在Mac资料库；MCP查询到引用不表示已经阅读全文。没有新增学术模型评估、导入、数据迁移或真实建筑事实。

## 本轮文件指纹

核对时间：2026-10-22T13:08:19Z。

| 文件 | SHA-256 |
|---|---|
| MCP启动.py | d92f31d8cd25647b1c40bf6e83f65b94673b84fffb9b1c577bfea43fadf81e7c |
| MCP实测.py | b228ef06cedc9d7efd6f6bfe279b3d4229bb261f63723da9e764f280e56a0106 |
| APOC最小权限启用.py | 9cbf76f9fc5d4abb7b3f1cbabd141977c63b851ad683f3b0ef168b1172e5e066 |
| MCP验证查询.json | 158c2b7f2a6136b27a890040cceb350476b3a1958ae32b3f423f3c58c79d32b7 |
| MCP与Skill使用说明.md | 1705af6b21fcf4c9e63f5f26bf633e08a8c4612bc6d6c516299acb84c8d44dac |
| 导入与验证.py | 88989e12a0b5110c2d952ae41647685ac6ba1d7898465694abeeeb0732810000 |
