V01 2.1→2.2独立静态/语义复核

结论：blocking=true，当前不建议验收。发现4项，其中2项阻塞本轮交付。

F01（高，阻塞）：31条既有边的evidenceRole被统一改成synthetic_assignment，包括5条旧合成通行断言、R058以及墙轴/墙柱/屋面几何派生关系。不是单纯模型版本提升，丢失既有证据角色分层，应按2.1恢复。所有原几何和旧ID确实保持，不能因此漏掉属性语义漂移。

F02（高，阻塞）：屋顶交集GeoJSON的coordinates为tuple，保存JSON后变list。build_review.py:19直接比较新分析与JSON读回，实际本地复算的往返相等为false，导致正式审核页构建在输出前断言失败。应统一JSON类型后比较，不能删掉一致性检查。

F03（中）：应用义务校验存在假通过。C01成员目标改为来源EV09、I01两侧都改为side-a，完整validate_model仍接受；部分实际来源字段缺失/改错也被analyze接受。精确数据库读回另有保护，不把此问题扩大为能绕过整个写入流程，但逐对象“义务通过”标签需要补足角色、端点和来源校验。

F04（低，非写入阻塞）：candidate/analysis.json实际是2.1版本和基线SHA，没有basicRelations。当前代码重算分析，因此它不是已证实的运行时错误；应重建2.2候选分析或明确标成历史材料。

已核实的核心修订

模型仍55节点，LPG载荷含SOURCE共56；285→290边，仅新增授权5条。旧节点ID、关系端点/类型、原几何和EV09版本1.1保持。

独立有限墙厚减洞与圆柱截线复算，声明局部范围无数值差异：S04南侧四柱0.14/0.28/0.28/0.14m，S05端柱0.02m；S06扣I05剩0.4m；原15墙关系已定位。逐边段并集与去重一致。S04四墙端/转角只列候选，不加边、不把残余自动当开放。

RF01对S01—04全覆盖、S05局部5.616平方米、S06交集0；不推出没有其他屋顶。I04三个2.92m只为平面开敞段；S06/ST01投影交集2.76平方米且同层，无合并、包含或通行新断言。

实际LPG反序分析一致；几何、局部字段和缓存改值/缺值按已测反例拒绝，未回退rawModel。另做17个内存变异探针；随附36个基础关系测试实际运行全部通过，未覆盖上述缺陷。

run_graph.py仅静态审核：原位属性更新、严格5条新边、无删点删边/DDL，具旧图/原生类型/来源/载荷/代码hash guard与不重试、分层读回流程。未执行或导入run_graph.py，未连接数据库，未把候选视为数据库已写。

边界与留存

只读review-fixed，所有输出在review-output；未联网、未调用Neo4j/Obsidian、未启动子agent，未访问其他目录资料。冻结manifest约束的33文件初末哈希均匹配，manifest自身哈希亦未变。不重放旧2.1迁移，不声称建筑语义完备、真实净空或实证有效。

详见findings.json；复算脚本independent_review.py及independent-geometry.json、mutation-probes.json、evidence-role-drift.json、json-roundtrip-repro.json、verification.json保留于同目录。

复现命令（从本任务目录运行）：
/Users/wangyuelin/.hermes/profiles/academic/runtime/venv/bin/python -B review-output/independent_review.py
