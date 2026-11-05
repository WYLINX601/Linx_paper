#!/usr/bin/env python3
"""Bounded, archived, atomic graph replacement through the configured official MCP.
No credentials, remote configuration changes, server restart, or broad APOC access.
"""
import argparse, collections, datetime, hashlib, importlib.util, json, math, sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CASE=HERE.parent
VAULT=CASE.parents[1]
ARCHIVE=VAULT/'archive/2026-10-24-Neo4j旧图谱归档'
spec=importlib.util.spec_from_file_location('local_mcp',HERE/'MCP客户端.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def js(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else js(x).encode()).hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n');t.replace(p)
def read(p):return json.loads(p.read_text())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def call(c,q,params=None,admin=False):
 r=c.request('tools/call',{'name':'write-cypher' if admin else 'read-cypher','arguments':{'query':q,'params':params or {}}})
 texts=[b['text'] for b in r.get('content',[]) if b.get('type')=='text']
 if not texts:raise RuntimeError('MCP returned no text')
 return json.loads('\n'.join(texts))
def connect():
 c=mod.MCP();i=c.request('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'paper-v01-migration','version':'1.0'}});c.send({'jsonrpc':'2.0','method':'notifications/initialized'})
 ts=c.request('tools/list',{})['tools'];assert 'write-cypher' in [t['name'] for t in ts], 'Existing MCP server is read-only; no permission change made'
 return c,i
EXPORT='''CALL { MATCH (n) RETURN collect({elementId:elementId(n),labels:labels(n),properties:properties(n)}) AS nodes }
CALL { MATCH (a)-[r]->(b) RETURN collect({elementId:elementId(r),source:a.uid,target:b.uid,type:type(r),properties:properties(r)}) AS relationships }
RETURN nodes,relationships'''
def graph(c):
 r=call(c,EXPORT);assert isinstance(r,list) and len(r)==1
 g=r[0];validate(g);return g
def propval(v):
 if isinstance(v,(str,bool,int)):return True
 if isinstance(v,float):return math.isfinite(v)
 return isinstance(v,list) and (not v or len({type(x) for x in v})==1) and all(isinstance(x,(str,bool,int,float)) and propval(x) for x in v)
def validate(g):
 ids=[n['properties'].get('uid') for n in g['nodes']];assert all(isinstance(i,str) and i for i in ids) and len(ids)==len(set(ids)), 'Node uid missing/duplicate'
 assert all(n['labels'] and all(isinstance(l,str) and l for l in n['labels']) for n in g['nodes'])
 for rec in g['nodes']+g['relationships']:assert all(propval(v) for v in rec['properties'].values()), 'Unsupported property value; do not migrate'
 assert all(r['source'] in ids and r['target'] in ids for r in g['relationships'])
def canonical(g):
 return {'nodes':sorted([{'labels':sorted(n['labels']),'properties':n['properties']} for n in g['nodes']],key=lambda n:n['properties']['uid']), 'relationships':sorted([{'source':r['source'],'target':r['target'],'type':r['type'],'properties':r['properties']} for r in g['relationships']],key=js)}
def fingerprint(g):return sha(canonical(g))
def flatprops(p):return {k:v if propval(v) else js(v) for k,v in p.items() if v is not None}
def desired():
 raw=(CASE/'案例模型.json').read_bytes();d=json.loads(raw);h=sha(raw);out={'nodes':[],'relationships':[]}
 for n in d['nodes']:
  p=flatprops(n['properties']);p.update({'uid':'V01:'+n['id'],'id':n['id'],'name':n['name'],'class':n['class'],'datasetId':'V01','graphStatus':'active','dataMode':'synthetic_demo','sourceModelSha256':h,'evidenceIds':n.get('evidence',[]),'sourceRecordJson':js(n)})
  if n.get('geometry'):
   g=n['geometry'];p['geometryJson']=js(g)
   if g['kind']=='rect':p.update(centerX=(g['min'][0]+g['max'][0])/2,centerY=(g['min'][1]+g['max'][1])/2,centerZ=g.get('z',0))
   elif g['kind']=='column':p.update(centerX=g['center'][0],centerY=g['center'][1],centerZ=g['center'][2])
  for k in ['labelEvidence','propertyOrigins']:
   if k in n:p[k+'Json']=js(n[k])
  labels=sorted(set(n['labels']+['KGItem','V01','Demo']+([] if n['class']=='Evidence' else ['Entity'])))
  out['nodes'].append({'labels':labels,'properties':p})
 for r in d['relationships']:
  p=flatprops(r['properties']);p.update({'uid':'V01:'+r['id'],'id':r['id'],'datasetId':'V01','graphStatus':'active','dataMode':'synthetic_demo','recordStatus':r['status'],'evidenceIds':r.get('evidence',[]),'sourceRecordJson':js(r)})
  out['relationships'].append({'source':'V01:'+r['source'],'target':'V01:'+r['target'],'type':r['type'],'properties':p})
 out['nodes'].append({'labels':['DatasetSnapshot','Demo','KGItem'],'properties':{'uid':'V01:SOURCE','id':'V01:SOURCE','name':'V01迭代基线与来源快照','datasetId':'V01','graphStatus':'active','dataMode':'synthetic_demo','sourceModelSha256':h,'sourcePath':str(CASE/'案例模型.json'),'rawModelJson':raw.decode(),'inferenceResultsJson':(CASE/'验证/推演结果.json').read_text(),'method':'canonical local JSON projected into LPG; unknown predictions do not update case facts'}})
 validate(out);return out

def quoted(s):return '`'+s.replace('`','``')+'`'
def import_blocks(g):
 groups=collections.defaultdict(list);rels=collections.defaultdict(list);params={};blocks=[]
 for n in g['nodes']:groups[tuple(sorted(n['labels']))].append({'properties':n['properties']})
 for i,(labels,rows) in enumerate(sorted(groups.items())):
  key='nodes'+str(i);params[key]=rows
  blocks.append(f'CALL {{ UNWIND ${key} AS row CREATE (n:'+':'.join(map(quoted,labels))+f') SET n = row.properties RETURN count(*) AS madeNodes{i} }}')
 for r in g['relationships']:rels[r['type']].append(r)
 for i,(typ,rows) in enumerate(sorted(rels.items())):
  key='rels'+str(i);params[key]=rows
  blocks.append(f'CALL {{ UNWIND ${key} AS row MATCH (a:KGItem {{uid:row.source}}),(b:KGItem {{uid:row.target}}) CREATE (a)-[r:{quoted(typ)}]->(b) SET r = row.properties RETURN count(*) AS madeRels{i} }}')
 return blocks,params

def migration_query(old,new):
 # Lock the exact archived records before comparison. Self-assignment reads the same
 # property it writes, acquiring a write lock without introducing/removing any key.
 locks=['CALL { UNWIND $oldNodes AS row MATCH (n) WHERE elementId(n)=row.elementId WITH n ORDER BY elementId(n) SET n.uid=n.uid RETURN count(n) AS lockedNodes }']
 lockgroups=collections.defaultdict(list)
 for r in old['relationships']:
  assert r['properties'], 'Cannot select a safe existing relationship lock property'
  lockgroups[sorted(r['properties'])[0]].append(r['elementId'])
 lockparams={}
 for i,(key,ids) in enumerate(sorted(lockgroups.items())):
  lockparams['lockRels'+str(i)]=ids
  locks.append(f'CALL {{ UNWIND $lockRels{i} AS rid MATCH ()-[r]->() WHERE elementId(r)=rid WITH r ORDER BY elementId(r) SET r.{quoted(key)}=r.{quoted(key)} RETURN count(r) AS lockedRels{i} }}')
 # Compare every record after obtaining locks; only archived relationships may be deleted.
 guard='''CALL { MATCH (n) RETURN count(n) AS liveNodes }
CALL { MATCH ()-[r]->() RETURN count(r) AS liveRels }
CALL { UNWIND $oldNodes AS row OPTIONAL MATCH (n) WHERE elementId(n)=row.elementId
RETURN collect(n) AS oldNodeObjects, sum(CASE WHEN n IS NOT NULL AND properties(n)=row.properties AND size(labels(n))=size(row.labels) AND all(l IN row.labels WHERE l IN labels(n)) THEN 1 ELSE 0 END) AS equalNodes }
CALL { UNWIND $oldRels AS row OPTIONAL MATCH (a)-[r]->(b) WHERE elementId(r)=row.elementId
RETURN sum(CASE WHEN r IS NOT NULL AND a.uid=row.source AND b.uid=row.target AND type(r)=row.type AND properties(r)=row.properties THEN 1 ELSE 0 END) AS equalRels }
WITH * WHERE liveNodes=size($oldNodes) AND liveRels=size($oldRels) AND equalNodes=liveNodes AND equalRels=liveRels
CALL { UNWIND $oldRels AS row MATCH ()-[r]->() WHERE elementId(r)=row.elementId DELETE r RETURN count(*) AS archivedRelationships }
CALL { WITH oldNodeObjects UNWIND oldNodeObjects AS n DELETE n RETURN count(*) AS archivedNodes }
'''
 blocks,params=import_blocks(new);params.update(oldNodes=old['nodes'],oldRels=old['relationships'],**lockparams)
 guard=guard.replace('WITH * WHERE liveNodes=', 'WITH * WHERE lockedNodes=liveNodes AND '+ ('+'.join('lockedRels'+str(i) for i in range(len(lockgroups))) or '0') +'=liveRels AND liveNodes=')
 return '\n'.join(locks)+'\n'+guard+'\n'.join(blocks)+'\nRETURN archivedNodes, '+str(len(new['nodes']))+' AS expectedNodes, '+str(len(new['relationships']))+' AS expectedRelationships',params

def prepare(c,info):
 ap=ARCHIVE/'数据库完整快照.json'
 assert not ap.exists(), 'Archive exists; do not overwrite. Inspect previous report.'
 old=graph(c);assert all('KGItem' in n['labels'] for n in old['nodes']), 'Unrelated graph data found; stop'
 types=call(c,"MATCH (n) UNWIND keys(n) AS k RETURN DISTINCT valueType(n[k]) AS propertyType UNION MATCH ()-[r]->() UNWIND keys(r) AS k RETURN DISTINCT valueType(r[k]) AS propertyType")
 for t in types:
  assert t['propertyType'].startswith(('STRING','BOOLEAN','INTEGER','FLOAT','LIST<STRING','LIST<INTEGER','LIST<FLOAT','LIST<BOOLEAN')), 'Non-JSON-native property type needs explicit restore mapping'
 constraints=call(c,'SHOW CONSTRAINTS',admin=True);indexes=call(c,'SHOW INDEXES',admin=True)
 version=call(c,'CALL dbms.components() YIELD name, versions, edition RETURN name,versions,edition',admin=True)
 snapshot={'capturedAt':now(),'server':info['serverInfo'],'databaseComponents':version,'nodes':old['nodes'],'relationships':old['relationships'],'constraints':constraints,'indexes':indexes,'propertyTypes':types,'graphSha256':fingerprint(old),'scope':'Full current graph; original documents and PDFs are not database contents.'}
 save(ap,snapshot);reread=read(ap);assert fingerprint(reread)==fingerprint(old)
 new=desired();q,params=migration_query(old,new)
 (HERE/'本次切换.cypher').write_text(q+'\n');save(HERE/'本次切换参数.json',params)
 # A complete restore plan is generated for an empty graph, preserving labels and all values.
 blocks,rparams=import_blocks(old)
 rq='CALL { MATCH (n) RETURN count(n) AS existing } WITH existing WHERE existing=0\n'+'\n'.join(blocks)+'\nRETURN '+str(len(old['nodes']))+' AS restoredNodes'
 (ARCHIVE/'空库恢复.cypher').write_text(rq+'\n');save(ARCHIVE/'恢复参数.json',rparams)
 plan=call(c,'EXPLAIN '+q,params,True);restoreplan=call(c,'EXPLAIN '+rq,rparams,True)
 report={'status':'prepared','preparedAt':now(),'sourceModelSha256':sha((CASE/'案例模型.json').read_bytes()),'archiveFileSha256':sha(ap.read_bytes()),'oldNodes':len(old['nodes']),'oldRelationships':len(old['relationships']),'oldGraphSha256':fingerprint(old),'newNodes':len(new['nodes']),'newRelationships':len(new['relationships']),'newGraphSha256':fingerprint(new),'archive':str(ap),'queryExplain':plan,'restoreExplain':restoreplan,'schemaPolicy':'Existing constraints and indexes retained; no schema changes','authorization':'User requested archive all previous graph data and make V01 the iteration base.'}
 save(HERE/'切换预检.json',report);print(js({k:report[k] for k in ['status','oldNodes','oldRelationships','newNodes','newRelationships','archive']}))

def verify(c):
 actual=graph(c);expected=desired();assert canonical(actual)==canonical(expected),'Database differs from canonical V01 payload'
 # Record integral-float JSON normalization separately from value equality.
 numeric_changes=[]
 for group in ['nodes','relationships']:
  wanted={r['properties']['uid']:r for r in expected[group]}
  for r in actual[group]:
   p=r['properties'];ep=wanted[p['uid']]['properties']
   for k,v in p.items():
    if js(v)!=js(ep[k]):
     assert type(v) in (int,float) and type(ep[k]) in (int,float) and v==ep[k], 'Unexpected representation change'
     numeric_changes.append({'uid':p['uid'],'property':k,'expected':ep[k],'returned':v,'expectedJsonType':type(ep[k]).__name__,'returnedJsonType':type(v).__name__})
 tests=[]
 for name,q in [
  ('对象类型分布','MATCH (n:V01) RETURN n.class AS class,count(*) AS count ORDER BY class'),
  ('材料分组','MATCH (n:V01:Element) UNWIND [l IN labels(n) WHERE l STARTS WITH "材质_"] AS material RETURN material,[l IN labels(n) WHERE l IN ["Wall","Column","Roof"]][0] AS componentType,count(*) AS count ORDER BY material,componentType'),
  ('通行链','MATCH p=shortestPath((a:V01:Space {id:"S06"})-[:DIRECT_ACCESS_TO*]-(b:V01:Space {id:"S03"})) WHERE all(r IN relationships(p) WHERE r.bidirectional=true) RETURN [n IN nodes(p)|n.name] AS spaces,length(p) AS steps'),
  ('材料依据','MATCH (e:V01:Evidence)-[r:DOCUMENTS]->(w:V01:Wall {id:"W06"}) RETURN e.id AS evidence,r.scope AS scope'),
  ('方位距离','MATCH (a:V01:Space {id:"S02"})-[r:SPATIAL_RELATION]->(b:V01:Space {id:"S03"}) RETURN r.distanceM AS storedDistance,point.distance(point({x:a.centerX,y:a.centerY}),point({x:b.centerX,y:b.centerY})) AS recomputedDistance'),
  ('旧候选层残留','MATCH (n:ModelDefinition) RETURN count(n) AS oldModelNodes')]:
  tests.append({'name':name,'query':q,'result':call(c,q)})
 assert tests[-1]['result']==[{'oldModelNodes':0}]
 assert tests[2]['result'][0]['steps']==4
 report={'status':'verified','verifiedAt':now(),'nodeCount':len(actual['nodes']),'domainAndEvidenceNodes':40,'sourceSnapshotNodes':1,'relationshipCount':len(actual['relationships']),'graphSha256':fingerprint(actual),'expectedProjectionSha256':fingerprint(expected),'numericRepresentationChanges':numeric_changes,'comparison':'All node labels, property values, typed relationship endpoints and property values match the expected LPG projection. Integral-float JSON normalization is recorded separately; serialization hashes need not match.','queries':tests}
 save(HERE/'入库核验.json',report);print(js({'status':'verified','nodes':len(actual['nodes']),'relationships':len(actual['relationships']),'functionalQueries':len(tests)}));return report

def apply(c):
 pre=read(HERE/'切换预检.json');ap=ARCHIVE/'数据库完整快照.json';assert sha(ap.read_bytes())==pre['archiveFileSha256'];assert sha((CASE/'案例模型.json').read_bytes())==pre['sourceModelSha256']
 current=graph(c);new=desired()
 if canonical(current)==canonical(new):print(js({'status':'already_applied_no_write'}));return verify(c)
 assert fingerprint(current)==pre['oldGraphSha256'],'Live graph changed after archive; stop'
 q=(HERE/'本次切换.cypher').read_text();params=read(HERE/'本次切换参数.json')
 expected_q,expected_p=migration_query(read(ap),new);assert q.strip()==expected_q.strip() and params==expected_p,'Prepared query/parameters changed'
 receipt=call(c,q,params,True);save(HERE/'切换回执.json',{'appliedAt':now(),'receipt':receipt,'archiveFileSha256':pre['archiveFileSha256']})
 return verify(c)

def main():
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['prepare','apply','verify']);args=a.parse_args();c,info=connect()
 try:
  if args.mode=='prepare':prepare(c,info)
  elif args.mode=='apply':apply(c)
  else:verify(c)
 finally:c.close()
if __name__=='__main__':main()
