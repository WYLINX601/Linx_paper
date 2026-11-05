# F03残余项独立复审

结论：F03关闭，blocking=false。本轮仅报告F03与delta回归；不重开或重复宣告F01/F02/F04。

- 冻结manifest：38条始末均匹配，manifest自身SHA未变。
- delta：仅三文件；afterSHA及反向diff重建beforeSHA全部匹配。
- 本轮新编反例：两条边 × 三字段 × 缺失/错置 × 三入口 = 36次，全部ValueError拒绝。canonical validate与compile独立调用；实际LPG调用默认完整analyze。
- 实际LPG的12次变异未改rawModelJson；记录包装器确认校验器看到实际变异，assertion来源仍正确。
- 复用上一轮独立脚本：仅FIX/OUT赋值改路径；84项变异全部拒绝，58项几何比较全部相等。明确属于复用，不是本轮新编证明；未运行随附测试。
- 正常payload、完整analysis与冻结相等；JSON往返与LPG反序相等；EV09历史1.1、历史来源、旧边evidenceRole及五新增边范围保留。SRC-B02仅允许当前assertionSourceVersion按既定2.1到2.2升级，不改历史sourceVersion。

修复根据：tools/semantics.py:116-118先验证assertion精确定位，再验证非HAS_SOURCE来源别名与BOUNDARY_PARTICIPANT locator；历史HAS_SOURCE保持独立来源规则。未统一改写历史来源。

证据：fresh-f03-results.json、fresh-positive-results.json、reused-verification.json、mutation-probes.json、geometry-recomputation.json、delta-verification.json、manifest-execution-start.json、manifest-end.json。脚本为f03_review.py及reused_previous_independent_review.py；真实stdout/stderr和退出码见reused-*。

边界：未执行数据库、GUI、发布或正式审核构建；不宣称这些已完成。当前目录manifest.json不存在，首次读取失败后使用冻结包内manifest.json。跨轮未变以用户给定为前提；本轮只核当前冻结和重算结果。其余限制见findings.json。

执行纠正：新编脚本首次退出1，原因是历史整边判据误把当前断言版本升级也当作禁止；核对SRC-B02后只允许assertionSourceVersion从2.1到2.2这一精确差异并重跑，未修改冻结文件。
