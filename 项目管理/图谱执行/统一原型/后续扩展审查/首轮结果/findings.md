# 冻结包独立只读审查

结论：REQUEST_CHANGES，blocking=true。发现 1 项 P1 阻断、3 项 P2；未发现可复现 P0。本结论针对冻结代码的限定反例，不表示冻结基线的现有输出已经出现这些变异。

## 范围与完整性

- 唯一审查输入：`../review-fixed/`。manifest 的 31 个条目初检、试验后复检均匹配。未更改冻结包，Python 以 `-B` 执行；导入的研究模块均来自冻结包 tools，不从上级 tools 导入。
- 未访问 Paper、数据库、服务配置或凭据；未修改技能或记忆。只在 review-output 创建审查文件及复现脚本／输出。
- 阅读 d04.py、d05.py、d06.py、projection.py、compile_model.py、run_graph.py、analyze.py，另静态核读 queries.py；以 originals 的 D04/D05/D06、BOT、优化基准为语义依据，并比较 originals/model.json。
- 复现：`/Users/wangyuelin/.hermes/profiles/academic/runtime/venv/bin/python -B /Users/wangyuelin/.hermes/profiles/academic/cache/scratch/prototype-next-ozht7hck/review-output/reproduce.py`。
- `test-results.json` 保存脚本的 21 项观测记录，含预期拒绝及缺陷复现，不应表述为“21 项全部通过”。脚本只读冻结文件，变异在 deepcopy 内存副本上执行。

## F01 — P1：净面积为零的材料进入 D06 材料种数并改变归类

位置：`tools/d04.py:390-403`（材料登记及面积计算）、`tools/d06.py:63-71`（尤其第 65 行 `len(s['materialAreasM2'])`）。

语义依据：`originals/d04.md:128-135` 要求扣洞后的完整声明面域及材料面积口径；`originals/d06.md:80-84,179-186` 要求归类定义性输入真实满足、保留反例。当前 complete-surface-material 方案明确限定净域内完整已知表层配置，不是包含洞口的毛域材料类别清单。

可复现变异：只改 W03 的局部 surfaceRegions，不动对象、墙几何、洞口或来源边。将原灰泥矩形拆成四个互不重叠的灰泥矩形 `[0,0,9.6,1]`、`[0,1,1,2]`、`[2.2,1,9.6,2]`、`[0,2,9.6,3.6]`，以及一个砖矩形 `[1,1,2.2,2]`；后者恰好完全位于 I08 洞口。各区保留原有单位／版本／合成证据等元数据，并给不同局部 ID。

预期：扣洞后砖的净面积为 0；实际净墙面仍只有灰泥，completeMaterialCount 应为 1，归类仍为 single-material-complete-domain；也可显式拒绝不贡献净表面的材料区，但不能把 0 面积砖判成第二种净墙面材料。

实际：`compile_model.validate_model` 返回 True；D04 输出 `materialAreasM2={灰泥:30.959999999999997,砖:0.0}`、state=known；D06 completeMaterialCount=2，输出 multiple-materials-complete-domain。见脚本测试 `zero_net_material_changes_classification`。

影响／优先级理由：这是既有固定直墙及既有矩形洞口内的小型反例，不涉及曲面泛化。通过统一编译校验的输入会得到错误的定义性特征和候选归类，冻结载荷一致性保护不会发现这种逻辑错误，因此列为本轮阻断。

建议验收：材料字典可保留零面积诊断，但分类只计实际净域内有正面积的材料；明确数值零的处理，不能用未经审核的分类容差。加入此反例及真正存在两种正面积材料的正例。

## F02 — P2：D03 围合重算仍用 rawModel 快照掩盖实际几何缺失／变化

位置：`tools/analyze.py:28,55-65`，特别是 `expected_boundary=boundary_qualification(M)` 中 M 来自 rawModelJson，而不是实际节点 geometryJson。

可复现变异 A：在候选 payload 的内存副本中，仅删除 V01:C01 的实际 geometryJson，保留 SOURCE.rawModelJson 及边界派生缓存。

预期：依赖 C01 实际截面的围合分析拒绝或标记缺失，不继续声称已从当前几何核对。

实际：`analyze.analyze` 成功，D03.T02 与原分析完全相同，netSolidRatio 仍为 0.6310541310541311。测试 `missing_actual_C01_geometry`。

可复现变异 B：将实际 C01.geometryJson.radius 改为 1.0，快照及派生边缓存不动。

预期：按实际几何重算并拒绝过期缓存；独立调用冻结 boundary_qualification 对装入实际几何的模型计算时，BOUND-S05-C01 的净贡献由 0.020000000000000004 m 变为 0.88 m。

实际：顶层 analyze 仍返回原 D03.T02，不发现该变动。测试 `actual_C01_geometry_vs_rawModel`；贡献差值为另行执行的内存核算。

影响及分级边界：独立 analyze/CLI 的“实际读回重算”保证不完整；违反未知不以快照补回的要求。但 run_graph.main 第 114 行在调用 analyze 前执行 verify_exact，能拦截相对于载荷的此类变化。故不声称本反例能绕过整个迁移验证链，不将它升为写入阻断。

建议：围合推导使用实际读回几何，快照只提供已冻结契约／清单；缺少实际几何必须停止对应计算，并核对实际值重算与缓存。

## F03 — P2：rehydrate 丢弃快照清单外的实际关系，配对唯一性检查出现盲区

位置：`tools/projection.py:8-27`、`tools/d06.py:42-47`、`tools/analyze.py:104-108`。

可复现变异：复制候选 payload 中 I05→S05、role=side-a 的实际 INTERFACE_OF，改成新关系 ID／uid `EXTRA`／`V01:EXTRA` 并加入实际 relationships；不改 rawModelJson。

预期：实际 I05→S05 同角色关系有两条，D06 唯一实际配对资格不成立；应拒绝或明确报告额外关系。

实际：rehydrate 只遍历快照的 285 条关系，忽略实际第 286 条关系；analyze 仍发布 D06-P01，支持边只显示 R042、R044。见 `extra_actual_pair_relationship`。

影响及分级边界：独立重算忽略实际额外关系，D06 所称 unique actual interface role 并非基于完整实际关系集合。run_graph.verify_exact 能检查完整关系身份集合并拒绝多边；已执行其内存负例，故本项为 P2，而非声称写后保护可被绕过。

建议：重建时核对实际清单与快照清单的集合差，或在完整实际关系集上执行资格校验，不能静默截断。

## F04 — P2：新增几何来源定位／版本字段有登记但无值校验

位置：`tools/projection.py:33-55`、`tools/compile_model.py:137-186`；涉及 B03/CG01/ST01/TP01 的 geometrySourceLocator、geometrySourceVersion。

可复现变异：在候选 model 的内存副本上，将 B03.properties.geometrySourceLocator 从 `/nodes/51/geometry` 改为 `/nodes/9/geometry`（实际指 W03），同时把 geometrySourceVersion 改为 `stale-version`；其他所有内容不动。

预期：新邻宅的几何来源不能错指另一墙，且不能以旧版来源支持当前几何，应拒绝。

实际：统一 `compile_model.validate_model` 返回 True；现有来源校验只检查这些属性名被 contract 和 HAS_SOURCE.fields 覆盖，不检查属性自身所指的几何／版本。见 `new_geometry_wrong_locator_version`。

影响及分级边界：当前冻结候选这四个几何指针和版本均正确，本反例不表明原候选已存在错链。但未来更新这些已定义字段时，错误来源元数据能够进入合法编译载荷；写后逐值一致也只能证明数据库忠实保存了错误元数据。

建议：对本固定原型，校验新节点几何指针确实解析到该节点 geometry，且版本与声明几何／来源版本相容；无需发展任意外部格式解析器。

## 已验证的正确部分

1. candidate/model.json 经冻结编译器校验并编译，所得 payload 与 candidate/payload.json 相同；实际运行 analyze(payload) 与 candidate/analysis.json 相同。55 个案例节点，投影含 SOURCE 为 56 个节点，285 条关系。
2. 与 originals/model.json 比较：全部旧节点 ID、名称、class、labels、evidence、geometry 不变；全部旧关系 ID、类型、端点、状态、evidence 不变。旧节点已有属性的变化仅为 analysisItems 和版本类字段；旧关系属性变化也是来源／几何／基准／比较预期版本更新。仅新增 B03、CG01、ST01、TP01 四个节点。
3. B03 明确为人工另一邻宅，无 U01 的 BOT_HAS_BUILDING 归属；CG01 是 AnalysisCollection，不是 Zone/Site；ST01 是街段参照；TP01 是独立人工两点地表。局部立面记录未节点化，两墙结果未聚合成整栋类型。
4. 独立公式核对：W03 毛域 9.6×3.6、三洞面积和／并集、W10 已知覆盖 0.5、路面与边界宽 3.88 m、左侧实体比例 8/9.6、地表坡比 3/hypot(0.4,3.8) 均一致；门轴点不在路面内时同点门槛高差保留 unknown。均为合成技术计算。
5. D06 只有 T01—T05。基线联合有效集合为 W03 局部记录，W10 未知材料不强归完整材料类型；把 W03 也设 unknown 时联合集合为空。把实际 W10.facadeRecordsJson 的未知半区设为已知灰泥、保持快照不变时，实际分析会重算完整材料份额 1.0，并把 W10 加入联合有效集合。
6. 实际缺失 W03.facadeRecordsJson、实际缺失 B03.eaveZM 均拒绝；缺失 facadeRecords 字段来源、错指局部来源指针、过期来源／局部版本、重叠材料分区、错误关系 assertionLocator、错误 W03 配对均拒绝。未知／已知未匹配／互斥规则冲突分别返回不同状态。
7. 写前 Cypher 静态检查：冻结输入绑定、原生类型、唯一 ID／端点／命名空间、旧节点与相关关系集合及属性比对、分阶段防重试、提交前重新编译均有对应代码。未在 Neo4j 执行，不能宣称 Cypher 保护已独立实测。
8. 写后 verify_exact 仅以 AST 提取纯函数，不导入 mcp_client：内存构造合法读回记录可通过，属性变化、数值相等但原生类型不同、额外重复关系均拒绝。main 还安排其他图数据及 schema 比较、功能查询、读回分析与载荷分析对比；这里只完成静态核读和纯函数试验。

## 验证边界

- 不声称独立验证任何数据库实际状态、Cypher 执行结果、约束／索引、事务并发、写入／恢复或跨系统原子性；未连接数据库，也未运行 run_graph.main。
- 未导入 mcp_client、未读取配置凭据，未执行任何生产写入。run_graph 的静态代码不是数据库通过回执。
- 所有数值与反例均是固定 V01 合成试验，不是真实民居样本、真实统计、地方类型、因果或方法优越性证据；D02 内部构架、D07、D08 没有恢复。
- 完整表图、浏览器视觉验收、任意曲墙／曲街泛化不在本次范围；未把这些未来能力当阻断条件。
- 审查依据是包内五份语义文件，没有访问其外链文献、PDF、Zotero 或 Paper 主源，也不冒称重新精读文献。
