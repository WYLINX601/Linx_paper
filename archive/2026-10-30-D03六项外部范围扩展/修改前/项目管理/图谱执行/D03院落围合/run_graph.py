"""First-create or verify D03V01 via configured MCP; never update other scopes.
Requires an explicit frozen model hash and mode. No blind retries or upserts.
"""
import argparse,asyncio,copy,datetime,hashlib,json
from pathlib import Path
from compile_model import compile_model,query_params,validate_payload,require,IMPORT,queries,DS,PREFIX,MODEL
from mcp_client import connected,snapshot,save,digest,canonical

def owned(row):
    p=row['properties']
    return p.get('caseId')==DS or p.get('datasetId')==DS or row['key'].startswith(PREFIX)

def split(g):
    new={k:[x for x in g[k] if owned(x)] for k in ['nodes','relationships']}
    old={k:[x for x in g[k] if not owned(x)] for k in ['nodes','relationships']}
    return canonical(new),canonical(old)

def expected_type(v):
    if isinstance(v,bool):return 'BOOLEAN NOT NULL'
    if isinstance(v,str):return 'STRING NOT NULL'
    if isinstance(v,int):return 'INTEGER NOT NULL'
    if isinstance(v,float):return 'FLOAT NOT NULL'
    if isinstance(v,list):
        return 'LIST<'+expected_type(v[0])+'> NOT NULL' if v else None
    raise ValueError(type(v))

def verify_exact(g,payload):
    for category in ['nodes','relationships']:
        expected={x['properties']['uid']:x for x in payload[category]}
        actual={x['key']:x for x in g[category]}
        require(len(actual)==len(g[category]) and set(actual)==set(expected),'Identity/count mismatch '+category)
        for uid,e in expected.items():
            a=actual[uid];require(a['properties']==e['properties'],'Property mismatch '+uid)
            if category=='nodes':require(sorted(a['labels'])==sorted(e['labels']),'Label mismatch '+uid)
            else:require(all(a[k]==e[k] for k in ['source','target','type']),'Endpoint/type mismatch '+uid)
            types={x['key']:x['type'] for x in a['types']}
            for k,v in e['properties'].items():
                t=expected_type(v)
                if t:require(types[k]==t,'Native type mismatch '+uid+'.'+k+': '+types[k]+' expected '+t)
    return {'exactNodes':len(g['nodes']),'exactRelationships':len(g['relationships']),'propertiesAndNativeTypes':'equal'}

async def main(args):
    d=Path(args.workspace).resolve(); out=d/'db'; path=Path(args.model) if args.model else d/'candidates'/MODEL
    model,payload,assignments=compile_model(path)
    validate_payload(payload,path,args.model_sha)
    receipt=out/'execution-stage.json'
    if receipt.exists():
        previous=json.loads(receipt.read_text())
        require(previous['modelSHA256']==args.model_sha,'Reconcile different execution source')
        require(previous['payloadSHA256']==digest(payload),'Compiled payload changed; reconcile before verification')
        require(previous['compilerSHA256']==hashlib.sha256(Path(__file__).with_name('compile_model.py').read_bytes()).hexdigest(),'Compiler changed; reconcile before verification')
        require(args.mode=='verify','Prior execution exists; inspect/read back with verify, do not resend')
    async with connected(out) as call:
        before,summary=await snapshot(call,out/('write-before' if args.mode=='write' else 'verify-before'))
        new,old=split(before)
        if args.mode=='write':
            require(not new['nodes'] and not new['relationships'],'Namespace not empty; use verification, not replacement')
            baseline=json.loads((out/'post-guard/graph.json').read_text())
            require(before==baseline,'Database changed since rejection tests')
            schema=json.loads((out/'write-before/schema.json').read_text())
            require(any(c['labelsOrTypes']==['KGItem'] and c['properties']==['uid'] and c['type']=='UNIQUENESS' for c in schema['constraints']),'Required existing uniqueness constraint absent')
            require(all(i['state']=='ONLINE' for i in schema['indexes']),'Indexes not ONLINE')
            save(receipt,{'stage':'write-started-no-retry','modelSHA256':args.model_sha,'payloadSHA256':digest(payload),'compilerSHA256':hashlib.sha256(Path(__file__).with_name('compile_model.py').read_bytes()).hexdigest(),'beforeFingerprint':digest(before),'at':datetime.datetime.now().astimezone().isoformat()})
            validate_payload(payload,path,args.model_sha)
            result=await call(IMPORT,payload,write=True,receipt=out/'import-return.json')
            require(result==[{'nodesCreated':len(payload['nodes']),'relationshipsCreated':len(payload['relationships'])}],'Import rejected or unexpected returned counts; read back without retry')
        after,summary_after=await snapshot(call,out/'after')
        new,old_after=split(after)
        baseline=json.loads((out/'write-before/graph.json').read_text())
        require(old_after==baseline,'Existing graph fingerprint changed')
        require(json.loads((out/'after/schema.json').read_text())==json.loads((out/'write-before/schema.json').read_text()),'Constraints or indexes changed')
        exact=verify_exact(new,payload);save(out/'D03-readback.json',new)
        results={k:await call(q,query_params(payload),receipt=out/(k+'-raw.json')) for k,q in queries().items()}
        require(len(results['Q01'])==4 and len(results['Q02'])==16 and len(results['Q03'])==4,'Missing functional rows')
        require(all(x['valid'] for x in results['Q03']),'Entrance validity failed')
        require([x['relativePosition'] for x in results['Q03']]==[0.5,0.25,0.5,0.5],'Entrance results differ')
        require(len(results['Q04'])==26 and len(results['Q05'])==4,'Missing provenance/classification rows')
        require(all(x['cacheConsistent'] for x in results['Q05']),'Classification cache mismatch')
        require([(r['example'],r['resultStatus'],r['candidateType']) for r in results['Q05']]==[(x['example'],x['status'],x['candidateType']) for x in assignments],'Classification results differ')
        require(results['Q07']==[{'crossDatasetEdges':0}],'Cross dataset edge')
        save(out/'query-results.json',results)
        negative=[]
        for kind in ['wrong-model-hash','different-rule-content']:
            p=query_params(payload)
            if kind=='wrong-model-hash':p['modelSha']='not-the-source'
            else:p=copy.deepcopy(p);p['expectedRule']['definitionJson']='{}'
            r=await call(queries()['Q05'],p)
            require(len(r)==4 and all(x['resultStatus']=='invalid-input' for x in r),'Read-only mismatch not rejected')
            negative.append({'id':kind,'returned':r,'passed':True})
        save(out/'readback-negative-tests.json',negative)
        report={'status':'verified-technical-only-user-review-pending','at':datetime.datetime.now().astimezone().isoformat(),'modelSHA256':args.model_sha,**exact,'globalNodes':summary_after['nodes'],'globalRelationships':summary_after['relationships'],'oldNodes':len(baseline['nodes']),'oldRelationships':len(baseline['relationships']),'oldFingerprint':digest(baseline),'preservedFingerprint':digest(old_after),'oldGraphUnchanged':True,'constraintsIndexesUnchanged':True,'queries':{k:len(v) for k,v in results.items()},'readOnlyMismatchTests':len(negative),'sourceRuleBoundary':'four synthetic examples; not empirical validity; no native Neo4j GUI check'}
        save(out/'verification.json',report)
        stage=json.loads(receipt.read_text());stage.update(stage='verified',verificationFingerprint=digest(report));save(receipt,stage)
        print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',required=True);p.add_argument('--model');p.add_argument('--model-sha',required=True);p.add_argument('--mode',choices=['write','verify'],required=True)
    asyncio.run(main(p.parse_args()))
