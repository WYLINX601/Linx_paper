"""在既有SSH通道执行一次候选定义导入。凭据仅在Linux私有文件内读取。"""
import argparse,json,subprocess,shlex
from pathlib import Path
BASE=Path(__file__).resolve().parent
REMOTE=r'''
import sys,json,urllib.request,base64,hashlib,collections
from pathlib import Path
req=json.load(sys.stdin);p=req['payload'];mode=req['mode'];ns=p['namespace'];h=p['sourceHash']
assert ns=='kgmodel:single:v01:'
creds=json.loads((Path.home()/'.config/neo4j-paper/access.json').read_text())
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def tx(statements):
 body={'statements':[{'statement':q,'parameters':a} for q,a in statements]}
 auth=base64.b64encode((creds['username']+':'+creds['password']).encode()).decode()
 r=urllib.request.Request('http://100.68.38.32:7474/db/neo4j/tx/commit',data=json.dumps(body).encode(),headers={'Authorization':'Basic '+auth,'Content-Type':'application/json'})
 with opener.open(r,timeout=120) as f:d=json.load(f)
 if d.get('errors'):raise RuntimeError(json.dumps(d['errors'],ensure_ascii=False))
 return d['results']
def query(q,a=None):
 r=tx([(q,a or {})])[0]
 return [dict(zip(r['columns'],x['row'])) for x in r['data']]
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sortedrows(v):return sorted(v,key=canon)
def digest(v):return hashlib.sha256(canon(v).encode()).hexdigest()
def snapshot(exclude):
 where='NOT n.uid STARTS WITH $ns' if exclude else 'n.uid STARTS WITH $ns'
 # Missing uid records are also protected.
 if exclude:where='n.uid IS NULL OR NOT n.uid STARTS WITH $ns'
 nodes=query('MATCH (n) WHERE '+where+' RETURN labels(n) AS labels, properties(n) AS properties',{'ns':ns})
 rw='NOT a.uid STARTS WITH $ns AND NOT b.uid STARTS WITH $ns' if exclude else 'a.uid STARTS WITH $ns OR b.uid STARTS WITH $ns'
 if exclude:rw='(a.uid IS NULL OR NOT a.uid STARTS WITH $ns) AND (b.uid IS NULL OR NOT b.uid STARTS WITH $ns)'
 rels=query('MATCH (a)-[r]->(b) WHERE '+rw+' RETURN a.uid AS source,b.uid AS target,type(r) AS type,properties(r) AS properties',{'ns':ns})
 for x in nodes:x['labels']=sorted(x['labels'])
 return {'nodes':sortedrows(nodes),'edges':sortedrows(rels)}
assert all(n['uid'].startswith(ns) and n['properties']['uid']==n['uid'] and n['properties']['uid'].startswith(ns) and n['properties']['datasetKind']=='candidate_model' and n['properties']['sourceHash']==h for n in p['nodes']),'actual node properties must use the candidate namespace and source version'
keys={n['uid'] for n in p['nodes']};assert len(keys)==len(p['nodes'])
assert all(e['from'] in keys and e['to'] in keys for e in p['edges'])
allowed_labels={'ModelVersion','ModelEntityType','ModelElementProfile','ModelProperty','ModelRelation','ModelRecordProfile','ModelAnalysisQuestion','ModelResearchItem','ModelEvidenceReference','ModelDecision','ModelOpenIssue'}
allowed_edges={'DEFINES','DESIGN_FROM_ITEM','COVERS_ITEM','USES_ENTITY_TYPE','USES_PROPERTY','USES_RELATION','USES_PROFILE','USES_RECORD_PROFILE','REFERENCES_EVIDENCE','HAS_PROPERTY','ALLOWS_RELATION','TO_TYPE','PROFILE_OF','REQUIRES_PROPERTY','REQUIRES_RELATION','INVOLVES_TYPE','ANALYSES_ITEM','HAS_DECISION','PROPOSES_DEFINITION','HAS_OPEN_ISSUE'}
assert all(n['label'] in allowed_labels for n in p['nodes'])
assert all(e['type'] in allowed_edges for e in p['edges'])
constraints=query('SHOW CONSTRAINTS YIELD labelsOrTypes,properties,type RETURN labelsOrTypes,properties,type')
assert any(x['labelsOrTypes']==['KGItem'] and x['properties']==['uid'] and 'UNIQUENESS' in x['type'] for x in constraints),'existing unique key missing; no schema changes attempted'
indexes=query("SHOW INDEXES YIELD state,populationPercent RETURN state,populationPercent")
assert all(x['state']=='ONLINE' and x['populationPercent']==100.0 for x in indexes)
current=query('MATCH (n) WHERE n.uid STARTS WITH $ns RETURN count(n) AS count,collect(DISTINCT n.sourceHash) AS hashes',{'ns':ns})[0]
assert current['count']==0 or current['hashes']==[h],'candidate namespace contains different version; stop without overwriting'
before=snapshot(True);basehash=digest(before)
ng=collections.defaultdict(list);eg=collections.defaultdict(list)
for n in p['nodes']:ng[n['label']].append(n['properties'])
for e in p['edges']:eg[e['type']].append({'source':e['from'],'target':e['to'],'props':e['properties']})
statements=[]
for label,rows in ng.items():statements.append(('UNWIND $rows AS row CREATE (n:KGItem:ModelDefinition:Candidate:'+label+') SET n = row RETURN count(n) AS created',{'rows':rows}))
for typ,rows in eg.items():statements.append(('UNWIND $rows AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:'+typ+']->(b) SET r = row.props RETURN count(r) AS created',{'rows':rows}))
report={'mode':mode,'namespace':ns,'sourceHash':h,'expectedNodes':len(p['nodes']),'expectedEdges':len(p['edges']),'protectedBeforeHash':basehash,'protectedNodeCount':len(before['nodes']),'protectedEdgeCount':len(before['edges']),'constraints':constraints,'indexes':indexes}
if mode=='plan':
 plans=[]
 for q,a in statements:
  sample={'rows':a['rows'][:1]};r=tx([('EXPLAIN '+q,sample)])[0];plans.append({'query':q,'rows':len(a['rows']),'planned':bool(r.get('plan'))})
 report.update(status='planned',plans=plans,protectedSnapshot=before)
else:
 assert req.get('expectedProtectedHash')==basehash,'protected data changed since plan; no write performed'
 if mode=='apply' and current['count']==0:
  result=tx(statements)
  report['statementCounts']=[x['data'][0]['row'][0] for x in result]
  report['operation']='one_atomic_transaction'
 else:report['operation']='verify_existing_only'
 actual=snapshot(False)
 expected={'nodes':sortedrows([{'labels':sorted(['KGItem','ModelDefinition','Candidate',n['label']]),'properties':n['properties']} for n in p['nodes']]),'edges':sortedrows([{'source':e['from'],'target':e['to'],'type':e['type'],'properties':e['properties']} for e in p['edges']])}
 after=snapshot(True)
 candidate_matches=canon(actual)==canon(expected)
 protected_unchanged=canon(before)==canon(after)
 report.update(candidateMatchesPayload=candidate_matches,protectedUnchanged=protected_unchanged,actualNodes=len(actual['nodes']),actualEdges=len(actual['edges']),protectedAfterHash=digest(after),comparison='canonical JSON, preserving boolean and numeric types')
 assert candidate_matches,'candidate content mismatch; inspect report before any retry'
 assert protected_unchanged,'protected graph changed; no rollback of other work attempted'
 report['status']='passed'
print(json.dumps(report,ensure_ascii=False))
'''
def main():
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['plan','apply','verify']);args=a.parse_args()
 payload=json.loads((BASE/'Neo4j候选层载荷.json').read_text());request={'payload':payload,'mode':args.mode}
 if args.mode!='plan':request['expectedProtectedHash']=json.loads((BASE/'入库预检.json').read_text())['protectedBeforeHash']
 cmd=['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=10','linx-HP-EliteDesk-880-G6-Tower-PC','python3 -c '+shlex.quote(REMOTE)]
 r=subprocess.run(cmd,input=json.dumps(request,ensure_ascii=False),capture_output=True,text=True,timeout=180)
 if r.returncode:raise RuntimeError(r.stderr[:4000])
 report=json.loads(r.stdout)
 if args.mode=='plan':
  (BASE/'数据库写入前快照.json').write_text(json.dumps(report.pop('protectedSnapshot'),ensure_ascii=False,indent=2)+'\n')
 name={'plan':'入库预检.json','apply':'入库结果.json','verify':'数据库逐记录核验.json'}[args.mode]
 (BASE/name).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['plans','constraints','indexes','statementCounts']},ensure_ascii=False))
if __name__=='__main__':main()
