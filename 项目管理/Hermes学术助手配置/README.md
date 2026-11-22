# Hermes 学术助手使用说明

更新：2026-11-11（本次将活动子agent路由切换为Hermes官方Model routes；其余迁移说明保留原核查范围）。学术助手已迁到 Mac，桌面选择 **This device → 学术助手**。模型配置为 `openai-codex / gpt-6.1-sol`；历史会话保留原有单会话模型选择。Paper、Zotero 与 Obsidian 在本机访问，只有 Neo4j 仍连接 Linux。

## 本地入口

- 档案：`/Users/wangyuelin/.hermes/profiles/academic`。
- CLI：`/Users/wangyuelin/.local/bin/hermes -p academic`。
- 运行工作区与唯一现行研究主库：`/Volumes/LinxSpace/Paper`（2026-11-16用户确认已迁入）；原 `/Users/wangyuelin/Desktop/Obsidian/Paper` 停用。此前19条会话的执行目录同步与旧workspace归档属于历史迁移记录，见[工作区迁移记录](工作区迁移记录.md)，不表示本轮已批量更新历史会话。
- 启动时先运行档案 `bin/mac-paper status` 和 `bin/mac-paper context`，读取最新项目规则与入口。
- `mac-paper` 保留原CLI，用本地文件操作替代SSH；`mac-run -- COMMAND ARG...` 也在本机执行。`--target` 仅允许 `local` / `localhost`。
- Python：档案下 `runtime/venv/bin/python`；文档渲染：`bin/soffice`，使用本机正式 LibreOffice 与中文字体配置。

### 新主库入口核对（2026-11-16）

- 本次只修正当前academic档案的`mac-paper`默认根目录及`ars-paper`、`paper-maintain`、`outline-ops`启动脚本路径；没有搬动研究文件、修改历史回执或重写研究内容。
- 已重新执行`mac-paper status/context`，成功读取新主库的`AGENTS.md`、`README.md`、`context/PROJECT_CONTEXT.md`；`ars-paper list`与`paper-maintain --help`可运行。
- `outline-ops --help`仍因当前Python环境缺少`ruamel.yaml`而失败；本轮不执行大纲修改或安装依赖。全库维护、ARS角色绑定、Obsidian界面与MCP服务未因入口修正自动视为通过验收。
- 修改前的四个启动文件保留在`/Users/wangyuelin/.hermes/profiles/academic/backups/paper-root-20261116-1920/`。恢复时仅比较并恢复本轮路径改动，不覆盖后续修改。

旧附件内联预览可能仍引用Linux绝对路径，使用[本地文件索引](历史会话本地文件索引.md)访问迁移后的原文件。

旧会话中的 `/home/linx/.hermes/profiles/academic` 路径只作历史记录，当前对应本机档案路径。原始消息没有批量替换；会话执行目录已迁移。正式成果直接写回Paper，不另建研究库副本。

## 论文精读卡片（2026-11-16）

已按用户要求以`nature-paper-card`为基础完成Paper适配，使用academic档案内安装副本，不依赖Downloads长期存在。以后涉及论文阅读，先查找并复用已有单篇卡；无卡先建立明确Partial的初读卡，再核读更新，最后做拆解、比较、引用或导图。单篇卡片是复用主记录，不因每轮任务重复创建。

完整中文卡保留16节，补充建筑调查/空间类型、理论/框架视角；方法实验栏目按论文真实逻辑调整。已有旧卡保留路径、批注和格式，定向阅读不扩大成全文。来源定位、作者与阅读者判断、迁移条件和暂缓研究映射分别记录；新建卡不等于精读完成。

用法、脚本检查边界及恢复见[论文精读卡片使用说明](论文精读卡片使用说明.md)，实际技术结果见[验证记录](论文精读卡片验证.json)。本轮不更改模型配置、数据库、正文或已有文献卡片，不自动补全历史文献库；真实论文试读质量仍须单独验收。

## 文件与服务

**ExFAT兼容（2026-11-16，用户授权）：** 当前主库新建文件可显式使用`--expect-missing --create-mode recoverable`；先保留完整待写副本，再独占创建并回读校验。该模式的新文件可在写完前被看到，不冒充完整文件原子发布；默认`atomic`不自动降级。`mac-paper recoveries 路径`只查询恢复记录。12项隔离回归测试通过，R1已在实际ExFAT主库完成上传与回读。详见[ExFAT写入兼容说明](ExFAT写入兼容说明.md)、[验证记录](工具验证/mac-paper-exfat验证.json)。

`mac-paper read` 提供 SHA-256；覆盖必须使用刚读到的 `--expected-sha256`，新建使用 `--expect-missing`。写入前保存可恢复副本到 Paper 的 `.hermes-academic-backups/`，写完回读核对。冲突须重新读取合并。工具自身逐文件加锁，Obsidian等编辑器不参与此锁，因此仍需避免同时编辑。

Zotero MCP直接运行本机兼容启动文件，保留条目键、页码与PyMuPDF回退标识。Obsidian MCP直连 `http://127.0.0.1:27123/mcp/`；密钥仅放受限配置，Zotero/Obsidian须处于可用状态。

Neo4j经SSH连接 `linx-HP-EliteDesk-880-G6-Tower-PC` 并启动原MCP，数据库仍在Linux。Linux离线不影响本地Paper、Zotero和Obsidian；此时图谱查询不可用。MCP仍有写工具，数据库变更必须遵守项目授权与可恢复规则。本次迁移仅执行只读查询。

既有技能保留；2026-11-09起自动加载 `academic-workspace` 与 `academic-research-suite` 两个入口，具体工作流和专业技能按任务加载，不一次展开整个套件。转录及部分外部服务仍需各自凭证，不因文件迁移而宣称已接通。保留最新多模型协作配置，但OpenRouter等能力是否可用取决于Mac已有凭证。

验收与尚未完成事项见[验收清单](验收清单.md)，恢复方式见[恢复说明](恢复说明.md)，技能迁移见[技能迁移清单](技能迁移清单.md)。旧部署说明保存在[Linux历史记录](历史配置/2026-10-26-Linux/README.md)，其中路径与服务状态不是当前使用入口。

## Excalidraw 原生 CLI（2026-11-02）

已安装完整的 `obsidian-excalidraw-cli` 配套技能与辅助脚本，当前学术档案可加载；Paper 库原生连接、创建、读回和 PNG 导出已经实测。详见[Excalidraw CLI 使用说明](ExcalidrawCLI使用说明.md)，其中保留版本、来源提交、命令、验收路径及未验证范围。本次不改变既有研究图，也不新增额外 MCP 或 API 密钥。

## ARS科研工作流融合（2026-11-09）

已按用户要求以ARS组织科研流程，并接入既有精读、方法比较、建筑图谱、统计、写作与原生交付能力。设计与日常用法见[ARS融合入口](ARS融合/README.md)，机器映射为同目录`工作流映射.json`，实测与恢复见[验证记录](ARS融合/验证记录.md)。

`ars-paper list/route/brief/doctor`提供只读任务路由、交接准备和安装核验；命令本身不启动agent或代替工作流合同。当前保留本机ARS3.23.0，不声称已升级至3.24.2。六个模型路由已完成配置核验，证据复核路由的原生同步子任务已实际联调；完整科研流程尚未端到端验收。

新的CLI/API会话启用委派并自动加载ARS入口；当前会话不强刷工具列表，桌面GUI新会话流程仍需实际任务检验。研究问题、正文、证据和数据库不因集成自动改写。

## ARS角色级路由（2026-11-10）

已补齐45份规范角色的执行归属与合同绑定：34可委派、11主会话；另配4筛选席位、4分阶段重审调用，插件别名不重复计数。2026-11-11起活动后端为官方`model_map`，复用原六条模型路由；主模型、并发限制与研究主源不因切换重置。模型、供应商和推理强度在Hermes中逐路由配置，不需逐角色创建profile。

`ars-paper roles/role/role-brief`供透明检查和交接准备，`roles --all-bindings`含席位及重审调用；长context优先用`role-brief --readable-context`。配置主源为[角色路由.json](ARS融合/角色路由.json)，用法与实际工具限制见[ARS融合入口](ARS融合/README.md)，结果见[角色验收](ARS融合/角色路由验收.json)。

62项测试、47项doctor检查通过，4类代表角色已通过有限CLI父会话实际委派。
上述为2026-11-10旧角色后端验收；本轮结果见[验证记录](ARS融合/验证记录.md)。新会话使用`goal/context/option`，ARS角色及合同仍在context中，派发前显式运行`ars-paper role-check TASK.json`。此检查不是官方Model routes运行时硬拦截；旧`ars_roles`仅保留兼容回退和工具集注册。默认路由为`evidence_review`，六条路由禁止供应商自动回退。DeepSeek仍待型号与渠道确认，尚未接入。当前原生API没有逐任务`role/toolsets`，子任务继承父工具；角色工具配置不等于任意桌面父会话下的权限隔离，严格子集需限定父CLI工具集，文件路径仍非OS沙箱。新聊天加载更新schema；桌面GUI与完整科研流程没有因此端到端通过。
