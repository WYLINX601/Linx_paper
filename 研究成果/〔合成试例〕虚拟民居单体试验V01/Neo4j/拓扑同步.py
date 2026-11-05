#!/usr/bin/env python3
"""Archived, guarded incremental V01 update via the already configured official MCP.
No credentials, service configuration, schema changes, or unscoped deletion.
The human has authorized this topology update; prepare is EXPLAIN/read only remotely.
"""
import argparse
import collections
import copy
import importlib.util
import json
import math
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CASE=HERE.parent
ARCHIVE=CASE.parents[1]/'archive/2026-10-26-V01拓扑更新前'
spec=importlib.util.spec_from_file_location('migration',HERE/'迁移与核验.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def graph(c):
    rows=m.call(c,m.EXPORT);assert isinstance(rows,list) and len(rows)==1
    g=rows[0];validation=copy.deepcopy(g)
    # MCP may return a stored FLOAT array as [0, 7.2]. Normalize a disposable copy
    # for the legacy JSON validator, retain raw readback, and verify native DB types below.
    for item in validation['nodes']+validation['relationships']:
        for key,value in item['properties'].items():
            if isinstance(value,list) and value and all(type(v) in (int,float) for v in value):
                item['properties'][key]=[float(v) for v in value]
    m.validate(validation)
    return g

def capture_types(c):
    rows=m.call(c,"MATCH (n) UNWIND keys(n) AS key RETURN 'node' AS kind,n.uid AS uid,key,valueType(n[key]) AS valueType UNION ALL MATCH ()-[r]->() UNWIND keys(r) AS key RETURN 'relationship' AS kind,r.uid AS uid,key,valueType(r[key]) AS valueType")
    return sorted(rows,key=lambda r:(r['kind'],r['uid'],r['key']))

def typed_archive():
    """Restore FLOAT vs INTEGER information lost by MCP's JSON serialization."""
    original=m.read(ARCHIVE/'数据库完整快照.json');old=copy.deepcopy(original)
    types=m.read(ARCHIVE/'数据库属性类型.json')['properties']
    records={(kind,r['properties']['uid']):r['properties'] for group,kind in [('nodes','node'),('relationships','relationship')] for r in old[group]}
    assert len(types)==sum(len(p) for p in records.values())
    assert len({(r['kind'],r['uid'],r['key']) for r in types})==len(types)
    for row in types:
        p=records[(row['kind'],row['uid'])];key=row['key'];typ=row['valueType']
        assert key in p
        if typ.startswith('FLOAT'):p[key]=float(p[key])
        elif typ.startswith('INTEGER'):p[key]=int(p[key])
        elif typ.startswith('LIST<FLOAT'):p[key]=list(map(float,p[key]))
        elif typ.startswith('LIST<INTEGER'):p[key]=list(map(int,p[key]))
        else:assert typ.startswith(('STRING','BOOLEAN','LIST<STRING','LIST<BOOLEAN','LIST<NOTHING')),(row,p[key])
    assert m.canonical(old)==m.canonical(original),'Type restoration changed property values'
    return old

def transition(old,new):
    """Guard the complete observed state, then alter only an explicitly enumerated delta.
    UID is stable; both existing nodes and existing relationships are locked and compared.
    """
    m.validate(old);m.validate(new)
    on={n['properties']['uid']:n for n in old['nodes']};nn={n['properties']['uid']:n for n in new['nodes']}
    oe={r['properties']['uid']:r for r in old['relationships']};ne={r['properties']['uid']:r for r in new['relationships']}
    assert len(oe)==len(old['relationships']) and len(ne)==len(new['relationships'])
    for uid in on.keys()&nn.keys():
        assert sorted(on[uid]['labels'])==sorted(nn[uid]['labels']),'Unexpected label migration'
    for uid in oe.keys()&ne.keys():
        assert {k:oe[uid][k] for k in ('source','target','type','properties')}=={k:ne[uid][k] for k in ('source','target','type','properties')},'Existing relationship modification outside delta'
    for rec in old['nodes']+new['nodes']:
        assert rec['properties']['datasetId']=='V01' and rec['properties']['uid'].startswith('V01:')
    params={'oldNodes':old['nodes'],'oldRels':old['relationships'],
            'updateNodes':[nn[k] for k in sorted(on.keys()&nn.keys())],
            'deleteNodes':sorted(on.keys()-nn.keys()),'deleteRels':sorted(oe.keys()-ne.keys())}
    q='''CALL { UNWIND $oldNodes AS row MATCH (n:KGItem {uid:row.properties.uid})
WITH n ORDER BY n.uid SET n.uid=n.uid RETURN count(n) AS lockedNodes }
CALL { UNWIND $oldRels AS row MATCH ()-[r]->() WHERE r.uid=row.properties.uid
WITH r ORDER BY r.uid SET r.uid=r.uid RETURN count(r) AS lockedRels }
CALL { MATCH (n) RETURN count(n) AS liveNodes }
CALL { MATCH ()-[r]->() RETURN count(r) AS liveRels }
CALL { UNWIND $oldNodes AS row OPTIONAL MATCH (n:KGItem {uid:row.properties.uid})
RETURN sum(CASE WHEN n IS NOT NULL AND properties(n)=row.properties
AND size(labels(n))=size(row.labels) AND all(l IN row.labels WHERE l IN labels(n)) THEN 1 ELSE 0 END) AS equalNodes }
CALL { UNWIND $oldRels AS row OPTIONAL MATCH (a)-[r]->(b) WHERE r.uid=row.properties.uid
RETURN sum(CASE WHEN r IS NOT NULL AND a.uid=row.source AND b.uid=row.target
AND type(r)=row.type AND properties(r)=row.properties THEN 1 ELSE 0 END) AS equalRels }
WITH * WHERE lockedNodes=liveNodes AND lockedRels=liveRels
AND liveNodes=size($oldNodes) AND liveRels=size($oldRels)
AND equalNodes=liveNodes AND equalRels=liveRels
CALL { UNWIND $deleteRels AS uid MATCH ()-[r]->() WHERE r.uid=uid DELETE r RETURN count(*) AS deletedRelationships }
CALL { UNWIND $deleteNodes AS uid MATCH (n:KGItem {uid:uid}) DELETE n RETURN count(*) AS deletedNodes }
CALL { UNWIND $updateNodes AS row MATCH (n:KGItem {uid:row.properties.uid})
SET n=row.properties RETURN count(n) AS updatedNodes }
'''
    newg={'nodes':[nn[k] for k in sorted(nn.keys()-on.keys())], 'relationships':[ne[k] for k in sorted(ne.keys()-oe.keys())]}
    blocks,pp=m.import_blocks(newg)
    # CREATE is safe here: all original records are guarded and new UIDs absent from
    # the full old graph. Existing uniqueness constraint remains active.
    q+='\n'.join(blocks)
    q+='\nRETURN updatedNodes,deletedNodes,deletedRelationships,'+str(len(newg['nodes']))+' AS createdNodes,'+str(len(newg['relationships']))+' AS createdRelationships'
    params.update(pp)
    return q,params

def prepare(c):
    original=m.read(ARCHIVE/'数据库完整快照.json');current=graph(c);new=m.desired()
    assert m.canonical(current)==m.canonical(original),'Live state changed since archive; do not overwrite'
    typefile=ARCHIVE/'数据库属性类型.json';types=capture_types(c)
    if typefile.exists():
        assert m.read(typefile)['properties']==types,'Live property types changed since capture'
    else:m.save(typefile,{'capturedAt':m.now(),'source':'Neo4j valueType, before authorized topology update','properties':types})
    old=typed_archive()
    assert len(new['nodes'])==43 and len(new['relationships'])==191
    q,p=transition(old,new);rq,rp=transition(new,old)
    (HERE/'拓扑更新.cypher').write_text(q+'\n');m.save(HERE/'拓扑更新参数.json',p)
    (ARCHIVE/'回退本轮更新.cypher').write_text(rq+'\n');m.save(ARCHIVE/'回退参数.json',rp)
    plan=m.call(c,'EXPLAIN '+q,p,True);rplan=m.call(c,'EXPLAIN '+rq,rp,True)
    result={'status':'prepared','preparedAt':m.now(),'archiveFileSha256':m.sha((ARCHIVE/'数据库完整快照.json').read_bytes()),
            'archiveTypesSha256':m.sha(typefile.read_bytes()),
            'sourceModelSha256':m.sha((CASE/'案例模型.json').read_bytes()),'sourceNodeCount':42,
            'oldNodes':41,'oldRelationships':166,'newNodes':43,'newRelationships':191,
            'delta':{'addedNodes':2,'addedRelationships':25,'deletedNodes':0,'deletedRelationships':0,'refreshedSourceNodes':41},
            'queryExplain':plan,'rollbackExplain':rplan,'querySha256':m.sha(q.encode()),'parameterSha256':m.sha(p),
            'authorization':'2026-10-26 user explicitly authorized construction, extension, and Neo4j CRUD update.',
            'schemaPolicy':'Retain KGItem.uid uniqueness constraint and existing indexes; no server/permission changes'}
    m.save(HERE/'拓扑更新预检.json',result)
    print(m.js({k:result[k] for k in ('status','oldNodes','oldRelationships','newNodes','newRelationships','delta')}))

QUERIES=[
    ('拓扑关系分布',"MATCH (a:V01)-[r]->(b:V01) WHERE type(r) IN ['AXIS_JOINS','ENVELOPE_INTERSECTS','SHARES_BOUNDARY'] RETURN type(r) AS relationType,count(*) AS count ORDER BY relationType"),
    ('前院南墙交接',"MATCH (w:V01:Wall {id:'W10'})-[r:AXIS_JOINS]-(b:V01:Wall) RETURN b.id AS wall,r.junctionXY AS intersection,startNode(r).id AS storedSource,r.atSource AS atStoredSource,endNode(r).id AS storedTarget,r.atTarget AS atStoredTarget ORDER BY wall"),
    ('墙柱包络及未知构造',"MATCH (w:V01:Wall)-[r:ENVELOPE_INTERSECTS]->(c:V01:Column) RETURN w.id AS wall,c.id AS column,r.intersectionKind AS geometryResult,r.atWall AS wallPosition,r.commonZ AS commonZ,r.recordStatus AS status ORDER BY wall,column"),
    ('坡面共边与长度',"MATCH (a:V01:RoofSurface)-[r:SHARES_BOUNDARY]->(b:V01:RoofSurface) RETURN a.id AS source,b.id AS target,r.boundaryRole AS role,point.distance(point({x:r.boundaryStart[0],y:r.boundaryStart[1],z:r.boundaryStart[2]}),point({x:r.boundaryEnd[0],y:r.boundaryEnd[1],z:r.boundaryEnd[2]})) AS lengthM"),
    ('坡面归属与面积',"MATCH (s:V01:RoofSurface)-[:PART_OF]->(r:V01:Roof) RETURN r.id AS roof,count(s) AS surfaces,sum(s.areaM2) AS areaM2"),
    ('通行链保留',"MATCH p=shortestPath((a:V01:Space {id:'S06'})-[:DIRECT_ACCESS_TO*1..6]-(b:V01:Space {id:'S03'})) WHERE all(r IN relationships(p) WHERE r.bidirectional=true) RETURN [n IN nodes(p)|n.id] AS spaces,length(p) AS steps"),
    ('几何边来源规则',"MATCH (:V01)-[r]->(:V01) WHERE type(r) IN ['AXIS_JOINS','ENVELOPE_INTERSECTS','SHARES_BOUNDARY'] RETURN count(r) AS total,sum(CASE WHEN r.ruleId IS NOT NULL AND 'EV01' IN r.evidenceIds AND r.recordStatus='synthetic_geometry_derived' THEN 1 ELSE 0 END) AS traced"),
    ('新增坡面无材料继承',"MATCH (n:V01:RoofSurface) RETURN n.id AS id,[l IN labels(n) WHERE l STARTS WITH '材质_'] AS materialLabels ORDER BY id"),
]

def verify(c):
    expected=m.desired();actual=graph(c)
    assert m.canonical(actual)==m.canonical(expected),'Live graph differs from canonical projection'
    results=[{'name':name,'query':q,'result':m.call(c,q)} for name,q in QUERIES]
    assert results[0]['result']==[{'relationType':'AXIS_JOINS','count':12},{'relationType':'ENVELOPE_INTERSECTS','count':4},{'relationType':'SHARES_BOUNDARY','count':1}]
    assert [r['wall'] for r in results[1]['result']]==['W08','W09']
    assert len(results[2]['result'])==4 and all(r['geometryResult']=='interior_overlap' for r in results[2]['result'])
    assert len(results[3]['result'])==1
    ridge=results[3]['result'][0]
    assert {k:ridge[k] for k in ['source','target','role']}=={'source':'RS01','target':'RS02','role':'ridge'}
    assert math.isclose(ridge['lengthM'],10.8,rel_tol=0,abs_tol=1e-9)  # arithmetic, not survey tolerance
    assert results[4]['result'][0]['surfaces']==2 and abs(results[4]['result'][0]['areaM2']-103.78)<.0001
    assert results[5]['result']==[{'spaces':['S06','S05','S04','S01','S03'],'steps':4}]
    assert results[6]['result']==[{'total':17,'traced':17}]
    assert all(not r['materialLabels'] for r in results[7]['result'])
    assert m.call(c,'MATCH (n:KGItem) WITH n.uid AS uid,count(*) AS c WHERE c>1 RETURN uid,c')==[]
    assert m.call(c,'MATCH ()-[r]->() WITH r.uid AS uid,count(*) AS c WHERE c>1 RETURN uid,c')==[]
    # Check numeric types in Neo4j, not only JSON equality (MCP serializes 1.0 as 1).
    numeric=[]
    for group,entity in [('nodes','n'),('relationships','r')]:
        rows=[]
        for item in expected[group]:
            for key,value in item['properties'].items():
                if type(value) in (int,float):
                    rows.append({'uid':item['properties']['uid'],'key':key,'expectedType':'INTEGER' if type(value)==int else 'FLOAT'})
                elif isinstance(value,list) and value and type(value[0]) in (int,float):
                    rows.append({'uid':item['properties']['uid'],'key':key,'expectedType':'LIST<'+('INTEGER' if type(value[0])==int else 'FLOAT')})
        pattern='(n:KGItem)' if entity=='n' else '()-[r]->()'
        query=f'UNWIND $rows AS row MATCH {pattern} WHERE {entity}.uid=row.uid RETURN row.uid AS uid,row.key AS key,row.expectedType AS expectedType,valueType({entity}[row.key]) AS actualType'
        checked=m.call(c,query,{'rows':rows});assert len(checked)==len(rows)
        assert all(x['actualType'].startswith(x['expectedType']) for x in checked)
        numeric.extend(checked)
    report={'status':'verified','verifiedAt':m.now(),'sourceModelSha256':m.sha((CASE/'案例模型.json').read_bytes()),
            'nodeCount':len(actual['nodes']),'domainAndEvidenceNodes':42,'sourceSnapshotNodes':1,'relationshipCount':len(actual['relationships']),
            'comparison':'Every node label/property value and relationship type/endpoint/property value matches canonical projection; numeric database types separately checked. MCP integral-float JSON display normalization is allowed, not byte-hash equality.',
            'queries':results,'numericTypeChecks':numeric,'scope':'synthetic case and scoped geometry; not field, structural, Browser favorite or concurrency stress validation'}
    m.save(HERE/'拓扑入库核验.json',report)
    print(m.js({'status':'verified','nodes':len(actual['nodes']),'relationships':len(actual['relationships']),'functionalQueries':len(results),'numericTypeChecks':len(numeric)}))

def apply(c):
    pre=m.read(HERE/'拓扑更新预检.json');old=typed_archive();expected=m.desired()
    assert m.sha((ARCHIVE/'数据库完整快照.json').read_bytes())==pre['archiveFileSha256']
    assert m.sha((ARCHIVE/'数据库属性类型.json').read_bytes())==pre['archiveTypesSha256']
    assert m.sha((CASE/'案例模型.json').read_bytes())==pre['sourceModelSha256']
    current=graph(c)
    if m.canonical(current)==m.canonical(expected):
        print(m.js({'status':'already_applied_no_write'}));return verify(c)
    assert m.canonical(current)==m.canonical(old),'Live graph changed; stop'
    assert capture_types(c)==m.read(ARCHIVE/'数据库属性类型.json')['properties'],'Live property types changed; stop'
    q,p=transition(old,expected)
    assert q.strip()==(HERE/'拓扑更新.cypher').read_text().strip() and p==m.read(HERE/'拓扑更新参数.json')
    assert m.sha(q.encode())==pre['querySha256'] and m.sha(p)==pre['parameterSha256']
    receipt=m.call(c,q,p,True)
    m.save(HERE/'拓扑更新回执.json',{'appliedAt':m.now(),'receipt':receipt,'sourceModelSha256':pre['sourceModelSha256']})
    assert receipt==[{'updatedNodes':41,'deletedNodes':0,'deletedRelationships':0,'createdNodes':2,'createdRelationships':25}],receipt
    verify(c)

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','apply','verify']);mode=p.parse_args().mode
    c,info=m.connect()
    try:{'prepare':prepare,'apply':apply,'verify':verify}[mode](c)
    finally:c.close()

if __name__=='__main__':main()
