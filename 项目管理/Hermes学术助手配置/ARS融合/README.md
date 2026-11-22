---
wiki_id: ars-paper-integration
type: management
status: active
created: '2026-11-09'
updated: '2026-11-16'
summary: 以ARS组织科研流程，融合既有专业技能、Paper单源知识体系与Hermes执行；区分可调用入口、技术验收和研究验证。
---

# ARS 科研工作流融合

## 当前模型管理：Hermes官方Model routes（2026-11-11）

用户确认使用Model routes。活动委派后端为官方`advanced-delegation`插件提供的`model_map`；六条模型路由及其模型、供应商、推理强度唯一维护在当前`academic/config.yaml`的`delegation.backends.model_map`，不在Paper复制第二份模型配置，也不为每个ARS角色创建profile。

- 当前六条路由均保留`openai-codex / gpt-6.1-sol / medium / normal`；未选路由的任务使用具名默认`evidence_review`，六条路由显式设置`fallback_providers: []`，不自动换供应商。
- DeepSeek型号与接入渠道未确定，本轮未接入，也未向其发送材料。未来可只修改`literature`，其余路由不变；绑定到该路由的所有角色一起受影响。若仅改变其中一个角色，先显式拆分路由并调整角色绑定。
- 图形入口为Hermes子agent的Model routes设置；命令入口为`hermes delegation config`，只读检查用`hermes delegation config --show`。配置修改后开启新会话，不强刷现有聊天工具缓存。
- ARS仍提供角色、科研工作流、技能及输出合同。`ars-paper role-brief`生成`goal/context/option`；角色ID与来源绑定保留在`context`中，正式派发前显式运行`ars-paper role-check TASK.json`。
- **边界：** `role-check`是显式前置检查，不是官方`model_map`的运行时拦截。直接调用官方路由可以绕过ARS绑定检查；不能继续声称所有调用均被角色后端硬校验。主会话必须先读合同、检查授权并核对派发任务包。
- 原`ars_roles`后端保留为非活动的兼容/回退实现；其插件仍加载以提供`ars_*`工具子集，不再负责当前模型选择。工具继承与文件路径非沙箱的限制不变。

迁移实测、恢复与未测项见[验证记录](验证记录.md)；2026-11-10的旧角色后端回执保留历史身份，不用它证明本轮官方后端已实测。

## 采用决定与范围

**来源：** 用户于2026-11-09明确要求先引入ARS能力，将已有能力融合，并以其框架适配个人科研工作。此决定授权工作流、技能入口与执行适配；不自动授权修改研究问题关系、正文、证据、案例JSON、数据库或启用额外模型服务。

**本轮定位：完整引入流程框架，而不是只摘取几个方法。** ARS的研究、写作、审稿、全流程、系统筛选入口全部保留，配套实验工作流单独标识；每次按任务选择流程和阶段，不要求所有工作都跑完整流水线。已有专业技能不是被替换，而是作为领域执行与交付模块接入。

当前激活的是本机已适配的ARS **3.23.0**（上游提交`6ab4b03bf70a118a1b3ee7f3263ed9f19031061b`），本轮未升级上游包。2026-11-09的历史发布核查为3.24.2，不表示2026-11-10重新检索了最新版本；历史核查：3.24.2于2026-11-06发布；升级需单独检查Hermes路径、保留的适配和脚本兼容性，不覆盖本地适配包来冒充完成。

## 四层融合架构

| 层 | 负责什么 | 不负责什么 |
|---|---|---|
| 研究者与主会话 | 确认问题、范围、方法、采用与修订决定；整合及最终验收 | 不从子任务成功或校验PASS推导研究已成立 |
| ARS流程层 | 任务分类、阶段交接、材料缺口、证据核查、模拟审稿与确认节点 | 不另维护研究库、不自主完成实证、不自动开整篇流程 |
| 专业执行层 | 既有精读、方法比较、建筑拆解、图谱、统计、写作与原生文档技能 | 不各自重新主持同一流程或覆盖其他主源 |
| 资料与工具层 | Paper、Zotero、Obsidian、本机程序及获授权的Neo4j操作 | 工具存在或能连接不等于材料可信、实验完成 |

Paper仍是现行研究资料主源；ARS运行材料引用现有主源。材料护照是某次任务的交接记录，不是第二份大纲、研究定位、双基准或案例数据。

## 单一维护与日常入口

- **机器可读能力映射唯一维护在[工作流映射.json](工作流映射.json)**：六个工作流入口、任务类型、候选专业技能、模型路由、交付归属及确认节点。本页只解释设计，不手工复制第二份完整映射表。
- **只读适配器：[ars_paper.py](ars_paper.py)**；`ars-paper`命令由当前academic档案的轻量启动器调用这份Paper代码，不保留第二份执行代码。
- **角色交接与显式前置检查：[ars_role_routes.py](ars_role_routes.py)**；[ars_role_provider.py](ars_role_provider.py)保留旧后端及`ars_*`工具集注册，运行时插件只作薄加载。活动模型路由使用Hermes官方实现。
- **技术测试：[test_ars_paper.py](test_ars_paper.py)、[官方路由测试](test_model_routes.py)及[旧后端兼容测试](test_ars_roles.py)**；实际验证、未测项及恢复见[验证记录](验证记录.md)。
- 上游来源与版本、角色提示词和详细协议保留在本机`academic-research-suite`；本页不重写其全部规则。

不需要记住命令；直接描述任务即可。日常例子：

- “按ARS和我们的精读规范，读这篇论文；先还原作者研究，不急着套到本研究。”
- “比较这些论文的方法，逐篇讨论，再决定哪些能迁移。”
- “审查这一节，先只给证据和论证问题，不直接改稿。”
- “按ARS完整流程处理这篇稿件，每个阶段等我确认。”

命令用于透明检查，不替代真实工作：

```bash
ars-paper list
ars-paper route paper-read
ars-paper route review --mode methodology-focus
ars-paper brief rq-discuss --goal '只讨论研究问题，不建立下层映射' --source '论文章节/研究问题.md'
ars-paper doctor
```

`route`和`brief`只生成路由及交接数据，状态为`prepared_not_dispatched`，不启动agent、不写Paper、不完成阅读。`brief`对明确指定的Paper文本通过`mac-paper`取得当前哈希；哈希只标识字节，不证明研究内容已经审核。自定义交接格式为`ars-paper-handoff/1`，**不是**伪造的ARS Material Passport。

模式列表用于发现入口，不是可执行合同。包括默认模式在内，适配器均返回`dispatch_allowed_by_this_adapter: false`与`mode_contract.status: not_loaded_by_adapter`；实际执行者仍须读取所选工作流和角色合同，核实前置材料及用户授权。用`--mode`切换模式时，不沿用原任务默认门槛作为新模式的有效合同。跨会话恢复由上游真实护照协议处理，本适配器不实现或伪称已经实现恢复。

## 角色合同与路由绑定（2026-11-10建立，2026-11-11切换官方模型路由）

**已完成配置，不等于所有角色都完成科研实测。** 机器主源为[角色路由.json](角色路由.json)；本机ARS3.23.0的45份规范角色文件已逐一绑定，其中34个可委派角色、11个主会话角色，未映射为0。另有4个字节相同的插件别名，不重复计数。

| 角色来源 | 可委派角色 | 主会话角色 |
|---|---|---|
| 研究与综述 `deep-research` | 12 | 2 |
| 论文写作 `academic-paper` | 9 | 3 |
| 模拟审稿 `academic-paper-reviewer` | 7 | 0 |
| 全流程协调 `academic-pipeline` | 3 | 2 |
| 系统筛选 `sr-screener` | 1 | 3 |
| 实验配套 `experiment-agent` | 1 | 1 |
| 共享完整性核查 `shared` | 1 | 0 |

- 每个角色显式指定执行位置、既有模型路由、原角色文件与SHA、工作流/专项协议、所需技能及输出合同。技能引用绑定实际安装文件与SHA；只读worker可用`read_file`读取，不依赖它没有的`skill_view`。
- 每个角色仍映射到既有六条模型路由之一；模型参数由Hermes管理，不由Paper强制所有路由同模型。准备和显式前置检查会拒绝未知角色、绑定漂移、主会话角色委派或错选路由；官方`model_map`本身不执行这些ARS检查。
- 筛选的A、B、仲裁、senior QC分别配置席位及提示变体锚点；它们复用规范筛选角色。不同ID本身不证明盲态、输入相同或仲裁先后，执行时仍由主会话按真实流程检查。
- 重审Phase 1、2A、2B、受限2B′设4个**本地合同调用ID**，直接绑定上游重审协议，不以首轮EIC或editorial-synthesizer角色冒充。这些调用不新增上游规范agent文件。

### 检查与交接

```bash
ars-paper roles
ars-paper roles --all-bindings --workflow sr-screener
ars-paper role academic-paper/peer_reviewer_agent
ars-paper role-brief academic-paper/peer_reviewer_agent --goal '按已确认范围审查材料，不改稿' --readable-context
ars-paper role-check /absolute/path/to/prepared-task.json
ars-paper doctor
```

`role-brief`仍只准备交接；新会话实际派发使用官方API的`goal/context/option`，不再提交`ars_role`。`--readable-context`将context展开为多行对象，减少长行截断风险；派发时将`context_object`序列化回JSON字符串，保留所有绑定值，并以`role-check`检查重建后的准确任务包。它不能保证任意长字段都不会截断，读工具仍须检查截断标志。

### 工具边界：以本机实际API为准

当前原生模型可见schema**不提供逐任务的`role`和`toolsets`**；实际子任务继承父会话工具，能力由深度限制决定。注册表中的readonly/research/candidate/compute在不受限父会话里只是调用约束，不是provider强制权限隔离。

需要严格工具子集时，使用独立、有限的父CLI会话，仅开启`delegation`加对应的`ars_readonly`、`ars_research`、`ars_candidate`或`ars_compute`。`role-brief`给出`parent_toolset_scope_for_strict_subset`。`inherit_mcp_toolsets=false`在此API下也不能独自移除父会话原有MCP工具。工具子集不等于文件路径沙箱；正式Paper写回仍由主会话完成。

旧`ars_roles`后端在会话建立时绑定注册表版本；官方后端只绑定路由选项，ARS版本在生成和显式检查任务包时核对。派发前重新检查，不能把较早检查当作原子锁。后端或路由选项变化后开启新会话，不强刷当前聊天schema。桌面GUI完整科研流程尚未验收。

**历史验收（2026-11-10）：** 62项程序测试、47项doctor检查通过；旧`ars_roles`后端4类代表角色已真实委派并读取角色/技能头部。三轮独立静态审查及运行中暴露的API修正，分别见[验证记录](验证记录.md)与[旧机器验收回执](角色路由验收.json)。本轮官方路由的实测另行记录，不是全流程科研、所有角色效果或盲筛准确性验证。

## 怎样执行融合后的任务

1. 先通过`mac-paper status/context`读取当前规则、入口与定位，再读取本次明确相关的资料。
2. ARS统一识别任务。明确请求直接进入对应模式；跨阶段且目标不清才澄清；完整pipeline和系统筛选均保持显式启动。
3. 读取选定`WORKFLOW.md`和当前阶段角色文件，只加载确实需要的专业技能。映射中的`skills`是候选能力，不是要求一次全部加载。
4. 写作与审稿由ARS合同组织；专业技能补充领域操作、质量标准或交付格式，不另起竞争的评分、裁决或阶段状态。
5. 有独立工作价值时，通过模型路由委派。交接同时给出任务、必要来源及当前哈希、角色文件、所需技能、输出字段和边界。路由名本身不会加载技能或构成权限隔离。
6. 主会话整合结果，核对来源、推断、缺口、实际执行和未做事项。正式写回以最新SHA通过`mac-paper`完成，冲突重新读合并。
7. 用户确认研究决定后才进入依赖该决定的下一阶段。长任务按ARS真实Material Passport及`run_ledger.py`记录；一次小改字或短问答不强制创建护照或管理文件。

## 已有能力怎样融合

- **文献（2026-11-16卡片先行）：** 涉及论文阅读先由Paper适配版`nature-paper-card`查找并复用单篇卡，无卡先保存明确Partial的初读卡；随后核读补卡，再做拆解、比较、引用或导图。`read-research-paper`继续负责共用证据规范及定向执行，`paper-methods-comparison`负责分篇节奏与跨篇对齐，`obsidian-mindmap`负责阅读视图；不再并行生成两种卡片。定向核读不扩大为全文，旧卡原位复用，不自动补历史卡。检索、下载、解析、建卡、实际阅读与精读分别记录；这是本地专业扩展，不是新增ARS官方模式。详见[卡片使用说明](../论文精读卡片使用说明.md)。
- **写作与审稿：** ARS负责问题—论证—证据与阶段；`nature-writing/polishing/response/reviewer`按当前角色补充，不能把一次模拟审查当真实期刊裁决或双盲实测。
- **建筑与图谱：** ARS容纳方法讨论与证据交接；建筑拆解与Neo4j技能负责领域表达。BOT原定义、本研究优化基准及案例JSON继续各自单源，实际建模任务先读双基准。建模入口不自动执行数据库写入。
- **实证与统计：** 配套experiment-agent用于用户明确要求的设计、管理或分析任务，统计与表格技能承接；真实执行在ARS论文流水线之外的获授权任务进行，再将真实记录交回。设计、代码运行、结果复核与学术解释分别验收。
- **知识组织：** Paper继续维护跨任务主题、问题、论点与资料；ARS只管理本轮任务状态，避免把整个研究库复制进护照。
- **交付：** DOCX、PDF、原生导图、Draw.io、Excalidraw和PPT继续使用现有技能；根据用户要求选择格式并渲染检查，不因框架接入自动生成全部格式。

## 模型、并行与数据边界

本轮切换不改主模型、并发限制或六条路由的现有模型。以后各路由可在Hermes中独立选择模型；Paper只维护角色到路由的绑定、科研合同与检查规则。历史模型指定与历史验收不被追溯改写。

独立评审需要隔离上下文和相同冻结输入，不能把同一会话先后换角色称为独立盲审。即使实际分离了上下文，同模型仍可能有共同偏差，不等于跨模型验证。所选流程必须独立评审而当前环境不具备时，报告阻塞；只有流程允许时才能明确降级为单评审或主会话执行。

跨模型服务、额外API、未公开稿件向新供应商传输仍需明确供应商与内容类别的授权；配置项存在不是同意。现有模型会话和服务本身也不等于离线处理。不得启用自动投稿、自动Git提交或后台改写。

## 当前研究接续不被框架改写

研究问题与范围以当前[项目上下文](../../../context/PROJECT_CONTEXT.md)及研究路径JSON为准。当前上层问题之间逻辑与下层映射仍待讨论；ARS不得为了满足模板而强补子问题、章节采用、证据关系、研究假设或形式化评分。临时讨论可保留`draft/incomplete`，未确认材料不伪称完整合规RQ Brief。

ARS通用示例中的医学式证据等级、固定文献数量、双语摘要locale或IMRaD结构不直接变成建筑学论文强制规则。按实际学科与作者要求适配；正式跨阶段交接若尚不满足原合同，明确说明缺项或记录适配，而不是偷偷补数、捏造证据或宣称原版校验通过。

## 来源、许可与恢复

来源：Imbad0202/academic-research-skills的README、POSITIONING、ARCHITECTURE、CONTROL_AVAILABILITY、DATA_FLOWS及发布记录；本机`manifest.json`保留原分发来源与提交。上游CC BY-NC 4.0与NOTICE继续保留，本适配不重新许可第三方内容。

适配代码和配置经`mac-paper`发布；运行时设置通过`hermes config set`和`hermes tools enable`修改，修改前备份当前academic配置。回退只恢复本次改动或删除新增适配，不动现有研究主源，不整文件回滚后续其他配置。具体备份与验证范围见[验证记录](验证记录.md)。
