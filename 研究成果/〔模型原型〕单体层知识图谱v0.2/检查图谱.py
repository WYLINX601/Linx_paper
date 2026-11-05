"""只读模型/数据/来源，验证语义约束并从数据计算查询；不修改v0.1。"""
from pathlib import Path
import json, hashlib, copy, re, datetime

P=Path(__file__).resolve().parent
def read(name): return json.loads((P/name).read_text())
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
M=read('模型定义.json'); G=read('案例图谱.json'); D=read('空间关系演示.json')
B=read('优化依据.json'); O=read('优化记录.json'); MIG=read('迁移记录.json')
OLD=json.loads((P/'../单体层知识图谱v0.1/案例图谱.json').read_text())
OLDM=json.loads((P/'../单体层知识图谱v0.1/模型定义.json').read_text())
F={x['id']:x for x in M['features']};R={x['id']:x for x in M['relations']};CL={x['id'] for x in M['classes']}
E={x['id']:x for x in B['evidence']};S={x['id']:x for x in B['sources']}
checks=[]
def check(ok,label): checks.append({'check':label,'passed':bool(ok)})
def unique(xs): return len(xs)==len({x['id'] for x in xs})
def refs(value,key):
 if isinstance(value,dict):
  for k,v in value.items():
   if k==key: yield from v
   else:yield from refs(v,key)
 elif isinstance(value,list):
  for v in value:yield from refs(v,key)
prior_refs=set(refs(OLDM,'basisRefs'))
check(all(r in E or r in prior_refs for r in refs(M,'basisRefs')),'模型依据均指向本轮证据或v0.1既有依据')
for name in ['classes','features','relations']:check(unique(M[name]),name+'标识唯一')
check(unique(B['evidence']) and unique(B['sources']),'方法来源及证据ID唯一')
for e in E.values():
 check(e['source'] in S and e['pdfPages'] and e['locator'] and e['sourceLink'],e['id']+'原文定位完整')
for s in S.values():check(Path(s['path']).is_file() and digest(s['path'])==s['sha256'],s['id']+'附件身份与哈希一致')
for o in O['changes']:
 check(all(r in E for r in o['basisRefs']),o['id']+'优化依据可解析')
 check(all(o.get(k) for k in ['before','after','rationale','implementation','validationBoundary','attribution']),o['id']+'前后变化及推断边界完整')
for f in F.values():check(set(f['domain'])<=CL,f['id']+'特征domain存在')
for r in R.values():check(set(r['domain']+r['range'])<=CL,r['id']+'关系domain/range存在')

def same_context(a,b):
 return a.get('accessContext')==b.get('accessContext') and a.get('temporalScope')==b.get('temporalScope')

def nonempty(value):
 if value is None:return False
 if isinstance(value,str):return bool(value.strip())
 if isinstance(value,(list,dict)):return bool(value)
 return True

def text(value):return isinstance(value,str) and bool(value.strip())

def iso_date(value):
 try:datetime.date.fromisoformat(value);return True
 except (TypeError,ValueError):return False

def validate(g):
 errors=[]
 def require(ok,msg):
  if not ok:errors.append(msg)
 for k in ['nodes','assertions','evidence','sources','classifications']:require(unique(g[k]),k+'重复标识')
 n={x['id']:x for x in g['nodes']};a={x['id']:x for x in g['assertions']};e={x['id']:x for x in g['evidence']};s={x['id']:x for x in g['sources']}
 synthetic=g.get('datasetKind')=='synthetic_demo'
 require(g.get('datasetKind') in ['literature_case','field_observation','synthetic_demo'],'数据集身份缺失')
 for x in n.values():
  require(x['class'] in CL,x['id']+'未知类别')
  if x['class']=='Space' and not g.get('migration'):require(all(x.get(k) for k in M['spaceIdentityContract']['requiredForNewSpace']),x['id']+'空间边界依据缺失')
  if x['class']=='GeometryRegion':
   require(all(k in x and nonempty(x[k]) for k in M['geometryContract']['required']),x['id']+'几何绑定记录缺失或为空')
   for k in ['assetUri','assetVersion','coordinateSystem','lengthUnit','mappingMethod','coverage']:require(text(x.get(k)),x['id']+'几何字段类型错误：'+k)
   require(isinstance(x.get('assetSha256'),str) and bool(re.fullmatch('[a-fA-F0-9]{64}',x['assetSha256'])),x['id']+'资产哈希格式错误')
   require(x.get('selectorType') in M['geometryContract']['selectorType'],x['id']+'区域选择器类型错误')
   require(x.get('mappingStatus') in M['geometryContract']['mappingStatus'],x['id']+'区域对应状态错误')
   selector=x.get('selector'); kind=x.get('selectorType')
   require(isinstance(selector,(str,list,dict)) and nonempty(selector),x['id']+'区域选择器内容错误')
   if kind=='bbox':
    valid=isinstance(selector,list) and len(selector) in (4,6) and all(type(v) in (int,float) for v in selector)
    require(valid and all(selector[i]<selector[i+len(selector)//2] for i in range(len(selector)//2)),x['id']+'bbox需为有效min/max坐标')
   if kind=='face_set':require(isinstance(selector,list) and bool(selector) and all(type(v)==int and v>=0 for v in selector),x['id']+'面索引需为非空非负整数列表')
  if x['class']=='AnalysisRun':
   require(all(k in x and nonempty(x[k]) for k in M['analysisRunContract']['required']),x['id']+'分析输入记录缺失或为空')
   for k in ['method','methodVersion','inputDataset','inputVersion','missingPolicy','outputKind']:require(text(x.get(k)),x['id']+'分析字段类型错误：'+k)
   inputs=x.get('inputAssertionIds');require(isinstance(inputs,list) and bool(inputs) and all(text(i) and i in a for i in inputs),x['id']+'分析输入断言不存在或为空')
   dimensions=x.get('dimensions');require(isinstance(dimensions,list) and bool(dimensions) and all(text(i) for i in dimensions),x['id']+'分析维度缺失或类型错误')
   require(isinstance(x.get('parameters'),dict) and bool(x.get('parameters')),x['id']+'分析参数需显式字典（无参数也须说明）')
   rr=x.get('results');valid_records=isinstance(rr,list) and bool(rr) and all(isinstance(r,dict) and text(r.get('id')) and text(r.get('kind')) for r in rr)
   require(valid_records,x['id']+'分析结果须为带ID与种类的非空记录列表')
   if valid_records:
    require(len(rr)==len({r['id'] for r in rr}),x['id']+'分析结果ID重复')
    for r in rr:
     if r['kind']=='similarity':
      require(text(r.get('subject')) and r['subject'] in n and text(r.get('object')) and r['object'] in n,x['id']+'相似结果端点不存在')
      require(r.get('decision') in ['similar','not_similar','unknown'],x['id']+'相似结果判断非法')
     elif r['kind']=='empty_result':require(text(r.get('scope')) and text(r.get('reason')),x['id']+'无命中结果缺范围或理由')
     else:require(text(r.get('summary')),x['id']+'其他分析结果缺说明')
   require(iso_date(x.get('executedAt')),x['id']+'分析日期格式错误')
  if 'broaderType' in x:
   b=n.get(x['broaderType'],{});require(x['class']=='TypeConcept' and b.get('class')=='TypeConcept' and b.get('scheme')==x.get('scheme'),x['id']+'上位类型越界')
 for x in e.values():
  require(x['source'] in s,x['id']+'证据来源不存在')
  if not synthetic:require(bool(x.get('pdfPages')) and bool(x.get('locator')),x['id']+'原文定位缺失')
  if x.get('image'):require((P/x['image']).is_file(),x['id']+'证据图页不存在')
 for x in a.values():
  xid=x['id'];require(all(k in x for k in M['assertionContract']['required']),xid+'必填字段缺失')
  require(x.get('subject') in n,xid+'起点不存在')
  require(('object' in x)!=('value' in x),xid+'目标/值须互斥')
  require(bool(x.get('evidence')) and all(i in e for i in x.get('evidence',[])+x.get('conflictingEvidence',[])),xid+'事实证据缺失')
  require(x.get('status') in M['assertionContract']['status'],xid+'非法状态')
  require(x.get('attribution') in M['assertionContract']['attribution'],xid+'非法归属')
  legacy=next((v for v in OLD['assertions'] if v['id']==xid),None)
  if not (g.get('migration') and legacy==x):
   require(all(text(x.get(k)) for k in M['assertionContract']['newRecordRequired']),xid+'新断言录入信息缺失')
   require(iso_date(x.get('recordedAt')),xid+'录入日期格式错误')
  if not synthetic:require(x.get('status')!='demonstration' and x.get('attribution')!='synthetic_assumption',xid+'演示数据污染研究数据')
  if synthetic:require(x.get('status')=='demonstration' and x.get('attribution')=='synthetic_assumption',xid+'演示未标身份')
  require(all(i in a for i in x.get('derivedFrom',[])),xid+'派生输入不存在')
  if 'object' in x:
   r=R.get(x['predicate']);require(bool(r) and x['object'] in n,xid+'关系或终点不存在')
   if r and x['object'] in n and x['subject'] in n:
    require(n[x['subject']]['class'] in r['domain'] and n[x['object']]['class'] in r['range'],xid+'关系域不符')
    require(all(k in x for k in r.get('requiredQualifiers',[])),xid+'关系限定条件缺失')
   if x['predicate']=='has_type':require(False,xid+'不能绕过classification直接写类型归属')
   if x['predicate']=='direct_access_to':
    via=x.get('via');require(n.get(via,{}).get('class')=='Interface',xid+'via不是界面')
    endpoints={y['object'] for y in a.values() if y['subject']==via and y['predicate']=='interface_of' and n.get(y.get('object'),{}).get('class')=='Space'}
    require(endpoints=={x['subject'],x['object']} and len(endpoints)==2,xid+'通行界面端点不匹配')
    require(all(x.get('accessContext',{}).get(k) for k in M['interfaceContract']['accessContextRequired']),xid+'通行情境缺失')
    require(not any(y['subject']==via and y['predicate']=='passage_allowed' and y.get('value') is False and same_context(x,y) for y in a.values()),xid+'与同情境禁止通行矛盾')
   if x['predicate']=='similar_to':
    run=n.get(x.get('analysisRun'),{});require(run.get('class')=='AnalysisRun',xid+'相似边缺运行依据')
    rr=run.get('results');result=next((r for r in rr if isinstance(r,dict) and r.get('id')==x.get('resultId')),None) if isinstance(rr,list) else None
    require(run.get('outputKind')=='similarity' and bool(result) and result.get('kind')=='similarity' and result.get('decision')=='similar' and result.get('subject')==x['subject'] and result.get('object')==x['object'],xid+'相似边缺对应肯定结果或端点不符')
  else:
   f=F.get(x['predicate']);require(bool(f),xid+'特征不存在')
   if f and x['subject'] in n:
    require(n[x['subject']]['class'] in f['domain'],xid+'特征域不符')
    t=type(x['value']);dt=f['datatype'];require(t==bool if dt=='boolean' else t==str if dt=='string' else t==int if dt=='integer' else t in (int,float),xid+'值型错误')
    if f.get('allowedValues'):require(x['value'] in f['allowedValues'],xid+'受控值错误')
    if f.get('unit'):require(x.get('unit')==f['unit'] and x.get('method') and x.get('scope'),xid+'单位/方法/范围缺失')
   if x['predicate']=='passage_allowed':require(all(x.get('accessContext',{}).get(k) for k in M['interfaceContract']['accessContextRequired']),xid+'通行判断情境缺失')
   if 'normalizedTerm' in x:require(x['normalizedTerm'] in {v['id'] for v in M['vocabulary']},xid+'规范词不存在')
 for predicate in ['has_space','has_element']:
  adj={}
  for x in a.values():
   if x['predicate']==predicate:adj.setdefault(x['subject'],[]).append(x['object'])
  def cycle(i,path):return i in path or any(cycle(j,path|{i}) for j in adj.get(i,[]))
  require(not any(cycle(i,set()) for i in adj),predicate+'包含循环')
 for x in n.values():
  seen=set();cur=x
  while cur.get('broaderType') in n:
   if cur['id'] in seen:require(False,x['id']+'上位类型循环');break
   seen.add(cur['id']);cur=n[cur['broaderType']]
 return errors

for label,g in [('文献案例',G),('空间演示',D)]:
 errors=validate(g);check(not errors,label+'语义约束：'+('通过' if not errors else '；'.join(errors)))
for k in MIG['preservedFacts']:check(G[k]==OLD[k],'迁移保留原事实：'+k)
for old,new in zip(OLD['evidence'],G['evidence']):check({k:v for k,v in old.items() if k!='image'}=={k:v for k,v in new.items() if k!='image'},old['id']+'证据只改相对图片路径')
for path,value in MIG['baselineFiles'].items():check(digest(P.parents[1]/path)==value,'v0.1原文件未改：'+Path(path).name)

def evaluate(g,c):
 nodes={x['id']:x for x in g['nodes']};answers=[]
 for criterion in nodes[c['type']]['criteria']:
  aa=[a for a in g['assertions'] if a['subject']==c['subject'] and a['predicate']==criterion['feature'] and 'value' in a]
  vals={json.dumps(a['value'],ensure_ascii=False) for a in aa}
  answer='unknown' if not aa or len(vals)!=1 or any(a['status']!='documented' for a in aa) else 'satisfied' if aa[0]['value']==criterion['expected'] else 'not_satisfied'
  answers.append(answer)
 decision='criteria_not_match' if 'not_satisfied' in answers else 'insufficient_evidence' if 'unknown' in answers else 'criteria_match'
 return decision,answers
for c in G['classifications']:check(evaluate(G,c)==(c['decision'],[r['result'] for r in c['criteriaResults']]),c['id']+'原分类复算不变')

def direct(g,subject):return [a for a in g['assertions'] if a['subject']==subject and a['predicate']=='direct_access_to' and a['status'] in ('documented','demonstration')]
def values(g,subject,predicate):return [a['value'] for a in g['assertions'] if a['subject']==subject and a['predicate']==predicate and 'value' in a]
def blocked_adjacent(g):
 """只返回有同一时点邻接证据、两个空间端点及明确禁止判断的界面。"""
 n={x['id']:x for x in g['nodes']}; aa=[a for a in g['assertions'] if a['status'] in ('documented','demonstration')];out=[]
 for blocked in aa:
  if blocked['predicate']!='passage_allowed' or blocked.get('value') is not False:continue
  interface=blocked['subject']
  if n.get(interface,{}).get('class')!='Interface':continue
  links=[a for a in aa if a['subject']==interface and a['predicate']=='interface_of' and a['temporalScope']==blocked['temporalScope'] and n.get(a.get('object'),{}).get('class')=='Space']
  endpoints={a['object'] for a in links}
  if len(endpoints)!=2:continue
  adjacency=[a for a in aa if a['predicate']=='adjacent_to' and {a['subject'],a['object']}==endpoints and a['temporalScope']==blocked['temporalScope']]
  if adjacency:out.append({'interface':interface,'objects':sorted(endpoints),'prohibitionAssertion':blocked['id'],'adjacencyAssertions':[a['id'] for a in adjacency],'endpointAssertions':[a['id'] for a in links],'accessContext':blocked.get('accessContext'),'evidence':sorted({e for a in [blocked]+adjacency+links for e in a['evidence']})})
 return out
guards=[]
def guard(ok,label):guards.append({'check':label,'passed':bool(ok)});check(ok,label)
bad=copy.deepcopy(D);next(a for a in bad['assertions'] if a['id']=='ACCESS_HV')['via']='I_WALL'
guard(any('端点不匹配' in e for e in validate(bad)),'错误界面不能支持堂屋至前廊通行')
bad=copy.deepcopy(D);del next(a for a in bad['assertions'] if a['id']=='ACCESS_HV')['via']
guard(any('限定条件缺失' in e for e in validate(bad)),'缺少via的通行边拒绝')
bad=copy.deepcopy(D);bad['datasetKind']='literature_case'
guard(any('演示数据污染' in e for e in validate(bad)),'合成演示不能冒充文献事实')
bad=copy.deepcopy(D);bad['assertions']=[a for a in bad['assertions'] if a['predicate']!='direct_access_to']
guard(direct(bad,'S_HALL')==[],'仅有邻接/开放/无隔断不自动生成通行')
bad=copy.deepcopy(D);bad['assertions']=[a for a in bad['assertions'] if a['id']!='PASS_WALL']
guard(values(bad,'I_WALL','passage_allowed')==[],'缺少通行判断不默认false')
bad=copy.deepcopy(D);next(a for a in bad['assertions'] if a['id']=='PASS_OPEN')['value']=False
guard(any('禁止通行矛盾' in e for e in validate(bad)),'同情境禁止通行与肯定边冲突可检出')
bad=copy.deepcopy(D);bad['nodes'].append({'id':'BAD_GEOM','class':'GeometryRegion'})
guard(any('几何绑定记录缺失' in e for e in validate(bad)),'三维锚点缺版本/区域信息拒绝')
bad=copy.deepcopy(D);bad['nodes'].append({'id':'BAD_RUN','class':'AnalysisRun'})
guard(any('分析输入记录缺失' in e for e in validate(bad)),'分析运行缺输入/参数拒绝')
bad=copy.deepcopy(D);bad['nodes'].append({**dict.fromkeys(M['geometryContract']['required']), 'id':'NULL_GEOM','class':'GeometryRegion'})
guard(any('几何绑定记录缺失或为空' in e for e in validate(bad)),'几何字段齐全但全为null仍拒绝')
bad=copy.deepcopy(D);bad['nodes'].append({**dict.fromkeys(M['analysisRunContract']['required']), 'id':'NULL_RUN','class':'AnalysisRun','inputAssertionIds':[]})
edge=next(a for a in bad['assertions'] if a['id']=='ADJ_HV');edge['predicate']='similar_to';edge['analysisRun']='NULL_RUN'
guard(any('分析输入记录缺失或为空' in e for e in validate(bad)),'空分析运行不能支持相似边')
bad=copy.deepcopy(D)
for k in M['assertionContract']['newRecordRequired']:next(a for a in bad['assertions'] if a['id']=='ACCESS_HV').pop(k,None)
guard(any('新断言录入信息缺失' in e for e in validate(bad)),'新断言缺取得方法/判断者/范围/日期拒绝')
bad=copy.deepcopy(D);next(a for a in bad['assertions'] if a['id']=='ADJ_HV')['predicate']='similar_to'
guard(any('相似边缺运行依据' in e for e in validate(bad)),'邻接边不能无依据改称分析相似')
bad=copy.deepcopy(D);bad['assertions']=[a for a in bad['assertions'] if a['id']!='ADJ_HB']
guard(blocked_adjacent(bad)==[],'缺少邻接证据不能回答相邻且禁止穿越')
bad=copy.deepcopy(D);next(a for a in bad['assertions'] if a['id']=='ACCESS_HV')['status']='disputed'
guard(direct(bad,'S_HALL')==[],'争议通行记录不作为确定可通行答案')
run={'id':'MEMORY_RUN','class':'AnalysisRun','method':'内存合成记录，仅测试结果引用','methodVersion':'guard-1','inputDataset':'synthetic_demo','inputVersion':'0.2','inputAssertionIds':['ENC_V'],'dimensions':['enclosure_degree'],'parameters':{'not_applicable':'仅验证记录关联，不执行相似计算'},'missingPolicy':'显式保留未知','outputKind':'similarity','results':[{'id':'TEST_RESULT','kind':'similarity','subject':'S_HALL','object':'S_VERANDA','decision':'similar'}],'executedAt':'2026-10-22'}
positive=copy.deepcopy(D);positive['nodes'].append(run);edge=next(a for a in positive['assertions'] if a['id']=='ADJ_HV');edge.update(predicate='similar_to',analysisRun='MEMORY_RUN',resultId='TEST_RESULT')
guard(validate(positive)==[],'有效的合成运行与肯定结果对应可接纳（不是实际分析）')
bad=copy.deepcopy(positive);bad['nodes'][-1]['results']=[None]
guard(any('带ID与种类的非空记录' in e for e in validate(bad)),'results含null不能支持相似边')
bad=copy.deepcopy(positive);bad['nodes'][-1]['results'][0]['object']='S_BED'
guard(any('相似边缺对应肯定结果' in e for e in validate(bad)),'运行结果与边端点不同不能接纳')
bad=copy.deepcopy(positive);bad['nodes'][-1]['results'][0]['decision']='not_similar'
guard(any('相似边缺对应肯定结果' in e for e in validate(bad)),'不相似结果不能生成肯定相似边')

DN={n['id']:n for n in D['nodes']}
queries=[]
def query(id,q,dataset,answer,meaning):queries.append({'id':id,'question':q,'datasetKind':dataset,'answer':answer,'interpretation':meaning})
query('Q01','周湖文献案例可给出堂屋—前廊通行吗？',G['datasetKind'],direct(G,'D_8'),'资料未覆盖；空结果不代表建筑没有通行关系。')
query('Q02','演示堂屋能直接通往哪个空间？',D['datasetKind'],[{'to':DN[a['object']]['label'],'via':DN[a['via']]['label'],'assertion':a['id'],'evidence':a['evidence']} for a in direct(D,'S_HALL')],'仅返回有明确通行断言的前廊；不由邻接推导卧室。')
query('Q03','演示中相邻但不能穿越该界面的是哪一对？',D['datasetKind'],blocked_adjacent(D),'联查同一时点的邻接、界面端点与禁止通行证据。只说明指定界面不能穿越；卧室是否有其他路径未设定。')
query('Q04','前廊能否同时有名称、围合程度和多个用途？',D['datasetKind'],{p:values(D,'S_VERANDA',p) for p in ['local_space_name','enclosure_degree','space_use']},'各轴分别记录；不是互斥总分类。')
query('Q05','两个案例的分类判断是否改变？',G['datasetKind'],[{'id':c['id'],'decision':evaluate(G,c)[0],'criteria':evaluate(G,c)[1]} for c in G['classifications']],'沿用四项判据；未改变原有分类事实。')
query('Q06','原屋面记载冲突是否保留？',G['datasetKind'],[{'id':a['id'],'value':a.get('value'),'evidence':a['evidence'],'conflictingEvidence':a.get('conflictingEvidence',[])} for a in G['assertions'] if a['status']=='disputed'],'保留原表值与冲突来源，不替作者裁决。')
query('Q07','真实文献案例是否已经关联三维区域？',G['datasetKind'],[n['id'] for n in G['nodes'] if n['class']=='GeometryRegion'],'无实际绑定；本轮只完善接口与记录约束。')
query('Q08','是否已经计算民居相似或聚类？',G['datasetKind'],[n['id'] for n in G['nodes'] if n['class']=='AnalysisRun'],'尚未运行分析；模型支持不等于分析完成。')
query('Q09','两类数据的事实是否都能回到各自来源？','dataset_audit',{g['datasetKind']:{'assertions':len(g['assertions']),'all_resolvable':all(a['evidence'] and all(e in {x['id'] for x in g['evidence']} for e in a['evidence']) for a in g['assertions'])} for g in [G,D]},'演示回到场景定义，文献事实回到原文，不能互作证据。')
query('Q10','十项优化是否都有依据与迁移边界？','model_audit',[{'id':o['id'],'basisRefs':o['basisRefs'],'status':o['status'],'validationBoundary':o['validationBoundary']} for o in O['changes']],'所有字段规则均为研究者优化；不冒充作者原本体或实证结论。')
result={'ok':all(x['passed'] for x in checks),'date':'2026-10-22','counts':{'classes':len(CL),'features':len(F),'relations':len(R),'methodSources':len(S),'methodEvidence':len(E),'changes':len(O['changes']),'literatureNodes':len(G['nodes']),'literatureAssertions':len(G['assertions']),'demoNodes':len(D['nodes']),'demoAssertions':len(D['assertions'])},'checks':checks,'semanticGuards':guards,'queries':queries,'errors':[x['check'] for x in checks if not x['passed']],'limits':'程序核验结构、迁移一致性和查询行为；原文抽核另记。没有田野验证、OWL一致性推理或真实三维绑定。'}
(P/'验证结果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
diff=[]
for group in ['classes','features','relations']:
 before={x['id']:x for x in OLDM[group]};after={x['id']:x for x in M[group]}
 for key in sorted(before.keys()|after.keys()):
  if before.get(key)!=after.get(key):diff.append({'path':group+'[id='+key+']','kind':'added' if key not in before else 'removed' if key not in after else 'modified','changeRefs':after.get(key,{}).get('changeRefs',[]),'before':before.get(key),'after':after.get(key)})
for key in sorted(OLDM.keys()|M.keys()):
 if key not in ['classes','features','relations'] and OLDM.get(key)!=M.get(key):diff.append({'path':key,'kind':'added' if key not in OLDM else 'modified','before':OLDM.get(key),'after':M.get(key)})
(P/'模型差异记录.json').write_text(json.dumps({'from':'0.1','to':'0.2','recordedAt':'2026-10-22','note':'检查脚本从两个版本模型逐字段比较生成；不是新的建筑观察记录。','changes':diff},ensure_ascii=False,indent=2)+'\n')
md='# 查询与程序核验\n\n数据来自同目录JSON；运行 `python3 检查图谱.py` 可复算。此文由脚本生成，不作独立事实源。\n\n'
md+=f"程序结果：{'通过' if result['ok'] else '未通过'}；{len(checks)}项检查，含{len(guards)}项内存防错试验。原文审查和GUI验收另见独立记录。\n\n"
for q in queries:md+=f"## {q['id']} {q['question']}\n\n数据身份：{q['datasetKind']}。{q['interpretation']}\n\n```json\n{json.dumps(q['answer'],ensure_ascii=False,indent=2)}\n```\n\n"
md+='## 验证边界\n\n'+result['limits']+' 原文献14节点、27断言、4次分类不变；空间演示单独统计。\n'
(P/'查询与验收.md').write_text(md)
print(json.dumps({'ok':result['ok'],'checks':len(checks),'guards':len(guards),'queries':len(queries),'errors':result['errors']},ensure_ascii=False))
raise SystemExit(0 if result['ok'] else 1)
