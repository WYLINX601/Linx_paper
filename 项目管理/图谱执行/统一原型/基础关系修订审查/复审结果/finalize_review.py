"""Validate frozen manifest again and assemble the independent review report."""
import hashlib,json
from pathlib import Path
OUT=Path(__file__).resolve().parent
FIX=OUT.parent/'review2-fixed'
def read(p):return json.loads(p.read_text())
def write(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
manifest=FIX/'manifest.json'
start=read(OUT/'manifest-start.json')
items=read(manifest)
end={'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'files':[{'path':i['path'],'ok':hashlib.sha256((FIX/i['path']).read_bytes()).hexdigest()==i['sha256']} for i in items]}
assert all(i['ok'] for i in start['files']) and all(i['ok'] for i in end['files'])
assert start==end
write('manifest-end.json',end)
v=read(OUT/'verification.json');probes=read(OUT/'mutation-probes.json');focused=read(OUT/'focused-provenance-repro.json');pres=read(OUT/'preservation.json')
assert v['failedChecks']==['all_provenance_and_endpoint_counterexamples_rejected']
assert len(probes)==84 and sum(x['rejected'] for x in probes)==68
assert all(x['analyzeAccepted'] for x in focused)
count=len(items)
report={
 'blocking':True,
 'findings':[{
  'id':'F03','severity':'medium',
  'issue':'仍阻塞本轮验收4：角色、成员端点、HAS_SOURCE字段覆盖和assertionSource*反例已修复，但局部边的另一组来源字段sourceUid/sourceVersion/locator未被同等验证。实际LPG错误来源版本或定位仍会获得通过结果；canonical错误locator也可编译。F03仅部分关闭。',
  'evidence':[
   'review2-fixed/build_fix.py:33-37为5条新边同时声明assertionSourceUid/assertionSourceVersion/assertionLocator与sourceUid/sourceVersion/locator。BOUND-S04-C01的两组定位正常均为/relationships/285，版本均为V01-unified-2.2，不是只含assertion字段的模型。',
   'review2-fixed/tools/semantics.py:114-116核验所有边的assertionSource*；117-132仅在HAS_SOURCE上核验另一组sourceUid/sourceVersion/locator；148-153的局部边检查未核验这组字段。tools/compile_model.py:169-177只对非HAS_SOURCE的sourceUid/sourceVersion补了检查，未核验其locator。',
   'review2-output/focused-provenance-repro.json前三项：分别将实际BOUND-S04-C01.sourceUid改V01:EV09、sourceVersion改1.1、locator改/relationships/0，完整analyze均接受且完整分析与未变异结果完全相同。rawModelJson保持不变；记录包装器确认semantics.validate实际接收的就是错误值，并非回退rawModel。',
   'review2-output/focused-provenance-repro.json最后一项：仅将canonical新边locator改/relationships/0，保持assertionLocator=/relationships/285，validate_model、重新compile_model及完整analyze全部成功。反例模型保存在review2-output/counterexample-wrong-boundary-locator.json。',
   'review2-output/mutation-probes.json：84个独立canonical/LPG探针中68拒绝、16接受；漏检集中于BOUND-S04-C01和既有R059的sourceUid/sourceVersion/locator缺失或错误。角色、端点、SRC-C01字段与来源、局部assertion来源的指定反例均被拒绝。'
  ],
  'reproduction':'使用指定Python加-B分别执行review2-output/independent_review.py与review2-output/focused_provenance_repro.py。二者已真实执行完成，退出码0。重点查看focused-provenance-repro.json中actualRehydratedValueSeenByValidator、fullAnalysisUnchanged和canonical-new-compile；不依赖随附测试结论。',
  'recommendation':'在共享的限定语义验证路径中核验局部边声明的两组来源字段是否一致，至少sourceUid/sourceVersion与assertionSourceUid/assertionSourceVersion一致，locator与该关系的准确JSON Pointer一致；实际LPG与canonical共用此检查。对既有关系保留原属性与证据角色，按其既定来源规则核验，不为消除冲突盲目改写历史来源。保留EV09的1.1例外，增加本轮可复现的负例。此处是应用验收缺口，不是已绕过run_graph固定payload或精确读回guard的证明，也不要求完整OWL或真实建筑实证。'
 }],
 'closed':['F01','F02','F04'],
 'checked':[
  f'冻结manifest始末共{count}个条目全部SHA匹配，manifest自身SHA始末相同；见manifest-start.json、manifest-end.json。未修改冻结源。',
  '独立比较55模型节点及285条旧关系：节点ID/顺序、名称/类别/标签、原几何及关系ID/类型/端点/顶层证据和状态保持。扣除精确版本升级及六空间边界/覆盖、局部范围与来源字段覆盖白名单后，没有旧记录非授权差异。EV09整个节点完全不变，sourceVersion仍为1.1。见preservation.json。',
  '只新增BOUND-S04-C01—C04和BOUND-S06-W10共5条BOUNDARY_PARTICIPANT，无新对象；模型关系285→290，编译载荷56节点/290关系。未重放2.1迁移。',
  'F01关闭：全部285条旧关系evidenceRole按ID与基线精确相等，包括原通行情境、geometry_derived及synthetic_geometry_derived分层；5条新边拥有自身来源与证据角色。',
  'F02关闭：完整analyze对象实际写入analysis-roundtrip.json再读回后相等；所有层级均为JSON原生类型且无非有限浮点数。roof_coverage自身JSON往返也相等。此为真实本地谓词测试，不冒称已运行正式审核页构建。',
  'F04关闭：重新compile_model所得payload与candidate/payload.json完全一致；重新完整analyze所得结果与candidate/analysis.json完全一致，不再是2.1旧分析。',
  'F03已修复的部分：canonical与实际LPG分别将C01成员指向EV09/B02、I01两侧重复side-a、界面侧指向墙/来源、opening-host指向柱/空间、清空或删除SRC-C01.fields、移除字段支持、修改SRC-C01来源UID/版本/locator/locatorKind、缺失或错置局部assertion来源均拒绝。全部实际LPG变异保留rawModelJson不变；另有实际几何/边界属性删除与缓存改值拒绝。',
  '独立解析线段裁切、圆柱截线、有限墙厚包络、宿主洞口扣除与区间并集复算全部六空间24边段，58项参与者或边段并集比较全部一致；不调用生产局部范围或区间函数作为独立几何预期值。',
  '数值保留：S04本侧柱0.14/0.28/0.28/0.14m；S06北界扣I05剩两段合计0.4m；RF01对S05投影5.616平方米，S01—S04全覆盖、S06为0；I04独立得到三个2.92m平面段；S06/ST01独立投影交集2.76平方米。见geometry-recomputation.json。',
  '正例保留I01/I04无墙宿主、I08—10单一已知side-a及外侧未知、B03独立与SOURCE无建筑边；未机械增设屋顶覆盖边、I04柱宿主、S06/ST01包含或通行。完整分析在实际LPG节点/关系反序后仍相等。',
  '静态AST/文本核查run_graph：只匹配既有节点更新，更新既有关系，严格创建5条限定边；无删除/合并/DDL。固定载荷、源SHA、原生类型、旧图属性/标签/端点/类型、授权/预检/代码绑定、写前重编译、no-retry阶段、无关图/模式保护及精确读回仍在。见static-checks.json；未执行Cypher。',
  '56项逐对象接受标签明确为declared-application-obligations-passed-not-completeness-proof或snapshot-metadata-not-building-object；semanticCompleteness=not-proved、empiricalValidity=not-validated。未把技术义务检查当语义完备性证书，来源检查强度残余问题单列F03。'
 ],
 'limits':[
  '仅访问当前review2-fixed冻结包及本次review2-output产物；仅写review2-output。未读取父目录其他文件、Paper、数据库、配置/凭据、会话、技能、记忆文件或日志，未联网、未启动子agent，未调用Neo4j/Obsidian。未使用预载历史材料作为证据。',
  '指定Python加-B运行；只主动导入冻结compile_model/analyze/semantics，允许其正常只读依赖导入。禁止的run_graph、mcp_client、build_review均未导入；run_graph/build_review只读文本。build_fix和随附test_semantics未执行。',
  '所报84项为本次独立变异矩阵，不是随附测试数量；随附tests/all-tests.json不被当作本次已执行证据。另有独立聚焦复现脚本及其真实输出。',
  '未接触正式数据库，未验证Cypher计划、写入事务、正式数据库读回或恢复。静态guard审查不等于实库运行证据。',
  '未执行完整非preview审核页构建；正式数据库读回及完整构建由主会话后续实测，不伪造完成凭据。F02关闭仅针对原先JSON往返导致的确定性失败谓词。',
  '仅复审合成V01限定切片、投影和应用义务；不要求完整OWL、真实建筑有效性、真实净空/结构/通行或完整建筑语义证明；不恢复暂停研究范围。'
 ]
}
assert set(report)=={'blocking','findings','closed','checked','limits'}
assert all(set(f)=={'id','severity','issue','evidence','reproduction','recommendation'} for f in report['findings'])
write('findings.json',report)
summary=f'''独立复审结论：blocking=true；F01、F02、F04关闭，F03部分修复但仍阻塞验收4。

剩余一项medium问题：局部边的assertionSource*检查已补齐，但另一组sourceUid/sourceVersion/locator仍有漏洞。实际LPG把新边来源版本改1.1或locator改/relationships/0，完整analyze仍通过；canonical错locator也可重新编译。聚焦复现确认实际错误值已送入语义验证，不是回退rawModel。固定payload和精确数据库读回guard并未因此被证明可绕过。

独立变异矩阵84项：68拒绝，16接受。原列角色、成员端点、SRC-C01字段覆盖及局部assertion来源反例均已拒绝；未接受的新反例详见findings.json及focused-provenance-repro.json。

已通过：旧对象/原几何/关系身份端点类型和旧证据角色保留，仅增5条边；完整分析实际JSON写读往返相等，候选payload与analysis均匹配重算；六空间24边段独立几何复算一致，指定柱长、0.4、5.616、三个2.92及2.76均保持；run_graph限定更新与保护静态检查通过。manifest始末{count}项哈希及自身哈希一致。

未执行正式数据库读回或完整非preview构建，留主会话后续实测。复算脚本independent_review.py、focused_provenance_repro.py及最终报告生成脚本均保存在本目录；冻结源未改。
'''
(OUT/'summary.md').write_text(summary)
assert read(OUT/'findings.json')==report
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==end['manifest_sha256']
assert all(hashlib.sha256((FIX/i['path']).read_bytes()).hexdigest()==i['sha256'] for i in items)
print(json.dumps({'blocking':True,'open':['F03'],'closed':report['closed'],'manifestEntries':count,'manifestStartEndEqual':True,'reportReadbackVerified':True,'output':str(OUT)},ensure_ascii=False))
