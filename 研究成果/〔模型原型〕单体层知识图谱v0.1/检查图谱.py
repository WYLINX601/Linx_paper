"""只读输入，重算本轮图谱约束、分类和查询；写验证结果及案例报告。"""
import json, pathlib, copy
P=pathlib.Path(__file__).resolve().parent
model=json.loads((P/'模型定义.json').read_text());g=json.loads((P/'案例图谱.json').read_text())
errors=[]; checks=[]
def check(ok,msg):
 checks.append({'check':msg,'passed':bool(ok)})
 if not ok: errors.append(msg)
def index(xs):
 check(len(xs)==len({x['id'] for x in xs}),'标识唯一：'+str(len(xs)))
 return {x['id']:x for x in xs}
N=index(g['nodes']); A=index(g['assertions']); E=index(g['evidence']); S=index(g['sources']); C=index(g['classifications'])
classes={x['id'] for x in model['classes']}; F={x['id']:x for x in model['features']}; R={x['id']:x for x in model['relations']}
for n in N.values(): check(n['class'] in classes,n['id']+'概念存在')
for e in E.values():
 check(e['source'] in S and bool(e['pdfPages']) and bool(e['locator']),e['id']+'来源及页图定位')
 check((P/e['image']).is_file(),e['id']+'图页存在')
for a in A.values():
 check(all(k in a for k in model['assertionContract']['required']),a['id']+'必填项')
 check(('object' in a)!=('value' in a),a['id']+'目标/值互斥')
 check(a['subject'] in N and bool(a['evidence']) and all(e in E for e in a['evidence']+a.get('conflictingEvidence',[])),a['id']+'对象及证据存在')
 check(a['attribution'] in model['assertionContract']['attribution'] and a['status'] in model['assertionContract']['status'],a['id']+'归属及状态合法')
 if 'object' in a:
  d=R.get(a['predicate']);check(bool(d) and a['object'] in N,a['id']+'关系及终点存在')
  if d and a['object'] in N:check(N[a['subject']]['class'] in d['domain'] and N[a['object']]['class'] in d['range'],a['id']+'关系方向及对象类别')
 else:
  f=F.get(a['predicate']); check(bool(f),a['id']+'特征存在')
  if f:
   check(N[a['subject']]['class'] in f['domain'],a['id']+'特征对象类别')
   dt=f['datatype'];v=a['value'];valid=(type(v)==bool if dt=='boolean' else type(v)==str if dt=='string' else type(v)==int if dt=='integer' else type(v) in [int,float])
   check(valid,a['id']+'值型')
   if f.get('unit'):check(a.get('unit')==f['unit'] and bool(a.get('method')) and bool(a.get('scope')),a['id']+'数值单位与口径')
 check(all(x in A for x in a.get('derivedFrom',[])),a['id']+'推断输入存在')

def has_cycle(predicate):
 adj={}
 for a in A.values():
  if a['predicate']==predicate:adj.setdefault(a['subject'],[]).append(a['object'])
 def visit(n,path):return n in path or any(visit(x,path|{n}) for x in adj.get(n,[]))
 return any(visit(n,set()) for n in adj)
for p in ['has_space','has_element']:check(not has_cycle(p),p+'无包含循环')

def evaluate(subject,typ,assertions):
 results=[]
 for cr in N[typ]['criteria']:
  aa=[a for a in assertions if a['subject']==subject and a['predicate']==cr['feature'] and 'value' in a]
  vals={json.dumps(a['value'],ensure_ascii=False) for a in aa}
  if not aa or len(vals)!=1 or any(a['status']!='documented' for a in aa):r='unknown'
  else:r='satisfied' if aa[0]['value']==cr['expected'] else 'not_satisfied'
  results.append(r)
 dec='criteria_not_match' if 'not_satisfied' in results else 'insufficient_evidence' if 'unknown' in results else 'criteria_match'
 return dec,results
for c in C.values():
 check(all(k in c for k in model['classificationContract']['required']),c['id']+'判断必填')
 check(c['subject'] in N and c['type'] in N and N[c['type']]['class']=='TypeConcept',c['id']+'判断对象和类型')
 check(c['scheme'] in N and c['scheme']==N[c['type']]['scheme'],c['id']+'分类体系一致')
 check(bool(c['evidence']) and all(x in E for x in c['evidence']),c['id']+'判断证据存在')
 expected=evaluate(c['subject'],c['type'],list(A.values()))
 check((c['decision'],[r['result'] for r in c['criteriaResults']])==expected,c['id']+'独立重算结果一致')
 for r in c['criteriaResults']:
  aid=r.get('assertion');check(aid is None or (aid in A and A[aid]['subject']==c['subject'] and A[aid]['predicate']==r['feature']),c['id']+'/'+r['criterion']+'输入对象/维度一致')
check(not any(a['predicate']=='has_type' for a in A.values()),'领域断言没有绕过分类判断的裸has_type')
check(all(a['subject'].startswith('R_') for a in A.values() if a['predicate'] in ['load_bearing','rear_courtyard_form','column_bay_form','roof_layered']),'四项侧样特征只落记录，不传播全栋')
check(not any(a['predicate'] in ['direct_access_to','supports','anchored_to'] for a in A.values()),'没有将未有案例证据的通行/支承/三维关系实例化')

# 语义防错试验在内存进行，不修改案例数据。
fixtures=copy.deepcopy(list(A.values()))
for a in fixtures:
 if a['subject']=='R_8' and a['predicate']=='column_bay_form':a['value']='五柱四筒'
guard=[]
def guardcheck(ok,label):guard.append({'check':label,'passed':bool(ok)});check(ok,label)
guardcheck(evaluate('R_8','T_PROTO',fixtures)[0]=='criteria_match','四项齐备一致可匹配（仅内存合成防错输入）')
missing=[a for a in fixtures if a['id']!='F_8_load_bearing']
guardcheck(evaluate('R_8','T_PROTO',missing)[0]=='insufficient_evidence','缺失不按false处理')
changed=copy.deepcopy(fixtures)
next(a for a in changed if a['id']=='F_8_load_bearing')['value']=True
guardcheck(evaluate('R_8','T_PROTO',changed)[0]=='criteria_not_match','明确否定和true值可以区分')
conflicted=copy.deepcopy(fixtures);extra=copy.deepcopy(next(a for a in conflicted if a['id']=='F_8_load_bearing'));extra['value']=True;extra['id']='MEMORY_ONLY';conflicted.append(extra)
guardcheck(evaluate('R_8','T_PROTO',conflicted)[0]=='insufficient_evidence','相反断言不被任意选择')
uncertain=copy.deepcopy(fixtures);next(a for a in uncertain if a['id']=='F_8_load_bearing')['status']='disputed'
guardcheck(evaluate('R_8','T_PROTO',uncertain)[0]=='insufficient_evidence','争议断言暂停确定匹配')

comparison=[]
for fid in ['load_bearing','rear_courtyard_form','column_bay_form','roof_layered']:
 aa=[next(a for a in A.values() if a['subject']==r and a['predicate']==fid) for r in ['R_8','R_1']]
 comparison.append({'feature':fid,'label':F[fid]['label'],'values':[a['value'] for a in aa],'statuses':[a['status'] for a in aa],'assertions':[a['id'] for a in aa],'evidence':sorted({e for a in aa for e in a['evidence']+a.get('conflictingEvidence',[])})})
queries=[
 {'id':'Q1','question':'这两条记录属于什么柱筒类别？','answer':[{ 'record':N[c['subject']]['label'],'type':N[c['type']]['label'],'judgement':c['id']} for c in C.values() if c['scheme']=='SC_COLUMN' and c['decision']=='criteria_match']},
 {'id':'Q2','question':'在原表的四个侧样维度上有何差异？','answer':comparison},
 {'id':'Q3','question':'满足2023论文原型的四项组合吗？','answer':[{'record':N[c['subject']]['label'],'decision':c['decision'],'criteria':[{'feature':r['feature'],'result':r['result']} for r in c['criteriaResults']],'judgement':c['id']} for c in C.values() if c['scheme']=='SC_PROTO']},
 {'id':'Q4','question':'能否追溯全部断言与分类判断？','answer':{'assertions':len(A),'classifications':len(C),'all_have_resolvable_evidence':all(a['evidence'] and all(e in E for e in a['evidence']) for a in list(A.values())+list(C.values())),'unresolved_source_conflicts':len(g.get('conflicts',[]))}},
 {'id':'Q5','question':'能否查房间通行与具体构件支承链？','answer':{'direct_access_edges':sum(a['predicate']=='direct_access_to' for a in A.values()),'support_edges':sum(a['predicate']=='supports' for a in A.values()),'meaning':'资料未覆盖；不能解释为建筑没有这些关系。'}},
 {'id':'Q6','question':'能否给出历时演变和三维区域？','answer':{'change_events':sum(n['class']=='ChangeEvent' for n in N.values()),'geometry_regions':sum(n['class']=='GeometryRegion' for n in N.values()),'meaning':'本轮没有相关个案证据，接口尚未实例化。'}}
]
result={'ok':not errors,'date':'2026-10-22','counts':{'classes':len(classes),'features':len(F),'relation_definitions':len(R),'case_nodes':len(N),'assertions':len(A),'classification_judgements':len(C),'evidence':len(E),'candidate_relations':sum(a['status']=='tentative' for a in A.values()),'unresolved_source_conflicts':len(g.get('conflicts',[]))},'checks':checks,'semantic_guard_tests':guard,'queries':queries,'errors':errors,'limits':'数据语义约束与定向原文证据检查；不证明分类理论有效性、全县覆盖或实地现状。'}
(P/'验证结果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
def val(v):return '是' if v is True else '否' if v is False else str(v)
md='''# 文献案例试表达与查询检验

对象是赵潇诺学位论文表3.7的周湖8号、1号。二者只有本篇编号与底图定位，本轮不确认正式宅名、独立住宅边界、地址、观测日期或2026年现状。用两条源内记录验证表达方法，不能称为完整的景宁单体样本建库。

原文：Zotero [学位论文](zotero://select/library/items/ZWDJJE99)；[2023侧样研究](zotero://select/library/items/83W7CJW2)。通过Zotero MCP核对附件后，页读取器报错，实际采用本地PDF解析及原页视觉核对。学位论文的2022封面日期、Zotero日期与实际调查日期分开；本轮调查日期未知。

## 确认可填的四个维度

| 侧样维度 | 周湖8号记录 | 周湖1号记录 | 依据 |
|---|---|---|---|
'''
for r in comparison:md+=f"| {r['label']} | {val(r['values'][0])} | {val(r['values'][1])}{'（表值；叙述有待核不一致）' if 'disputed' in r['statuses'] else ''} | 表3.7，PDF55／印刷44 |\n"
md+='''
[原表图页](证据图页/ZWDJJE99-PDF55.png) · [源内编号定位](证据图页/ZWDJJE99-PDF56.png)

四个字段保存在侧样记录R_8/R_1上，查询民居时需经过represented_by关系查看，不直接继承为全栋事实。五柱五筒/五柱六筒不是整栋柱数；一字形/方形只指后厨天井。

## 已实例化的图谱层次

2个来源内民居对象、2条侧样记录、1个地点接口、2个候选天井空间、2个候选院墙部位，以及分类体系和类型概念。候选空间/部位由表列字段拆分，相关8条关系标为读者建模推断、tentative。它们没有几何边界，也没有被补造通行或支承关系。

“空间存在”与“空间通行图完整”是两个不同层次。本轮只能支持前者的候选表达。所有未知见图谱gaps；这暴露出下一轮需要身份明确的完整平剖面和现场核验。

## 分类判断实际结果

'''
for c in C.values():
 rs=c['criteriaResults'];sat=sum(r['result']=='satisfied' for r in rs);no=sum(r['result']=='not_satisfied' for r in rs);un=sum(r['result']=='unknown' for r in rs)
 label={'criteria_match':'匹配','criteria_not_match':'不匹配','insufficient_evidence':'证据不足'}[c['decision']]
 md+=f"- {N[c['subject']]['label']} → {N[c['type']]['label']}：**{label}**；{sat}项满足、{no}项不满足、{un}项待核。判断ID：{c['id']}。\n"
md+='''
原型四项条件来自[期刊原页PDF5／印刷14](证据图页/83W7CJW2-PDF5.png)。这里把作者文字操作化成合取判据，进行跨来源的读者试判；还未完成两篇所有测绘口径的核对。8号的柱筒组合是五柱五筒，与原型五柱四筒不同，即使其他三项相同，也不判为整个原型。1号存在其他明确不符项，即使屋面项待核，整体合取仍不匹配。不匹配仅针对这四个条件，不能据此宣称历史上不是某种原型的衍化，也不用于排除研究样本。

## 原文内部不一致如何处理

表3.7中1号屋面分层为“是”；[PDF63／印刷52的常见型概括](证据图页/ZWDJJE99-PDF63.png)却将1—4号指向“屋架不分层”等特征，且4号其他字段也与概括不尽一致。本轮同时保留两处措辞和范围，不替作者纠正。

因此，1号屋面表值仍可作为“原表如何记载”的答案，但断言状态为disputed，原型判据取unknown。常见型的组级描述没有被直接赋为第二条已确认单体false值。来源内冲突没有被统计平均或覆盖。完整记录见CONFLICT_1。

## 查询覆盖与防错检查

Q1已从分类记录查询柱筒类别；Q2已读取同表特征对照；Q3独立重算四项原型判据；Q4核对每条断言与分类的来源定位。Q5房间通行与支承链、Q6历时变化与三维区域均返回“资料未覆盖”，并非“建筑不存在这些关系”。

防错检验在内存构造输入，不写入真实案例：齐备一致可匹配、缺失不视为false、true/false区分、相反断言不任意择一、争议项暂停确定匹配。结果和所有查询答案见[验证结果](验证结果.json)。运行检查图谱.py可重新计算；不需要安装图数据库。

## 这次试建带来的修订

1. 单体与文献表述必须分开，否则四项侧样特征容易被误当整栋属性。
2. 通过原文表列可以先拆出候选空间/部位，但只有补齐图纸后才能确定其边界和相互关系。
3. 类型判定需要比“属于某类型”更多的信息：判据、输入、比较范围和未知/冲突状态都必须保留。
4. 完整单体空间图谱的下一步材料是本号可确认的平面/剖面/部位对应、尺度与日期，不是继续用通用类型示意填空。

本轮证明的是这些记录能被组织、追溯和执行有限判断，尚未验证模型的普适性、实地可采集性或三维关联效果。
'''
(P/'案例与查询检验.md').write_text(md)
print(json.dumps({'ok':not errors,'counts':result['counts'],'checks':len(checks),'semantic_guards':len(guard),'errors':errors},ensure_ascii=False))
raise SystemExit(0 if not errors else 1)
