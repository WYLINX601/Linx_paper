"""从候选模型生成阅读表、候选定义图载荷和查询入口；不写数据库。"""
import json,csv,hashlib,re
from pathlib import Path
B=Path(__file__).resolve().parent
D=json.loads((B/'候选模型.json').read_text());NS=D['namespace'];HASH=hashlib.sha256((B/'候选模型.json').read_bytes()).hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,sort_keys=True)
def cell(v):
 if isinstance(v,(dict,list)):v=js(v)
 return str(v).replace('|','／').replace('\n','<br>')
def table(name,rows,cols,lead):
 text='# '+name+'\n\n'+lead+'\n\n| '+' | '.join(n for _,n in cols)+' |\n| '+' | '.join('---' for _ in cols)+' |\n'
 text+='\n'.join('| '+' | '.join(cell(r.get(k,'')) for k,_ in cols)+' |' for r in rows)+'\n'
 (B/(name+'.md')).write_text(text)
 with (B/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow([n for _,n in cols]);w.writerows([[js(r.get(k,'')) if isinstance(r.get(k,''),(list,dict)) else r.get(k,'') for k,_ in cols] for r in rows])
lead='2026-10-23。研究者候选设计；来源条目ID对应原100条，不代表原作者直接提出此数据模型。完整定义和记录协议以候选模型.json为准。'
table('01-实体定义表',D['entities'],[('id','ID'),('label','实体概念'),('definition','定义与边界'),('identityRule','识别规则'),('collectionGate','建实例门槛'),('action','对旧模型处理'),('sourceItems','来源条目')],lead)
table('02-属性字典',D['fields'],[('id','字段ID'),('label','属性/记录项'),('domain','描述对象'),('valueKind','知识性质'),('datatype','类型'),('unit','单位'),('definition','定义和口径'),('allowedValues','取值'),('cardinality','多值规则'),('subFields','复合字段子项'),('requiredSubFields','协议要求子项'),('collection','采集方式'),('storage','保存方式'),('missing','未知规则'),('sourceItems','来源条目')],lead+' domain为被描述对象，不能仅因结果存在AnalysisRun中就把它当建筑自身实体。属性记录携带来源与时点，量值不直接覆盖实体。')
table('03-关系字典',D['relations'],[('id','关系ID'),('label','关系名'),('domain','起点类型'),('range','终点类型'),('definition','语义及条件'),('layer','事实/分析层'),('qualifiers','必需限定'),('cardinality','多重性'),('symmetric','对称'),('transitive','传递'),('counterexample','不成立示例'),('action','调整方式'),('sourceItems','来源条目')],lead+' 起点/终点给出允许对象类型，具体关系仍须满足条件；不是看到两类节点就可以连边。')
table('04-分析问题与支撑',D['questions'],[('id','问题ID'),('question','分析问题'),('entities','实体'),('fields','字段'),('relations','关系'),('method','操作与限制'),('output','结果形式'),('inputPolicy','运行前要求'),('sourceItems','研究条目')],lead+' 12项均为拟分析问题，未执行样本计算。字段集合是候选输入目录，不代表每项字段均为同一运算的必需项。')
rows=[]
for m in D['itemMappings']:
 r=dict(m);r.update(title=m['source']['研究内容'],adoption=m['source']['采用建议'],evidence=m['source']['依据ID'],locator=m['source']['原文定位'],evidenceStatus=m['source']['来源证据状态']);rows.append(r)
table('05-原100条去向与依据',rows,[('item','原编号'),('title','研究内容'),('adoption','原采用状态'),('handling','本轮处理'),('entities','实体'),('profiles','实体部分profile'),('fields','属性'),('relations','关系'),('recordProfiles','记录profile'),('questions','分析问题'),('recordRequirements','记录要求'),('derivationRequirements','派生规则与门槛'),('reason','设计理由'),('evidence','原依据ID'),('locator','定位'),('evidenceStatus','原核读状态')],lead+' 全部保留原顺序；研究规则或暂缓项也保留明确去向。设计推导不升级原文证据状态。')
table('06-现有模型调整记录',D['modelChanges'],[('kind','类别'),('oldId','旧ID'),('newIds','候选ID'),('action','处理'),('reason','理由'),('sourceItems','来源条目')],lead+' 不改动旧kgv02实例。新增候选命名空间用于审阅与验证；当前本体迁移未执行。')
# graph metadata: explicit definition labels, never actual dwelling instance labels
nodes=[];edges=[]
def node(kind,id,name,data):
 uid=NS+kind+':'+id
 props={'uid':uid,'id':id,'name':name,'kind':kind,'datasetKind':'candidate_model','modelVersion':D['version'],'status':'candidate','sourceHash':HASH,'definitionJson':js(data)}
 for k,val in data.items():
  if k not in props and isinstance(val,(str,int,float,bool)):props[k]=val
 nodes.append({'uid':uid,'label':kind,'properties':props});return uid
def uid(kind,id):return NS+kind+':'+id
def edge(a,t,z,props=None):
 ekey=a+'|'+t+'|'+z+'|'+js(props or {})
 edges.append({'from':a,'to':z,'type':t,'properties':{'linkId':hashlib.sha256(ekey.encode()).hexdigest(),**(props or {})}})
root=node('ModelVersion','root','单体层候选语义模型 v0.1',{'scope':D['scope'],'principles':D['principles'],'recordContracts':D['recordContracts']})
for coll,kind,labelkey in [('entities','ModelEntityType','label'),('elementProfiles','ModelElementProfile','label'),('fields','ModelProperty','label'),('relations','ModelRelation','label'),('recordProfiles','ModelRecordProfile','label'),('questions','ModelAnalysisQuestion','question')]:
 for x in D[coll]:
  n=node(kind,x['id'],x[labelkey],x);edge(root,'DEFINES',n)
  for item in x.get('sourceItems',[]):edge(n,'DESIGN_FROM_ITEM',uid('ModelResearchItem',item),{'meaning':'研究者设计依据，非作者原模型等价'})
for m in D['itemMappings']:
 n=node('ModelResearchItem',m['item'],m['item']+' '+m['source']['研究内容'],m);edge(root,'COVERS_ITEM',n)
 for key,kind,typ in [('entities','ModelEntityType','USES_ENTITY_TYPE'),('fields','ModelProperty','USES_PROPERTY'),('relations','ModelRelation','USES_RELATION'),('profiles','ModelElementProfile','USES_PROFILE'),('recordProfiles','ModelRecordProfile','USES_RECORD_PROFILE')]:
  for id in m[key]:edge(n,typ,uid(kind,id))
 for e in m['source']['依据ID'].split(';'):edge(n,'REFERENCES_EVIDENCE',uid('ModelEvidenceReference',e))
evidences={}
for m in D['itemMappings']:
 for e in m['source']['依据ID'].split(';'):
  x=evidences.setdefault(e,{'id':e,'sourceItems':[],'locators':[],'statuses':[],'provenance':'复用原框架索引；本轮未新读PDF；依据支持原研究内容，不能直接证明新模型设计'})
  x['sourceItems'].append(m['item'])
  # full source row retained per item; avoid falsely attributing all locators to each evidence id
  x['locators'].append({'item':m['item'],'combinedOriginalLocator':m['source']['原文定位']})
  x['statuses'].append({'item':m['item'],'combinedOriginalStatus':m['source']['来源证据状态']})
for e,x in evidences.items():node('ModelEvidenceReference',e,e,x)
for f in D['fields']:
 for dom in f['domain']:edge(uid('ModelEntityType',dom),'HAS_PROPERTY',uid('ModelProperty',f['id']))
for r in D['relations']:
 for dom in r['domain']:edge(uid('ModelEntityType',dom),'ALLOWS_RELATION',uid('ModelRelation',r['id']))
 for ran in r['range']:edge(uid('ModelRelation',r['id']),'TO_TYPE',uid('ModelEntityType',ran))
for p in D['elementProfiles']:edge(uid('ModelElementProfile',p['id']),'PROFILE_OF',uid('ModelEntityType','Element'))
for q in D['questions']:
 for key,kind,t in [('fields','ModelProperty','REQUIRES_PROPERTY'),('relations','ModelRelation','REQUIRES_RELATION'),('entities','ModelEntityType','INVOLVES_TYPE')]:
  for id in q[key]:edge(uid('ModelAnalysisQuestion',q['id']),t,uid(kind,id))
 for item in q['sourceItems']:edge(uid('ModelAnalysisQuestion',q['id']),'ANALYSES_ITEM',uid('ModelResearchItem',item))
for j,x in enumerate(D['modelChanges'],1):
 nid=node('ModelDecision',f'D{j:03}',x['action']+' '+str(x.get('oldId') or ','.join(x['newIds'])),x);edge(root,'HAS_DECISION',nid)
 kind={'class':'ModelEntityType','feature':'ModelProperty','relation':'ModelRelation'}[x['kind']]
 for target in x['newIds']:edge(nid,'PROPOSES_DEFINITION',uid(kind,target))
for x in D['openIssues']:
 n=node('ModelOpenIssue',x['id'],x['issue'],x);edge(root,'HAS_OPEN_ISSUE',n)
unique={e['properties']['linkId']:e for e in edges};edges=list(unique.values())
assert len({n['uid'] for n in nodes})==len(nodes)
keys={n['uid'] for n in nodes};assert all(e['from'] in keys and e['to'] in keys for e in edges)
payload={'namespace':NS,'sourceHash':HASH,'nodes':nodes,'edges':edges,'boundary':'只登记候选定义；不生成Dwelling/Space/Element实例或实例关系，不写kgv02命名空间'}
(B/'Neo4j候选层载荷.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
queries={
'入口与待定项':"MATCH p=(v:ModelVersion {uid:'kgmodel:single:v01:ModelVersion:root'})-[:HAS_OPEN_ISSUE]->() RETURN p",
'实体关系总览':"MATCH p=(a:ModelEntityType)-[:ALLOWS_RELATION]->(r:ModelRelation)-[:TO_TYPE]->(b:ModelEntityType) WHERE a.uid STARTS WITH 'kgmodel:single:v01:' AND r.id IN ['has_building','has_space','has_element','bounds','has_surface','interface_of','realized_by'] RETURN p",
'查看空间属性':"MATCH p=(t:ModelEntityType {uid:'kgmodel:single:v01:ModelEntityType:Space'})-[:HAS_PROPERTY]->(f) RETURN p",
'查看体量错落依据':"MATCH p=(i:ModelResearchItem {uid:'kgmodel:single:v01:ModelResearchItem:B402'})-[r:USES_ENTITY_TYPE|USES_PROPERTY|USES_RELATION|REFERENCES_EVIDENCE]->() RETURN p",
'堂屋前廊关系设计':"MATCH p=(r:ModelRelation)-[:TO_TYPE]->(t:ModelEntityType) WHERE r.uid STARTS WITH 'kgmodel:single:v01:' AND r.id IN ['adjacent_to','direct_access_to','interface_of','realized_by'] RETURN p",
'某个分析需要什么':"MATCH p=(q:ModelAnalysisQuestion {uid:'kgmodel:single:v01:ModelAnalysisQuestion:Q03'})-[r:REQUIRES_PROPERTY|REQUIRES_RELATION|ANALYSES_ITEM]->() RETURN p",
'属性完整字典':"MATCH (p:ModelProperty) WHERE p.uid STARTS WITH 'kgmodel:single:v01:' RETURN p.id,p.name,p.definition,p.datatype,p.unit,p.storage ORDER BY p.id",
'原条目证据定位':"MATCH (i:ModelResearchItem {uid:'kgmodel:single:v01:ModelResearchItem:B402'}) RETURN i.definitionJson",
'候选版本数量':"MATCH (n:ModelDefinition) WHERE n.uid STARTS WITH 'kgmodel:single:v01:' RETURN n.kind,count(*) ORDER BY n.kind"}
(B/'浏览查询.json').write_text(json.dumps(queries,ensure_ascii=False,indent=2))
(B/'浏览查询.cypher').write_text('\n\n'.join('// '+name+'\n'+q+';' for name,q in queries.items())+'\n')
(B/'浏览指南.md').write_text('# 在Neo4j中查看候选模型\n\n打开[Neo4j Browser](http://100.68.38.32:7474/browser/)，沿用现有登录。以下查询使用图形视图；点击节点查看属性，完整字典在definitionJson。模型节点用Model开头标签，datasetKind=candidate_model，不属于真实民居样本。\n\n建议先看实体关系总览，再看某实体属性、某分析依赖，避免一次展示数千条边。若节点显示ID，可在Browser样式中把caption设为name。\n\n'+ '\n\n'.join('## '+name+'\n\n```cypher\n'+q+'\n```' for name,q in queries.items())+'\n\n这些查询展示设计定义，不计算真实民居特征；模型字典中关系域、证据与时点条件仍须遵守。\n')
(B/'README.md').write_text('''# 单体层实体—属性—关系候选模型 v0.1

2026-10-23。按用户最新要求以Neo4j候选模型层作为关系展示，不生成Drawio。此成果是模型设计定义，尚不是实测建筑数据或正式迁移。

- [Neo4j浏览指南](浏览指南.md)：实体关系、属性、分析依赖、依据追溯的查询入口。
- [实体定义表](01-实体定义表.md)
- [属性字典](02-属性字典.md)
- [关系字典](03-关系字典.md)
- [分析问题与支撑](04-分析问题与支撑.md)
- [原100条去向与依据](05-原100条去向与依据.md)
- [现有模型调整记录](06-现有模型调整记录.md)

各表同名CSV用于筛选，均从[候选模型.json](候选模型.json)生成。JSON是本轮唯一合并维护源；`设计约定.json`与`关系与分析设计.json`是形成过程记录，不作为后续修改入口。Neo4j载荷由维护源派生，数据库中的本轮节点保存源哈希和完整定义，不另行手工维护第二套模型。

实体概念包含建筑对象、分类概念及分析对象；Element的15个profiles区分体量、系统、构架和构件种类，不表示另建15个互斥本体类。同一实物不因多种描述建立重复身份。字段里复合记录保留subFields和requiredSubFields；domain表示被描述对象，保存到AnalysisResult或Assertion不改变其描述对象。

属性、关系与原条目的连接表示研究者建模依据；原文证据引用状态完整保留，不声称原论文提出本候选本体。所有100条有去向，B512/B621继续暂缓。拟新增Building、Surface、ReferenceFrame、ActorGroup均需试采确认。现有类型判定投影和承重布尔的局限登记为待解决事项，未覆盖旧实例。

本轮只在kgmodel:single:v01:命名空间登记ModelEntityType、ModelProperty、ModelRelation等定义节点。既有kgv02实例、文献和演示数据不迁移，不增设虚构民居。入库数量、逐记录回读与旧数据保护见[修订与验收](修订与验收.md)，子agent审核范围和结论见[独立审核](独立审核.md)。模型定义可浏览不代表分析已运行。

本次细化仍处于既有“语义建模—采集—查询比较”研究路径内，未更改总体对象、主线或阶段；保留原研究路径图。本轮取消的是新增概念关系Drawio图，使用Neo4j直接展示。
''')
print(json.dumps({'nodes':len(nodes),'edges':len(edges),'sourceHash':HASH},ensure_ascii=False))
