"""Guarded replacement of D03V01 only, followed by exact readback.
This is not a general synchronizer. Never retry an ambiguous mutation.
"""
import asyncio,copy,datetime,hashlib,json,argparse
from pathlib import Path
from compile_model import *
from mcp_client import connected,snapshot,save,digest,canonical
from analyze import analyze

# Fixed executable allowlists; not supplied by payload.
REPLACE='''WITH $nodes AS ns,$relationships AS rs
WHERE size(ns)>0 AND size(rs)>0
 AND ns=$frozenNodes AND rs=$frozenRelationships
 AND all(n IN ns WHERE all(t IN $frozenTypes[n.properties.uid] WHERE valueType(n.properties[t.key])=t.type))
 AND all(r IN rs WHERE all(t IN $frozenTypes[r.properties.uid] WHERE valueType(r.properties[t.key])=t.type))
 AND size(reduce(xs=[],n IN ns|CASE WHEN n.properties.uid IN xs THEN xs ELSE xs+[n.properties.uid] END))=size(ns)
 AND size(reduce(xs=[],r IN rs|CASE WHEN r.properties.uid IN xs THEN xs ELSE xs+[r.properties.uid] END))=size(rs)
 AND all(n IN ns WHERE coalesce(n.properties.uid STARTS WITH 'D03V01:' AND n.properties.caseId='D03V01' AND n.properties.datasetId='D03V01' AND n.properties.sourceModelSha256=$sourceModelSha256 AND 'KGItem' IN n.labels AND 'D03V01' IN n.labels AND all(l IN n.labels WHERE l IN __LABELS__),false))
 AND all(r IN rs WHERE coalesce(r.properties.uid STARTS WITH 'D03V01:' AND r.properties.caseId='D03V01' AND r.properties.datasetId='D03V01' AND r.properties.sourceModelSha256=$sourceModelSha256 AND r.type IN __RELS__ AND size([n IN ns WHERE n.properties.uid=r.source])=1 AND size([n IN ns WHERE n.properties.uid=r.target])=1,false))
OPTIONAL MATCH (n) WHERE n.caseId='D03V01' OR n.datasetId='D03V01' OR n.uid STARTS WITH 'D03V01:'
WITH ns,rs,collect(n) AS existing
WHERE size(existing)=size($oldNodes) AND size(existing)>0 AND all(n IN existing WHERE single(o IN $oldNodes WHERE n.uid=o.key AND properties(n)=o.properties AND size(labels(n))=size(o.labels) AND all(l IN labels(n) WHERE l IN o.labels) AND all(t IN o.types WHERE valueType(n[t.key])=t.type)))
OPTIONAL MATCH (a)-[r]->(b)
WHERE a IN existing OR b IN existing OR r.caseId='D03V01' OR r.datasetId='D03V01' OR r.uid STARTS WITH 'D03V01:'
WITH ns,rs,existing,collect({a:a,r:r,b:b}) AS es
WHERE size(es)=size($oldRelationships) AND all(e IN es WHERE single(o IN $oldRelationships WHERE e.r.uid=o.key AND e.a.uid=o.source AND e.b.uid=o.target AND type(e.r)=o.type AND properties(e.r)=o.properties AND all(t IN o.types WHERE valueType(e.r[t.key])=t.type)))
CALL { WITH es UNWIND es AS e WITH e.r AS r DELETE r RETURN count(*) AS relationshipsDeleted }
CALL { WITH existing UNWIND existing AS n DELETE n RETURN count(*) AS nodesDeleted }
CALL { WITH ns UNWIND ns AS row CREATE (n:$(row.labels)) SET n=row.properties RETURN count(*) AS nodesCreated }
CALL { WITH rs UNWIND rs AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:$(row.type)]->(b) SET r=row.properties RETURN count(*) AS relationshipsCreated }
RETURN nodesDeleted,relationshipsDeleted,nodesCreated,relationshipsCreated
'''.replace('__LABELS__',dumps(sorted(ALLOWED_LABELS))).replace('__RELS__',dumps(sorted(ALLOWED_RELS)))

def owned(row):
    p=row['properties'];return p.get('caseId')==DS or p.get('datasetId')==DS or row['key'].startswith(PREFIX)
def split(g):return tuple(canonical({k:[x for x in g[k] if owned(x)==yes] for k in ('nodes','relationships')}) for yes in (True,False))
def expected_type(v):
    if type(v)==bool:return 'BOOLEAN NOT NULL'
    if type(v)==str:return 'STRING NOT NULL'
    if type(v)==int:return 'INTEGER NOT NULL'
    if type(v)==float:return 'FLOAT NOT NULL'
    if type(v)==list:return 'LIST<'+expected_type(v[0])+'> NOT NULL' if v else None
    raise ValueError(type(v))
def verify_exact(g,payload):
    for cat in ('nodes','relationships'):
        a={r['key']:r for r in g[cat]};e={r['properties']['uid']:r for r in payload[cat]}
        require(len(a)==len(g[cat]) and set(a)==set(e),'Identity mismatch '+cat)
        for uid,row in e.items():
            require(a[uid]['properties']==row['properties'],'Property mismatch '+uid)
            if cat=='nodes':require(sorted(a[uid]['labels'])==sorted(row['labels']),'Labels mismatch '+uid)
            else:require(all(a[uid][k]==row[k] for k in ('source','target','type')),'Endpoint/type mismatch '+uid)
            types={p['key']:p['type'] for p in a[uid]['types']}
            for k,v in row['properties'].items():
                t=expected_type(v)
                if t:require(types[k]==t,'Native type mismatch '+uid+'.'+k)
    return True

def frozen_binding(payload):
    # This binding is generated from the recompiled source, never from a caller's edited payload.
    types={row['properties']['uid']:[{'key':k,'type':expected_type(v)} for k,v in row['properties'].items() if expected_type(v)] for row in payload['nodes']+payload['relationships']}
    return {'frozenNodes':copy.deepcopy(payload['nodes']),'frozenRelationships':copy.deepcopy(payload['relationships']),'frozenTypes':types}

def executable_digest():
    names=['compile_model.py','legacy_compile.py','analyze.py','run_graph.py','mcp_client.py']
    return digest({n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in names})

async def main(args):
    w=Path(args.workspace);out=w/'db';path=Path(args.model) if args.model else w/'candidates'/MODEL
    model,payload,assignments=compile_model(path);validate_payload(payload,path,args.model_sha)
    save(w/'generated/payload.json',payload);save(w/'generated/queries.json',queries());save(w/'generated/query-params.json',query_params(payload));(w/'generated/replace.cypher').write_text(REPLACE)
    receipt=out/'execution-stage.json';compiler_sha=executable_digest()
    if receipt.exists():
        s=json.loads(receipt.read_text());require(s['modelSHA256']==args.model_sha and s['payloadSHA256']==digest(payload) and s['compilerSHA256']==compiler_sha,'Execution version conflict');require(args.mode=='verify','Do not resend write; verify existing stage')
    async with connected(out) as call:
        before,_=await snapshot(call,out/('before' if args.mode=='preflight' else 'current'))
        current,preserved=split(before)
        if args.mode=='preflight':
            # Compare current core against the exact archived v1.0 model and compiler.
            old_model,old_payload,_=legacy.compile_model(w/'originals'/MODEL)
            verify_exact(current,old_payload)
            params={**payload,**frozen_binding(payload),'oldNodes':current['nodes'],'oldRelationships':current['relationships']}
            for key,q in {'replace':REPLACE,**queries()}.items():await call('EXPLAIN '+q,params if key=='replace' else query_params(payload),write=True,receipt=out/'explain'/(key+'.json'))
            tests=[]
            for name in ('duplicate-node','missing-endpoint','wrong-label','wrong-type','wrong-namespace','wrong-source','stale-old-node','stale-old-edge','null-uid','changed-property','wrong-native-type','equal-value-wrong-native-type','missing-actor','duplicate-use'):
                p=copy.deepcopy(params)
                if name=='duplicate-node':p['nodes'].append(copy.deepcopy(p['nodes'][0]))
                elif name=='missing-endpoint':p['relationships'][0]['target']='D03V01:NO-SUCH-NODE'
                elif name=='wrong-label':p['nodes'][0]['labels'].append('Unexpected')
                elif name=='wrong-type':p['relationships'][0]['type']='UNEXPECTED'
                elif name=='wrong-namespace':p['nodes'][0]['properties']['caseId']='V01'
                elif name=='wrong-source':p['nodes'][0]['properties']['sourceModelSha256']='wrong'
                elif name=='stale-old-node':p['oldNodes'][0]['properties']['name']='stale'
                elif name=='stale-old-edge':p['oldRelationships'][0]['properties']['uid']='stale'
                elif name=='null-uid':p['nodes'][0]['properties']['uid']=None
                elif name=='changed-property':p['nodes'][0]['properties']['name']='changed-with-same-source-hash'
                elif name=='wrong-native-type':next(n for n in p['nodes'] if n['id']=='E-I01')['properties']['clearWidthM']='2.0'
                elif name=='equal-value-wrong-native-type':next(n for n in p['nodes'] if n['id']=='E-I01')['properties']['clearWidthM']=2
                elif name=='missing-actor':del next(r for r in p['relationships'] if r['type']=='DIRECT_ACCESS_TO')['properties']['actor']
                elif name=='duplicate-use':next(n for n in p['nodes'] if n['id']=='E-C01')['properties']['useValues']=['晾晒','晾晒']
                ret=await call(REPLACE,p,write=True)
                require(ret==[],'Bad payload unexpectedly executed '+name)
                tests.append({'id':name,'rejected':True})
            after,_=await snapshot(call,out/'after-rejections');require(after==before,'Rejection tests changed graph')
            save(out/'rejection-tests.json',tests)
            save(out/'preflight.json',{'status':'passed','explainCount':len(queries())+1,'rejectedPayloads':len(tests),'beforeFingerprint':digest(before),'modelSHA256':args.model_sha,'payloadSHA256':digest(payload),'compilerSHA256':compiler_sha})
            print(json.dumps({'preflight':'passed','nodes':len(payload['nodes']),'relationships':len(payload['relationships']),'rejected':len(tests)}));return
        baseline=json.loads((out/'before/graph.json').read_text());old,untouched=split(baseline)
        if args.mode=='write':
            pre=json.loads((out/'preflight.json').read_text());require(before==baseline and pre['modelSHA256']==args.model_sha and pre['payloadSHA256']==digest(payload) and pre['compilerSHA256']==compiler_sha,'Source/database changed since preflight')
            schema=json.loads((out/'current/schema.json').read_text());require(any(c['labelsOrTypes']==['KGItem'] and c['properties']==['uid'] and c['type']=='UNIQUENESS' for c in schema['constraints']),'UID constraint absent');require(all(i['state']=='ONLINE' for i in schema['indexes']),'Indexes unavailable')
            save(receipt,{'stage':'write-started-no-retry','modelSHA256':args.model_sha,'payloadSHA256':digest(payload),'compilerSHA256':compiler_sha,'beforeFingerprint':digest(baseline),'at':datetime.datetime.now().astimezone().isoformat()})
            validate_payload(payload,path,args.model_sha)
            ret=await call(REPLACE,{**payload,**frozen_binding(compile_model(path)[1]),'oldNodes':old['nodes'],'oldRelationships':old['relationships']},write=True,receipt=out/'write-return.json')
            require(ret==[{'nodesDeleted':len(old['nodes']),'relationshipsDeleted':len(old['relationships']),'nodesCreated':len(payload['nodes']),'relationshipsCreated':len(payload['relationships'])}],'Unexpected write return; inspect without retry')
        after,summary=await snapshot(call,out/'after');new,still=split(after)
        require(still==untouched,'Unrelated graph changed');require(json.loads((out/'after/schema.json').read_text())==json.loads((out/'before/schema.json').read_text()),'Schema changed')
        verify_exact(new,payload);save(out/'D03-readback.json',new)
        results={k:await call(q,query_params(payload),receipt=out/(k+'-raw.json')) for k,q in queries().items()};save(out/'query-results.json',results)
        require(len(results['Q05'])==4 and all(r['cacheConsistent'] for r in results['Q05']),'Core classification mismatch')
        require([r['relativePosition'] for r in results['Q03']]==[0.5,0.25,0.5,0.5],'Core entrances changed')
        require(results['Q07']==[{'crossDatasetEdges':0}],'Cross-dataset edge')
        require([len(results[k]) for k in ('Q09','Q10','Q11','Q12','Q13','Q14','Q15')]==[4,2,4,5,7,4,1],'Missing extension query rows')
        analysis=analyze(new,model['externalExtension']['pathRequests'],model['externalExtension']['rules']);save(out/'analysis-results.json',analysis)
        require(len(analysis['items'])==6,'Missing D03 item')
        require(len(analysis['items']['T01'])==8 and len(analysis['items']['T03'])==8 and all(x['status']=='computed' for x in analysis['items']['T03']),'Space/entry coverage failed')
        # Fixed-case expected states, not the general accepted T06 state domain.
        require(all(x['state'] in ('known','unknown') for x in analysis['items']['T06']) and all(x.get('cacheConsistent',True) for x in analysis['items']['T05']),'Frozen-case use/position verification failed')
        require(all(r['status']=='computed' for r in analysis['items']['T02'] if r['example']=='E'),'Boundary calculation failed')
        require(analysis['items']['T04'][0]['crossings']==3 and analysis['items']['T04'][1]['crossings'] is None,'Known-subgraph path mismatch')
        require(analysis['useSummary']['knownSpaces']==2 and analysis['useSummary']['useAssignments']==4,'Use dedup mismatch')
        areas=next(r for r in analysis['items']['T05'] if r.get('kind')=='area-configuration');require(areas['status']=='computed' and areas['courtyardRatio']==0.3125,'Area ratio mismatch')
        report={'status':'verified-external-synthetic-six-items-new-details-awaiting-review','at':datetime.datetime.now().astimezone().isoformat(),'modelSHA256':args.model_sha,'exactNodes':len(new['nodes']),'exactRelationships':len(new['relationships']),'nativeTypes':'verified','preservedNodes':len(still['nodes']),'preservedRelationships':len(still['relationships']),'preservedFingerprint':digest(still),'originalPreservedFingerprint':digest(untouched),'constraintsIndexesUnchanged':True,'queries':{k:len(v) for k,v in results.items()},'analysisItems':list(analysis['items']),'firstExampleReview':'approved','extensionReview':'pending','empiricalValidity':'not-validated'}
        save(out/'verification.json',report);s=json.loads(receipt.read_text());s.update(stage='verified',verificationFingerprint=digest(report));save(receipt,s);print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);p.add_argument('--model');p.add_argument('--model-sha',required=True);p.add_argument('--mode',choices=['preflight','write','verify'],required=True);asyncio.run(main(p.parse_args()))
