"""Deterministic D03 analysis of genuine readback; no assumed unseen edges.
Geometry uses Shapely in 2D metres. Paths count explicit directed boundaries only.
"""
import json,math
from collections import deque,Counter
from shapely.geometry import Polygon,LineString
from shapely.ops import unary_union,substring
from compile_model import valid_polygon,require,PREFIX

def analyze(graph,requests,expected_rule):
    N={n['key']:n for n in graph['nodes']};R=graph['relationships'];P={k:n['properties'] for k,n in N.items()}
    rule=P.get(PREFIX+'R02',{})
    require(expected_rule.get('version')=='D03-external-1.0' and json.loads(rule.get('definitionJson','{}'))==expected_rule and rule.get('ruleVersion')==expected_rule['version'],'Analysis rule differs from frozen source/program')
    def supported(uid,fields):
        ss=[r for r in R if r['source']==uid and r['type']=='HAS_SOURCE']
        if P[uid].get('exampleId')=='E' and (P[uid].get('analysisRuleUid')!=PREFIX+'R02' or P[uid].get('analysisRuleVersion')!=expected_rule['version']):return False
        return any(set(fields)<=set(r['properties'].get('fields',[])) and r['target'] in P and r['properties'].get('sourceVersion')==P[r['target']].get('sourceVersion') and (P[uid].get('sourceVersion',r['properties']['sourceVersion'])==r['properties']['sourceVersion']) and r['properties'].get('locator') and r['properties'].get('locator')==P[uid].get('sourceLocator',r['properties']['locator']) and r['properties'].get('sourceModelSha256')==P[uid].get('sourceModelSha256') for r in ss)
    def rel_supported(r):
        p=r['properties'];return p.get('sourceUid') in P and p.get('sourceVersion')==P[p['sourceUid']].get('sourceVersion') and bool(p.get('locator')) and set(['source','target','type'])<=set(p.get('fields',[])) and p.get('analysisRuleVersion')==expected_rule['version'] and p.get('analysisRuleUid')==PREFIX+'R02' and p.get('sourceModelSha256')==P[p['sourceUid']].get('sourceModelSha256')
    def polygon(uid):
        p=P[uid];require(p.get('geometryComplete') is True,'Incomplete geometry');require(p.get('unit')=='m','Non-metric geometry')
        require(supported(uid,['polygonJson','geometryComplete','unit','geometryVersion','level','coordinateFrame','geometryBasis']),'Geometry provenance invalid')
        return valid_polygon(json.loads(p['polygonJson']))
    def compatible(ids):
        vals=[P[k] for k in ids]
        return all(len({p.get(f) for p in vals})==1 and vals[0].get(f) is not None for f in ('unit','level','coordinateFrame','geometryBasis','geometryVersion'))
    T={f'T{i:02}':[] for i in range(1,7)}
    spaces=sorted(k for k,n in N.items() if 'Space' in n['labels'])
    for uid in spaces:
        p=P[uid];ext=p.get('exampleId')=='E'
        T['T01'].append({'uid':uid,'name':p['name'],'example':p['exampleId'],'level':p.get('level'),'boundaryBasis':p.get('boundaryBasis',p.get('interpretation')),'geometryComplete':p.get('geometryComplete','reference-ring-only'),'geometryRole':'二维分析范围，非完整三维体','coverage':p.get('coverState','not-assessed'),'state':'synthetic-declared','sourceLocator':p.get('sourceLocator')})
        if not ext:
            bs=json.loads(p['boundarySegmentsJson'])
            T['T02'].append({'uid':uid,'example':p['exampleId'],'segments':bs,'status':'not-assessed-net-length','netSolidLengthM':None,'ratio':None,'reason':'首例只声明粗粒度侧类；未提供逐段实体及扣洞覆盖，不能由building/wall类别直接算净比例'})
            T['T06'].append({'uid':uid,'example':p['exampleId'],'state':'unknown','uses':[],'reason':'首例没有用途证据，不由名称或几何补值'})
            try:
                g=valid_polygon([b['startXY'] for b in bs]+[bs[0]['startXY']])
                T['T05'].append({'kind':'reference-area','uid':uid,'example':p['exampleId'],'areaM2':g.area,'status':'synthetic-reference-only','ratio':None,'reason':'仅人工闭合参照轮廓面积；整体边界未知，不能给全宅比例；围合参与未知不等于参照轮廓未定义'})
            except (ValueError,KeyError):T['T05'].append({'uid':uid,'status':'invalid-geometry','areaM2':None})
            continue
        if p.get('boundaryRecordsJson'):
            bs=json.loads(p['boundaryRecordsJson']);perimeter=known=solid=0.0;complete=True;segments=[]
            try:
                g=polygon(uid)
                require(supported(uid,['boundaryRecordsJson']),'Boundary provenance')
                require(bs and len({b['id'] for b in bs})==len(bs),'Boundary identities')
                lines=[]
                for j,b in enumerate(bs):
                    line=LineString(b['polyline']);L=line.length;perimeter+=L;lines.append(line)
                    require(line.is_simple and L>0 and g.boundary.covers(line),'Off-boundary segment')
                    require(b['polyline'][-1]==bs[(j+1)%len(bs)]['polyline'][0],'Broken ring')
                    if b['state']!='known' or b['solidState']!='known':complete=False;segments.append({'id':b['id'],'state':'unknown','lengthM':L});continue
                    require(b['kind'] in ('building','wall','open','covered-transition'),'Unknown kind')
                    if b['kind'] in ('building','wall','covered-transition'):require(b['participantId'] is not None,'Known participant missing')
                    particip=[r for r in R if r['source']==uid and r['type']=='BOUNDARY_PARTICIPANT' and r['properties'].get('boundaryId')==b['id']]
                    if b['participantId']:
                        require(len(particip)==1 and particip[0]['target']==PREFIX+b['participantId'] and rel_supported(particip[0]),'Participant mismatch')
                    else:require(not particip,'Unexpected participant')
                    last=-1.0;net=0.0
                    for a,z in b['solidIntervalsM']:require(0<=a<z<=L and a>=last,'Invalid solid interval');last=z;net+=z-a
                    if b['kind'] in ('open','covered-transition'):require(net==0,'Open/covered transition falsely solid')
                    if b['kind'] in ('wall','building'):
                        for e in P.values():
                            if e.get('referenceSpaceUid')==uid and e.get('referenceBoundaryId')==b['id']:
                                require(all(min(z,e['endChainageM'])<=max(a,e['startChainageM']) for a,z in b['solidIntervalsM']),'Opening counted as solid')
                    known+=L;solid+=net;segments.append({'id':b['id'],'kind':b['kind'],'participantId':b['participantId'],'lengthM':L,'solidLengthM':net,'cover':b['coverState']})
                require(abs(unary_union(lines).length-perimeter)<1e-9 and abs(g.length-perimeter)<1e-9,'Boundary duplicated or not exhaustive')
                status='computed' if complete and perimeter>0 else 'unknown-stopped'
                T['T02'].append({'uid':uid,'example':'E','status':status,'perimeterM':perimeter,'knownLengthM':known,'netSolidLengthM':solid,'coverageRatio':known/perimeter if perimeter else None,'ratio':solid/perimeter if status=='computed' else None,'segments':segments,'rule':'声明分析层位：扣门洞，廊盖不计实体；不等于三维闭合度或人的感受'})
            except (ValueError,KeyError,TypeError) as e:T['T02'].append({'uid':uid,'example':'E','status':'invalid-input','ratio':None,'reason':str(e)})
        state=p.get('useState','unknown');uses=p.get('useValues',[])
        valid=(state in ('known','unknown','none','not-applicable') and isinstance(uses,list) and all(isinstance(x,str) and x for x in uses) and len(uses)==len(set(uses)) and (bool(uses)==(state=='known')) and p.get('useScope')=='this-space' and p.get('useEvidenceRole')=='synthetic-assignment' and supported(uid,['useState','useValues','useContext','useScope','useLocator','useEvidenceRole']))
        T['T06'].append({'uid':uid,'example':'E','state':state if valid else 'invalid-input','uses':uses if valid else [],'context':p.get('useContext'),'sourceLocator':p.get('useLocator'),'evidenceRole':p.get('useEvidenceRole'),'reason':'多用途仍是一个空间；仅人工设定，不是现实用途调查'})
    for uid,n in sorted(N.items()):
        if 'EntranceInterface' not in n['labels']:continue
        p=P[uid]
        if p.get('exampleId')!='E':
            valid=supported(uid,['startChainageM','endChainageM','referenceLengthM','referenceBoundaryId','referenceGeometryVersion']) and 0<=p['startChainageM']<p['endChainageM']<=p['referenceLengthM']
            T['T03'].append({'uid':uid,'example':p['exampleId'],'status':'computed' if valid else 'invalid-input','relativePosition':(p['startChainageM']+p['endChainageM'])/2/p['referenceLengthM'] if valid else None,'farSide':'unknown','passage':'not-assessed','hostUid':p['expectedHostUid']});continue
        try:
            require(supported(uid,['startChainageM','endChainageM','referencePolylineJson','referenceSpaceUid','referenceBoundaryId','referenceGeometryVersion','correspondence','unit']),'Entry provenance')
            c=P[p['referenceSpaceUid']];b=next(x for x in json.loads(c['boundaryRecordsJson']) if x['id']==p['referenceBoundaryId'])
            require(p['referenceGeometryVersion']==c['geometryVersion'] and p['unit']==c['unit']=='m','Entry reference mismatch')
            require(p['correspondence']=='unique-on-reference-line' and json.loads(p['referencePolylineJson'])==b['polyline'],'Ambiguous correspondence')
            line=LineString(b['polyline']);sa=p['startChainageM'];sb=p['endChainageM'];require(line.length==p['referenceLengthM'] and 0<=sa<sb<=line.length,'Invalid entry length')
            segment=substring(line,sa,sb)
            for endpoint in [p['fromSpaceUid']]+([p['toSpaceUid']] if p['toSpaceUid'] else []):
                require(all(P[endpoint][k]==c[k] for k in ('unit','level','coordinateFrame','geometryVersion','floorZM')) and p['level']==P[endpoint]['level'],'Entry side references incompatible')
                require(polygon(endpoint).boundary.covers(segment),'Entry segment not on both declared sides')
            rels=[r for r in R if r['source']==uid and r['type']=='INTERFACE_OF'];expected=[('side-a',p['fromSpaceUid'])]+([('side-b',p['toSpaceUid'])] if p['toSpaceUid'] else [])+([('opening-host',p['hostUid'])] if p['hostUid'] else [])
            require(sorted((r['properties']['role'],r['target']) for r in rels)==sorted(expected) and all(rel_supported(r) for r in rels),'Entry role mismatch')
            mid=line.interpolate((sa+sb)/2)
            T['T03'].append({'uid':uid,'example':'E','status':'computed','relativePosition':(sa+sb)/2/line.length,'centerXY':[mid.x,mid.y],'from':p['fromSpaceUid'],'to':p['toSpaceUid'] or None,'farSide':p['farSideState'],'hostUid':p['hostUid'] or None,'scope':'唯一折线里程；不设居中阈值，不凭入口推通行'})
        except (ValueError,KeyError,TypeError,StopIteration) as e:T['T03'].append({'uid':uid,'example':'E','status':'invalid-input','relativePosition':None,'reason':str(e)})
    valid_entries={x['uid'] for x in T['T03'] if x['example']=='E' and x['status']=='computed'}
    access=[];invalid_access=[]
    for r in R:
        if r['type']!='DIRECT_ACCESS_TO' or r['properties'].get('exampleId')!='E':continue
        p=r['properties'];i=P.get(p.get('viaUid'),{})
        u=P[PREFIX+'E-U01']
        ok=(p.get('viaUid') in valid_entries and {r['source'],r['target']}=={i.get('fromSpaceUid'),i.get('toSpaceUid')} and p.get('state')=='passable-asserted' and p.get('evidenceRole')=='synthetic-explicit-passage-assertion' and all(p.get(k) for k in ('contextId','actor','doorState','obstacleState','observationTime')) and rel_supported(r) and supported(PREFIX+'E-U01',['passageContextId','passageActor','passageSnapshot']) and p['contextId']==u['passageContextId'] and p['actor']==u['passageActor'] and p['observationTime']==u['passageSnapshot'])
        (access if ok else invalid_access).append(r)
    for req in requests:
        a=PREFIX+req['from'];b=PREFIX+req['to'];context=req['contextId'];queue=deque([(a,[a],[])]);seen={a};found=None
        if context!=P[PREFIX+'E-U01']['passageContextId'] or a not in spaces or b not in spaces or any(P[x].get('exampleId')!='E' for x in (a,b)):
            T['T04'].append({'from':a,'to':b,'context':context,'status':'invalid-request-context','path':[],'crossings':None,'scope':'请求须指向E例空间及明确的冻结情境'});continue
        if a in N and b in N:
            while queue:
                here,path,edges=queue.popleft()
                if here==b:found=(path,edges);break
                for r in sorted(access,key=lambda r:r['key']):
                    if r['source']==here and r['properties']['contextId']==context and r['target'] not in seen:
                        seen.add(r['target']);queue.append((r['target'],path+[r['target']],edges+[r['key']]))
        T['T04'].append({'from':a,'to':b,'context':context,'status':'confirmed-path-in-known-subgraph' if found else 'no-confirmed-path-not-unreachable','path':found[0] if found else [],'edgeIds':found[1] if found else [],'crossings':len(found[1]) if found else None,'scope':'仅已知外部有向子图；非全宅最短、非步行距离','rejectedEdges':[r['key'] for r in invalid_access]})
    for code in 'ABCD':T['T04'].append({'example':code,'status':'not-assessed','crossings':None,'reason':'外侧未知、没有直接通行证据；不补边'})
    ids=[k for k in spaces if P[k].get('exampleId')=='E'];courts=[k for k in ids if 'Courtyard' in N[k]['labels']];uid=PREFIX+'E-U01'
    try:
        require(compatible([uid]+ids),'Incompatible area coordinate/level/basis/version')
        unit=polygon(uid);gs={k:polygon(k) for k in ids};require(all(unit.covers(g) for g in gs.values()),'Area outside denominator')
        union=unary_union(list(gs.values()));cu=unary_union([gs[k] for k in courts]);s=sum(g.area for g in gs.values())
        buildings=[k for k,n in N.items() if 'Building' in n['labels'] and P[k].get('exampleId')=='E']
        require(compatible([uid]+buildings),'Building plane incompatible')
        bg=[polygon(k) for k in buildings];require(all(unit.covers(g) for g in bg),'Building outside denominator')
        require(all(g.intersection(union).area<1e-9 for g in bg),'Space-building analysis footprints overlap')
        T['T05'].append({'kind':'area-configuration','example':'E','status':'computed','denominatorUid':uid,'denominatorM2':unit.area,'spaceAreasM2':{k:g.area for k,g in gs.items()},'rawSumM2':s,'spaceUnionM2':union.area,'overlapDeductedM2':s-union.area,'courtyardUnionM2':cu.area,'courtyardRatio':cu.area/unit.area,'scope':'同层平面分析投影；非全宅室内空间配比，非三维体积；剩余面积不补造房间'})
    except (ValueError,KeyError,TypeError) as e:T['T05'].append({'kind':'area-configuration','example':'E','status':'not-computed','courtyardRatio':None,'reason':str(e)})
    for r in R:
        if r['type']!='PLAN_POSITION':continue
        p=r['properties'];a=r['source'];b=r['target'];u=p['axisUid']
        try:
            require(compatible([a,b,u]) and rel_supported(r) and supported(u,['axisXY','axisBasis']),'Position references/provenance')
            require(p['inputGeometryVersion']==P[a]['geometryVersion']==P[b]['geometryVersion'],'Position geometry version')
            ca=polygon(a).centroid;cb=polygon(b).centroid;axis=P[u]['axisXY'];norm=math.hypot(*axis);require(norm>0,'Zero axis')
            dx=ca.x-cb.x;dy=ca.y-cb.y;along=(dx*axis[0]+dy*axis[1])/norm;cross=(dx*axis[1]-dy*axis[0])/norm
            T['T05'].append({'kind':'plan-position','source':a,'target':b,'example':'E','status':'computed','alongAxisM':along,'crossAxisM':cross,'cacheConsistent':all(math.isclose(p[k],v,abs_tol=1e-9) for k,v in [('deltaXM',dx),('deltaYM',dy),('alongAxisM',along),('crossAxisM',cross)]),'meaning':p['meaning']})
        except (ValueError,KeyError,TypeError) as e:T['T05'].append({'kind':'plan-position','status':'not-computed','reason':str(e)})
    uses=[x for x in T['T06'] if x.get('example')=='E' and x['state']=='known'];counts=Counter(u for x in uses for u in set(x['uses']))
    return {'items':T,'useSummary':{'knownSpaces':len({x['uid'] for x in uses}),'useAssignments':sum(len(x['uses']) for x in uses),'spacesByUse':dict(counts),'unknownSpaces':len([x for x in T['T06'] if x.get('example')=='E' and x['state']=='unknown']),'notAdditive':True},'engine':'Python + Shapely; inputs are verified Neo4j readback','boundary':'Synthetic external-scope tests only; not empirical validity'}
