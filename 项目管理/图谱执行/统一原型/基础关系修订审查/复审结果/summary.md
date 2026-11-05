独立复审结论：blocking=true；F01、F02、F04关闭，F03部分修复但仍阻塞验收4。

剩余一项medium问题：局部边的assertionSource*检查已补齐，但另一组sourceUid/sourceVersion/locator仍有漏洞。实际LPG把新边来源版本改1.1或locator改/relationships/0，完整analyze仍通过；canonical错locator也可重新编译。聚焦复现确认实际错误值已送入语义验证，不是回退rawModel。固定payload和精确数据库读回guard并未因此被证明可绕过。

独立变异矩阵84项：68拒绝，16接受。原列角色、成员端点、SRC-C01字段覆盖及局部assertion来源反例均已拒绝；未接受的新反例详见findings.json及focused-provenance-repro.json。

已通过：旧对象/原几何/关系身份端点类型和旧证据角色保留，仅增5条边；完整分析实际JSON写读往返相等，候选payload与analysis均匹配重算；六空间24边段独立几何复算一致，指定柱长、0.4、5.616、三个2.92及2.76均保持；run_graph限定更新与保护静态检查通过。manifest始末35项哈希及自身哈希一致。

未执行正式数据库读回或完整非preview构建，留主会话后续实测。复算脚本independent_review.py、focused_provenance_repro.py及最终报告生成脚本均保存在本目录；冻结源未改。
