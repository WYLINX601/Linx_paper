"""One authorized, recoverable consolidation. No blind retries or DDL.
The JSON source and database are separate commits; stage receipts are durable.
"""
import argparse,asyncio,copy,datetime,hashlib,json
from pathlib import Path
from compile_model import compile_model,LABELS,RELS,dumps,require
from mcp_client import connected,snapshot,canonical,save,digest
from analyze import analyze
from queries import queries,query_params
OWN=['V01']
# This revision may replace V01 only. Historical trials are out of scope.
REPLACE='''WITH $nodes AS ns,$relationships AS rs
WHERE size(ns)>0 AND size(rs)>0 AND ns=$frozenNodes AND rs=$frozenRelationships
AND all(n IN ns WHERE all(t IN $frozenTypes[n.properties.uid] WHERE valueType(n.properties[t.key])=t.type))
AND all(r IN rs WHERE all(t IN $frozenTypes[r.properties.uid] WHERE valueType(r.properties[t.key])=t.type))
AND size(reduce(xs=[],n IN ns|CASE WHEN n.properties.uid IN xs THEN xs ELSE xs+[n.properties.uid] END))=size(ns)
AND size(reduce(xs=[],r IN rs|CASE WHEN r.properties.uid IN xs THEN xs ELSE xs+[r.properties.uid] END))=size(rs)
AND all(n IN ns WHERE coalesce(n.properties.uid STARTS WITH 'V01:' AND n.properties.caseId='V01' AND n.properties.datasetId='V01' AND n.properties.sourceModelSha256=$sourceModelSha256 AND 'KGItem' IN n.labels AND 'V01' IN n.labels AND all(l IN n.labels WHERE l IN __LABELS__),false))
AND all(r IN rs WHERE coalesce(r.properties.uid STARTS WITH 'V01:' AND r.properties.caseId='V01' AND r.properties.datasetId='V01' AND r.properties.sourceModelSha256=$sourceModelSha256 AND r.type IN __RELS__ AND size([n IN ns WHERE n.properties.uid=r.source])=1 AND size([n IN ns WHERE n.properties.uid=r.target])=1,false))
OPTIONAL MATCH (n) WHERE n.caseId='V01' OR n.datasetId='V01' OR n.uid STARTS WITH 'V01:'
WITH ns,rs,collect(n) AS existing
WHERE size(existing)=size($oldNodes) AND size(existing)>0 AND all(n IN existing WHERE single(o IN $oldNodes WHERE n.uid=o.key AND properties(n)=o.properties AND size(labels(n))=size(o.labels) AND all(l IN labels(n) WHERE l IN o.labels) AND all(t IN o.types WHERE valueType(n[t.key])=t.type)))
OPTIONAL MATCH (a)-[r]->(b)
WHERE a IN existing OR b IN existing OR r.caseId='V01' OR r.datasetId='V01' OR r.uid STARTS WITH 'V01:'
WITH ns,rs,existing,collect({a:a,r:r,b:b}) AS es
WHERE size(es)=size($oldRelationships) AND all(e IN es WHERE single(o IN $oldRelationships WHERE e.r.uid=o.key AND e.a.uid=o.source AND e.b.uid=o.target AND type(e.r)=o.type AND properties(e.r)=o.properties AND all(t IN o.types WHERE valueType(e.r[t.key])=t.type)))
CALL { WITH es UNWIND es AS e WITH e.r AS r DELETE r RETURN count(*) AS relationshipsDeleted }
CALL { WITH existing UNWIND existing AS n DELETE n RETURN count(*) AS nodesDeleted }
CALL { WITH ns UNWIND ns AS row CREATE (n:$(row.labels)) SET n=row.properties RETURN count(*) AS nodesCreated }
CALL { WITH rs UNWIND rs AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:$(row.type)]->(b) SET r=row.properties RETURN count(*) AS relationshipsCreated }
RETURN nodesDeleted,relationshipsDeleted,nodesCreated,relationshipsCreated
'''.replace('__LABELS__',dumps(sorted(LABELS))).replace('__RELS__',dumps(sorted(RELS)))

def owned(r):
 p=r['properties'];return p.get('caseId') in OWN or p.get('datasetId') in OWN or any(r['key'].startswith(x+':') for x in OWN)
def split(g):return tuple(canonical({k:[r for r in g[k] if owned(r)==v] for k in ['nodes','relationships']}) for v in [True,False])
def native_type(v):
 if type(v)==bool:return 'BOOLEAN NOT NULL'
 if type(v)==str:return 'STRING NOT NULL'
 if type(v)==int:return 'INTEGER NOT NULL'
 if type(v)==float:return 'FLOAT NOT NULL'
 if type(v)==list:return 'LIST<'+native_type(v[0])+'> NOT NULL' if v else None
 raise ValueError(type(v))
def binding(p):return {'frozenNodes':copy.deepcopy(p['nodes']),'frozenRelationships':copy.deepcopy(p['relationships']),'frozenTypes':{r['properties']['uid']:[{'key':k,'type':native_type(v)} for k,v in r['properties'].items() if native_type(v)] for r in p['nodes']+p['relationships']}}
def verify_exact(g,p):
 for k in ['nodes','relationships']:
  a={r['key']:r for r in g[k]};e={r['properties']['uid']:r for r in p[k]};require(len(a)==len(g[k]) and set(a)==set(e),'Identity mismatch '+k)
  for uid,row in e.items():
   require(a[uid]['properties']==row['properties'],'Properties differ '+uid)
   if k=='nodes':require(sorted(a[uid]['labels'])==sorted(row['labels']),'Labels differ '+uid)
   else:require(all(a[uid][f]==row[f] for f in ['source','target','type']),'Relationship differs '+uid)
   types={x['key']:x['type'] for x in a[uid]['types']}
   for f,v in row['properties'].items():
    t=native_type(v)
    if t:require(types.get(f)==t,'Native type differs '+uid+'.'+f+': '+str(types.get(f))+' vs '+t)
 return True
def code_hash():return digest({n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in ['compile_model.py','analyze.py','queries.py','run_graph.py','mcp_client.py','d04.py','d05.py','d06.py','projection.py']})
def preserve_original_geometry(m,baseline):
 original={n['key']:n for n in baseline['nodes'] if n['key'].startswith('V01:')}
 require(set(original)<=set('V01:'+n['id'] for n in m['nodes'])|{'V01:SOURCE'},'Lost V01 identity')
 for n in m['nodes']:
  o=original.get('V01:'+n['id'])
  if o and 'geometryJson' in o['properties']:require(json.loads(o['properties']['geometryJson'])==n['geometry'],'Original geometry changed '+n['id'])
 return True
async def main(args):
 w=Path(args.workspace);out=w/'db';model_path=Path(args.model);m,p=compile_model(model_path);model_sha=p['sourceModelSha256'];require(model_sha==args.model_sha,'Source hash differs');baseline=json.loads((out/'before/graph.json').read_text());old,untouched=split(baseline);preserve_original_geometry(m,old)
 stage=out/'execution-stage.json';binding_sha={'modelSHA256':model_sha,'payloadSHA256':digest(p),'compilerSHA256':code_hash(),'beforeFingerprint':digest(baseline)}
 if stage.exists():
  st=json.loads(stage.read_text());require(args.mode=='verify','Stage exists; read back instead of resending')
  require(all(st[k]==v for k,v in binding_sha.items() if k!='compilerSHA256'),'Execution source/payload/baseline conflict')
  if st['compilerSHA256']!=binding_sha['compilerSHA256']:
   require(args.verification_upgrade,'Verifier code changed; explicit audited upgrade receipt required')
   upgrade=json.loads(Path(args.verification_upgrade).read_text())
   require(upgrade['scope']=='read-only-verifier-upgrade' and upgrade['oldCompilerSHA256']==st['compilerSHA256'] and upgrade['newCompilerSHA256']==binding_sha['compilerSHA256'],'Verifier upgrade mismatch')
   require(upgrade['modelSHA256']==model_sha and upgrade['payloadSHA256']==binding_sha['payloadSHA256'] and upgrade['beforeFingerprint']==binding_sha['beforeFingerprint'],'Verifier upgrade source conflict')
   require(set(upgrade['changedFiles'])=={'analyze.py','run_graph.py'},'Unexpected verifier upgrade scope')
 save(w/'generated/payload.json',p);save(w/'generated/queries.json',queries());save(w/'generated/query-params.json',query_params());(w/'generated/replace.cypher').write_text(REPLACE)
 async with connected(out) as call:
  current,_=await snapshot(call,out/'current');schema=json.loads((out/'current/schema.json').read_text());oldschema=json.loads((out/'before/schema.json').read_text());require(schema==oldschema,'Schema changed')
  require(any(c['type']=='UNIQUENESS' and c['labelsOrTypes']==['KGItem'] and c['properties']==['uid'] for c in schema['constraints']),'UID constraint absent');require(all(i['state']=='ONLINE' for i in schema['indexes']),'Indexes unavailable')
  params={**p,**binding(p),'oldNodes':old['nodes'],'oldRelationships':old['relationships']}
  if args.mode=='preflight':
   require(current==baseline,'Database changed since snapshot')
   for key,q in {'replace':REPLACE,**queries()}.items():await call('EXPLAIN '+q,params if key=='replace' else query_params(),write=True,receipt=out/'explain'/(key+'.json'))
   guard=REPLACE.split('CALL { WITH es UNWIND')[0]+'RETURN size(existing) AS oldNodes,size(es) AS oldRelationships,size(ns) AS newNodes,size(rs) AS newRelationships'
   positive=await call(guard,params,receipt=out/'positive-guard.json');require(positive==[{'oldNodes':len(old['nodes']),'oldRelationships':len(old['relationships']),'newNodes':len(p['nodes']),'newRelationships':len(p['relationships'])}],'Correct payload rejected by guard')
   tests=[]
   for name in ['duplicate-node','missing-endpoint','wrong-label','wrong-type','wrong-namespace','wrong-source','stale-old-node','stale-old-edge','null-uid','changed-property','wrong-native-type','equal-value-wrong-native-type','missing-actor','changed-source-document','wrong-boundary-slice','duplicate-old-identity']:
    q=copy.deepcopy(params)
    if name=='duplicate-node':q['nodes'].append(copy.deepcopy(q['nodes'][0]))
    elif name=='missing-endpoint':q['relationships'][0]['target']='V01:ABSENT'
    elif name=='wrong-label':q['nodes'][0]['labels'].append('Unauthorized')
    elif name=='wrong-type':q['relationships'][0]['type']='UNAUTHORIZED'
    elif name=='wrong-namespace':q['nodes'][0]['properties']['datasetId']='D03V01'
    elif name=='wrong-source':q['nodes'][0]['properties']['sourceModelSha256']='stale'
    elif name=='stale-old-node':q['oldNodes'][0]['properties']['name']='stale'
    elif name=='stale-old-edge':q['oldRelationships'][0]['properties']['uid']='stale'
    elif name=='null-uid':q['nodes'][0]['properties']['uid']=None
    elif name=='changed-property':q['nodes'][0]['properties']['name']='different-with-same-sha'
    elif name=='wrong-native-type':next(n for n in q['nodes'] if n['id']=='B02')['properties']['eaveZM']='7.0'
    elif name=='equal-value-wrong-native-type':next(n for n in q['nodes'] if n['id']=='B02')['properties']['eaveZM']=7
    elif name=='missing-actor':del next(r for r in q['relationships'] if r['type']=='DIRECT_ACCESS_TO')['properties']['actor']
    elif name=='changed-source-document':next(n for n in q['nodes'] if n['id']=='SOURCE')['properties']['rawModelJson']='{}'
    elif name=='wrong-boundary-slice':next(r for r in q['relationships'] if r['type']=='BOUNDARY_PARTICIPANT' and 'analysisSliceZM' in r['properties'])['properties']['analysisSliceZM']=2.0
    elif name=='duplicate-old-identity':q['oldNodes'].append(copy.deepcopy(q['oldNodes'][0]))
    ret=await call(REPLACE,q,write=True,receipt=out/'rejections'/(name+'.json'));require(ret==[],'Bad payload unexpectedly executed '+name);tests.append({'id':name,'rejected':True})
   after,_=await snapshot(call,out/'after-rejections');require(after==baseline,'Rejection tests changed database');save(out/'rejection-tests.json',tests);save(out/'preflight.json',{'status':'passed',**binding_sha,'explainCount':len(queries())+1,'explainScope':'compiled without error; MCP may not expose operators','rejectedPayloads':len(tests)});print(json.dumps({'preflight':'passed','nodes':len(p['nodes']),'relationships':len(p['relationships']),'rejects':len(tests)}));return
  if args.mode=='write':
   pre=json.loads((out/'preflight.json').read_text());require(current==baseline and all(pre[k]==v for k,v in binding_sha.items()),'Source/code/database changed since preflight')
   require(args.authorization=='user-authorized-continue-V01-D04-D05-D06','Explicit continuation authorization token absent')
   save(stage,{'stage':'write-started-no-retry',**binding_sha,'at':datetime.datetime.now().astimezone().isoformat()})
   require(compile_model(model_path)[1]==p,'Source changed before commit')
   ret=await call(REPLACE,params,write=True,receipt=out/'write-return.json');require(ret==[{'nodesDeleted':len(old['nodes']),'relationshipsDeleted':len(old['relationships']),'nodesCreated':len(p['nodes']),'relationshipsCreated':len(p['relationships'])}],'Unexpected write response; inspect without retry')
  after,summary=await snapshot(call,out/'after');active,remaining=split(after);require(remaining==untouched,'Unrelated graph changed');require(json.loads((out/'after/schema.json').read_text())==oldschema,'Schema changed');verify_exact(active,p);save(out/'V01-readback.json',active)
  answers={k:await call(q,query_params(),receipt=out/'queries'/(k+'.json')) for k,q in queries().items()};save(out/'query-results.json',answers)
  require(len(answers['Q01_identity'])==len(p['nodes']) and len(answers['Q02_dimensions'])==8,'Query coverage')
  require(len(answers['Q03_comparison'])==1 and answers['Q03_comparison'][0]['valid'] and answers['Q03_comparison'][0]['cacheAgreement'],'Comparison query')
  require(answers['Q12_no_duplicates']==[{'legacyActiveNodes':0,'courtyardIdentity':1,'hallIdentity':1}],'Duplicate prototype')
  require(len(answers['Q04_boundary'])==8 and len(answers['Q05_interfaces'])==5,'Boundary/interface coverage')
  for key in ['Q06_outward_path','Q07_return_path']:require(len(answers[key])==1 and answers[key][0]['crossings']==2,'Local passage query')
  require(answers['Q13_legacy_topology']==[{'type':'AXIS_JOINS','count':12},{'type':'ENVELOPE_INTERSECTS','count':4},{'type':'SHARES_BOUNDARY','count':1}],'Legacy topology changed')
  require([len(answers[k]) for k in ['Q14_facade_records','Q15_facade_openings','Q16_collection','Q17_street_sides','Q18_ground_reference','Q19_explicit_local_pair']]==[2,4,3,2,1,1],'Extension query coverage')
  require({r['building']:r['dwellingOwners'] for r in answers['Q16_collection']}=={'V01:B01':['V01:U01'],'V01:B02':['V01:U01'],'V01:B03':[]},'Independent dwelling semantics changed')
  require(len(answers['Q20_extension_sources'])==len(m['analysisContract']['extensionSourceFields']) and all(r['expectedVersion']==r['actualVersion']==m['modelVersion'] for r in answers['Q20_extension_sources']),'Extension source queries')
  analysis=analyze(active);require(analysis==analyze(p),'Readback analysis differs');save(out/'analysis-results.json',analysis)
  report={'status':'verified-unified-synthetic-prototype-new-details-await-user-review',**binding_sha,'at':datetime.datetime.now().astimezone().isoformat(),'exactNodes':len(active['nodes']),'exactRelationships':len(active['relationships']),'originalV01NodeIdentitiesPreserved':sum(n['key'].startswith('V01:') for n in old['nodes']),'allOriginalV01GeometriesUnchanged':True,'legacyTrialNodesActive':0,'nativeTypes':'verified','constraintsIndexesUnchanged':True,'preservedOtherGraphFingerprint':digest(remaining),'queryCounts':{k:len(v) for k,v in answers.items()},'analysisItems':list(analysis['D03']),'empiricalValidity':'not-validated','restoreRehearsed':False}
  report.update(extensionAnalysisItems={k:list(analysis[k]) for k in ['D04','D05','D06']},newDistinctObjectIds=['B03','CG01','ST01','TP01'],scope='V01 continuation only; no D01V01/D03V01 remigration')
  if args.mode=='verify' and stage.exists() and st['compilerSHA256']!=binding_sha['compilerSHA256']:report.update(executionCompilerSHA256=st['compilerSHA256'],verificationCodeUpgrade=upgrade)
  save(out/'verification.json',report)
  if stage.exists():st=json.loads(stage.read_text());st.update(stage='verified',verificationFingerprint=digest(report));save(stage,st)
  print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);p.add_argument('--model',required=True);p.add_argument('--model-sha',required=True);p.add_argument('--mode',choices=['preflight','write','verify'],required=True);p.add_argument('--authorization');p.add_argument('--verification-upgrade');asyncio.run(main(p.parse_args()))
