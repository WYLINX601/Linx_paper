import json,hashlib,re,csv
from pathlib import Path
B=Path(__file__).resolve().parent;V=B.parent.parent
def read(p):return json.loads(p.read_text())
d=read(B/'候选模型.json');src=read(V/'研究成果/〔方法衔接〕建筑单体框架-本体与分析衔接v0.1/衔接拆解.json');payload=read(B/'Neo4j候选层载荷.json');errs=[]
def check(x,m):
 if not x:errs.append(m)
ids={key:{x['id'] for x in d[key]} for key in ['entities','elementProfiles','fields','relations','recordProfiles','questions']};items={x['id']:x for x in src['items']}
for k,s in ids.items():check(len(s)==len(d[k]),'重复ID '+k)
check([m['item'] for m in d['itemMappings']]==list(items),'原100条顺序/覆盖')
for m in d['itemMappings']:
 i=m['item'];s=items[i];check(m['source']==s['original'],i+' 原行变化');check(m['originalInputDependencies']==s['inputs'],i+' 原输入依赖变化');check(m['derivationRequirements']==s['derivations'],i+' 原派生规则变化')
 for key,target in [('entities','entities'),('profiles','elementProfiles'),('fields','fields'),('relations','relations'),('questions','questions'),('recordProfiles','recordProfiles')]:check(set(m[key])<=ids[target],i+' 引用不明 '+key)
 check(bool(m['recordRequirements']) and bool(m['reason']),i+' 无处理理由')
 if i in ['B512','B621']:check(m['handling']=='暂缓' and not m['fields'],i+' 待核专题变成采集字段')
for k in ['entities','elementProfiles','fields','relations','recordProfiles','questions']:
 for x in d[k]:
  check(bool(x.get('sourceItems')) and set(x['sourceItems'])<=set(items),x['id']+' 来源条目')
for f in d['fields']:
 check(set(f['domain'])<=ids['entities'],f['id']+' field domain')
 check(all(f.get(k) for k in ['definition','datatype','unit','missing','collection','storage','status']),f['id']+' 字典不完整')
 if f['datatype']=='object':check(bool(f.get('subFields')) and set(f.get('requiredSubFields',[]))<=set(f['subFields']),f['id']+' 复合结构未定义')
for r in d['relations']:
 check(set(r['domain'])<=ids['entities'] and set(r['range'])<=ids['entities'],r['id']+' relation endpoint')
 check(bool(r['qualifiers']) and bool(r['definition']) and bool(r['counterexample']),r['id']+' 关系条件缺失')
for q in d['questions']:
 check(set(q['fields'])<=ids['fields'] and set(q['relations'])<=ids['relations'],q['id']+' 分析引用')
 check(bool(q['method']) and bool(q['output']) and q['status']=='候选分析任务，未执行',q['id']+' 分析要求/状态')
for path,h in d['sourceHashes'].items():check(hashlib.sha256((V/path).read_bytes()).hexdigest()==h,'源文件指纹改变 '+path)
h=hashlib.sha256((B/'候选模型.json').read_bytes()).hexdigest();check(payload['sourceHash']==h,'载荷哈希不一致')
ns=d['namespace'];keys={n['uid'] for n in payload['nodes']};check(len(keys)==len(payload['nodes']),'重复图节点')
check(all(e['from'] in keys and e['to'] in keys for e in payload['edges']),'图边悬空')
check(all(n['uid'].startswith(ns) and n['properties']['datasetKind']=='candidate_model' and n['label'].startswith('Model') for n in payload['nodes']),'候选层越界')
check(len({e['properties']['linkId'] for e in payload['edges']})==len(payload['edges']),'图边重复')
for p in B.glob('*.md'):
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  check((p.parent/target.split('#')[0]).exists(),'链接失效 '+p.name+' '+target)
for name,coll in [('01-实体定义表','entities'),('02-属性字典','fields'),('03-关系字典','relations'),('04-分析问题与支撑','questions'),('05-原100条去向与依据','itemMappings'),('06-现有模型调整记录','modelChanges')]:
 with (B/(name+'.csv')).open(encoding='utf-8-sig') as f:rows=list(csv.reader(f))
 check(len(rows)-1==len(d[coll]),name+' 表格行数')
result={'date':'2026-10-23','ok':not errs,'errors':errs,'modelSha256':h,'counts':{k:len(d[k]) for k in ['entities','elementProfiles','fields','relations','questions','itemMappings','modelChanges']},'graphNodes':len(payload['nodes']),'graphEdges':len(payload['edges']),'sourceOriginalsUnchanged':True,'limits':['只核候选定义结构、引用及生成内容；语义另由独立agent审核','不替代真实案例试采、PDF全文核读、算法复算或正式实例迁移']}
if any('源文件' in e or '原行' in e for e in errs):result['sourceOriginalsUnchanged']=False
(B/'本地核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if errs:raise SystemExit(1)
