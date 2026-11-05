"""Version 1.1: retain approved core, add six-item external synthetic projection."""
import json, hashlib, math
from pathlib import Path
import legacy_compile as legacy
from legacy_compile import DS,PREFIX,MODEL,PACKAGE,BOT,require,dumps
from shapely.geometry import Polygon,LineString
from shapely.ops import substring
ALLOWED_LABELS=legacy.ALLOWED_LABELS|{'ExternalTransition','AnalysisRule'}
ALLOWED_RELS=legacy.ALLOWED_RELS|{'DIRECT_ACCESS_TO','PLAN_POSITION','USES_ANALYSIS_RULE'}

def valid_polygon(p):
    require(isinstance(p,list) and len(p)>=4 and p[0]==p[-1],'Polygon must explicitly close')
    require(all(isinstance(x,list) and len(x)==2 and all(type(v) in (float,int) and math.isfinite(v) for v in x) for x in p),'Finite XY only')
    g=Polygon(p);require(g.is_valid and g.area>0,'Invalid/empty polygon');return g

def compile_model(path):
    model,payload,assignments=legacy.compile_model(path)
    ex=model['externalExtension'];sha=payload['sourceModelSha256'];ns=payload['nodes'];rs=payload['relationships']
    require(ex['id']=='E' and model['modelVersion']=='1.1','Unexpected extension version')
    require(model['review']['firstExample']=='user-approved-limited-synthetic-expression','Approval scope missing')
    ev=ex['source'];sv=ev['sourceVersion'];src=PREFIX+ev['id'];rule=ex['rules']
    require(sv=='E-1.0' and ex['version']=='E-1.0','Unexpected source version')
    for n in ns:
        if n['id']=='R01':n['properties']['reviewStatus']='user-approved-limited-synthetic-expression'
    for r in rs:
        if r['type'] in ('HAS_SOURCE','CLASSIFIED_BY'):r['properties']['reviewStatus']='first-example-approved-synthetic-only'
    def node(id,labels,props,locator,role='synthetic-assignment'):
        require(id.startswith('E-') or id in ('EV02','R02'),'Extension namespace')
        pp={'id':id,'uid':PREFIX+id,'caseId':DS,'datasetId':DS,'exampleId':'E','dataMode':'synthetic','dataVersion':'1.1','recordStatus':role,'sourceModelSha256':sha,'sourceUid':src,'sourceVersion':sv,'sourceLocator':locator,'analysisRuleUid':PREFIX+'R02','analysisRuleVersion':rule['version'],**props}
        ns.append({'id':id,'labels':['KGItem','D03V01',*labels],'properties':pp})
        return pp
    def edge(id,typ,a,b,props,locator):
        pp={'id':id,'uid':PREFIX+id,'caseId':DS,'datasetId':DS,'exampleId':'E','dataMode':'synthetic','sourceModelSha256':sha,'sourceUid':src,'sourceVersion':sv,'locator':locator,'analysisRuleUid':PREFIX+'R02','analysisRuleVersion':rule['version'],'evidenceRole':'synthetic-assignment','semanticOrigin':'research-extension',**props}
        if typ!='HAS_SOURCE':pp['fields']=sorted(k for k in pp if k not in ('fields','sourceModelSha256'))+['source','target','type']
        rs.append({'id':id,'type':typ,'source':PREFIX+a,'target':PREFIX+b,'properties':pp})
    node('EV02',['Source','SyntheticSource'],ev,'/externalExtension/source')
    node('R02',['AnalysisRule'],{'name':rule['name'],'ruleVersion':rule['version'],'definitionJson':dumps(rule),'reviewStatus':'new-details-awaiting-user-review'},'/externalExtension/rules','research-working-rule')
    objects={o['id']:o for o in ex['objects']}; require(len(objects)==len(ex['objects']),'Duplicate extension object')
    for i,o in enumerate(ex['objects']):
        labels=o['labels'];p={k:v for k,v in o.items() if k not in ('labels','polygon','boundaries')}
        require(set(labels)<=ALLOWED_LABELS and not ({'Space','Building'}<=set(labels)),'Invalid object class')
        if 'polygon' in o:
            valid_polygon(o['polygon']);p['polygonJson']=dumps(o['polygon'])
            require(o['geometryComplete'] is True and o['unit']=='m','Geometry scope')
        if 'boundaries' in o:
            bs=o['boundaries'];require(bs and len({b['id'] for b in bs})==len(bs),'Boundary identity')
            for j,b in enumerate(bs):
                require(b['state'] in ('known','unknown') and b['kind'] in ('building','wall','covered-transition','open','unknown'),'Boundary state/kind')
                require((b['state']=='unknown')==(b['kind']=='unknown'),'Unknown mismatch')
                line=LineString(b['polyline']);require(line.is_simple and line.length>0,'Invalid boundary polyline')
                require(valid_polygon(o['polygon']).boundary.covers(line),'Boundary not on declared polygon')
                require(b['polyline'][-1]==bs[(j+1)%len(bs)]['polyline'][0],'Boundary gap')
                intervals=b['solidIntervalsM'];require(isinstance(intervals,list),'Intervals missing')
                last=-1.0
                for a,z in intervals:require(0<=a<z<=line.length and a>=last,'Invalid/overlapping interval');last=z
                if b['kind']=='open':require(b['participantId'] is None and not intervals,'Open side has object/solid')
                if b['kind'] in ('building','wall','covered-transition'):require(b['participantId'] is not None,'Known participant required')
                if b['participantId']:
                    require(b['participantId'] in objects,'Missing boundary participant')
                    expected={'building':'Building','wall':'Wall','covered-transition':'ExternalTransition'}[b['kind']]
                    require(expected in objects[b['participantId']]['labels'],'Wrong boundary participant class')
                    edge('E-BOUNDARY-'+o['id']+'-'+b['id'],'BOUNDARY_PARTICIPANT',o['id'],b['participantId'],{'boundaryId':b['id'],'participantKind':b['kind'],'participantScope':b['basis']},f'/externalExtension/objects/{i}/boundaries/{j}')
            p['boundaryRecordsJson']=dumps(bs)
        if 'Space' in labels:
            require(o['useState'] in ('known','unknown','none','not-applicable'),'Use state')
            require(isinstance(o['useValues'],list) and len(o['useValues'])==len(set(o['useValues'])),'Use values')
            require((o['useState']=='known')==bool(o['useValues']),'Use state contradiction')
            require(o['useScope']=='this-space' and o['useEvidenceRole']=='synthetic-assignment','Use evidence scope')
        bc='Space' if 'Space' in labels else 'Building' if 'Building' in labels else 'Element' if 'Element' in labels else 'Zone'
        p['botClassIri']=BOT+bc
        pp=node(o['id'],labels,p,f'/externalExtension/objects/{i}')
        if o['id']!='E-U01':
            typ='BOT_HAS_SPACE' if 'Space' in labels else 'BOT_HAS_BUILDING' if 'Building' in labels else 'BOT_CONTAINS_ELEMENT'
            edge('E-CONTAINS-'+o['id'],typ,'E-U01',o['id'],{'botPropertyIri':BOT+{'BOT_HAS_SPACE':'hasSpace','BOT_HAS_BUILDING':'hasBuilding','BOT_CONTAINS_ELEMENT':'containsElement'}[typ],'semanticOrigin':'BOT-aligned-synthetic-assertion'},f'/externalExtension/objects/{i}')
    entrances={e['id']:e for e in ex['entrances']};require(len(entrances)==len(ex['entrances']),'Duplicate interface')
    for i,e in enumerate(ex['entrances']):
        c=objects[e['referenceSpaceId']];b=next(b for b in c['boundaries'] if b['id']==e['referenceBoundaryId']);line=LineString(b['polyline'])
        require(e['unit']=='m' and e['referenceGeometryVersion']==c['geometryVersion'],'Entry units/version')
        require(e['correspondence']=='unique-on-reference-line' and 0<=e['startChainageM']<e['endChainageM']<=line.length,'Entry interval')
        endpoints=[e[k] for k in ('fromSpaceId','toSpaceId') if e[k]]
        require(len(set(endpoints))==len(endpoints) and all(x in objects and 'Space' in objects[x]['labels'] for x in endpoints),'Entry endpoint')
        require(e['referenceSpaceId'] in endpoints,'Reference space not an endpoint')
        segment=substring(line,e['startChainageM'],e['endChainageM'])
        for endpoint in endpoints:
            other=objects[endpoint]
            require(all(other[k]==c[k] for k in ('unit','level','coordinateFrame','geometryVersion','floorZM')),'Entry side reference mismatch')
            require(e['level']==other['level'] and valid_polygon(other['polygon']).boundary.covers(segment),'Entry segment not on both declared sides')
        if b['kind'] in ('building','wall'):
            require(all(min(z,e['endChainageM'])<=max(a,e['startChainageM']) for a,z in b['solidIntervalsM']),'Opening counted as solid')
        if e['hostId']:require(e['hostId']==b['participantId'] and 'Wall' in objects[e['hostId']]['labels'],'Host mismatch')
        require((e['toSpaceId'] is None)==(e['farSideState']=='unknown'),'Other-side state')
        p={k:v for k,v in e.items() if k not in ('fromSpaceId','toSpaceId','hostId')}
        p.update(fromSpaceUid=PREFIX+e['fromSpaceId'],toSpaceUid=PREFIX+e['toSpaceId'] if e['toSpaceId'] else '',hostUid=PREFIX+e['hostId'] if e['hostId'] else '',referenceSpaceUid=PREFIX+e['referenceSpaceId'],referenceLengthM=float(line.length),referencePolylineJson=dumps(b['polyline']),botClassIri=BOT+'Interface')
        node(e['id'],['Interface','EntranceInterface'],p,f'/externalExtension/entrances/{i}')
        for role,target in [('side-a',e['fromSpaceId']),('side-b',e['toSpaceId']),('opening-host',e['hostId'])]:
            if target:edge(e['id']+'-'+role,'INTERFACE_OF',e['id'],target,{'role':role,'botPropertyIri':BOT+'interfaceOf','semanticOrigin':'BOT-aligned-with-research-role'},f'/externalExtension/entrances/{i}')
    seen=set()
    for i,a in enumerate(ex['access']):
        require(a['from']!=a['to'] and a['via'] in entrances,'Bad access identity')
        en=entrances[a['via']];require({a['from'],a['to']}=={en['fromSpaceId'],en['toSpaceId']},'Access via endpoint mismatch')
        require(a['state']=='passable-asserted' and a['contextId'] and a['actor'] and a['doorState'] and a['obstacleState'] and a['observationTime'],'Missing passage context')
        require(a['evidenceRole']=='synthetic-explicit-passage-assertion','Passage not explicitly supported')
        unit=objects['E-U01']
        require(a['contextId']==unit['passageContextId'] and a['actor']==unit['passageActor'] and a['observationTime']==unit['passageSnapshot'],'Inconsistent passage context')
        key=(a['from'],a['to'],a['via'],a['contextId']);require(key not in seen,'Duplicate passage');seen.add(key)
        edge(a['id'],'DIRECT_ACCESS_TO',a['from'],a['to'],{**{k:v for k,v in a.items() if k not in ('from','to','via')},'viaUid':PREFIX+a['via'],'analysisRuleUid':PREFIX+'R02','analysisRuleVersion':rule['version'],'networkScope':'partial-external-known-subgraph'},f'/externalExtension/access/{i}')
    for i,a in enumerate(ex['comparisons']):
        s=objects[a['subject']];r=objects[a['reference']];u=objects[a['axisFrom']]
        require(all(s[k]==r[k]==u[k] for k in ('unit','level','coordinateFrame','geometryBasis')),'Incompatible position comparison')
        ca=valid_polygon(s['polygon']).centroid;cb=valid_polygon(r['polygon']).centroid;axis=u['axisXY'];norm=math.hypot(*axis);require(norm>0,'Zero axis')
        dx=ca.x-cb.x;dy=ca.y-cb.y
        edge(a['id'],'PLAN_POSITION',a['subject'],a['reference'],{'axisUid':PREFIX+a['axisFrom'],'deltaXM':dx,'deltaYM':dy,'alongAxisM':(dx*axis[0]+dy*axis[1])/norm,'crossAxisM':(dx*axis[1]-dy*axis[0])/norm,'meaning':a['meaning'],'inputGeometryVersion':s['geometryVersion'],'analysisRuleUid':PREFIX+'R02','analysisRuleVersion':rule['version'],'recordStatus':'derived-synthetic','evidenceRole':'derived-not-independent-evidence'},f'/externalExtension/comparisons/{i}')
    edge('E-USES-R02','USES_ANALYSIS_RULE','E-U01','R02',{'analysisItems':['D03-T%02d'%i for i in range(1,7)]},'/externalExtension/rules')
    for n in list(ns):
        p=n['properties']
        if p.get('exampleId')!='E' or n['id']=='EV02':continue
        edge('SRC-'+n['id'],'HAS_SOURCE',n['id'],'EV02',{'fields':sorted(k for k in p if k not in ('sourceModelSha256','uid','caseId','datasetId')),'locatorKind':'JSON-pointer','sourceVersion':sv,'reviewStatus':'new-details-awaiting-user-review'},p['sourceLocator'])
    ids=[n['properties']['uid'] for n in ns];rids=[r['properties']['uid'] for r in rs]
    require(len(ids)==len(set(ids)) and len(rids)==len(set(rids)),'Duplicate graph identity')
    require(all(set(n['labels'])<=ALLOWED_LABELS for n in ns),'Unexpected labels')
    require(all(r['type'] in ALLOWED_RELS and r['source'] in ids and r['target'] in ids for r in rs),'Invalid relation')
    for row in ns+rs:
        for k,v in row['properties'].items():
            require(type(v) in (str,bool,int,float,list),'Non-native property '+row['id']+'.'+k)
            if isinstance(v,float):require(math.isfinite(v),'Nonfinite scalar')
            if isinstance(v,list):require(all(type(x) in (str,bool,int,float) and (type(x)!=float or math.isfinite(x)) for x in v) and len({type(x) for x in v})<=1,'Invalid property list')
    payload['allowedRelationshipTypes']=sorted({r['type'] for r in rs})
    return model,payload,assignments

def query_params(payload):return legacy.query_params(payload)
def validate_payload(payload,path,expected_sha):
    require(hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected_sha,'Source changed')
    require(payload==compile_model(path)[1],'Payload differs from recompiled source')
    return True

def queries():
    q=legacy.queries()
    for key in ('Q01','Q02','Q03','Q05','Q06'):
        q[key]=q[key].replace('MATCH (u:DwellingUnit {caseId:$caseId})-[:BOT_HAS_SPACE]->(c:Courtyard)','MATCH (u:DwellingUnit {caseId:$caseId})-[:BOT_HAS_SPACE]->(c:Courtyard) WHERE u.exampleId IN [\'A\',\'B\',\'C\',\'D\']')
        q[key]=q[key].replace('MATCH (c:Courtyard {caseId:$caseId})','MATCH (c:Courtyard {caseId:$caseId}) WHERE c.exampleId IN [\'A\',\'B\',\'C\',\'D\']')
        q[key]=q[key].replace('MATCH (i:EntranceInterface {caseId:$caseId})','MATCH (i:EntranceInterface {caseId:$caseId}) WHERE i.exampleId IN [\'A\',\'B\',\'C\',\'D\']')
    q['Q09']='MATCH (n:D03V01:Space {exampleId:"E"}) RETURN n.uid AS uid,properties(n) AS inputs ORDER BY uid'
    q['Q10']='MATCH (n:D03V01:Courtyard {exampleId:"E"}) OPTIONAL MATCH (n)-[r:BOUNDARY_PARTICIPANT]->(p) RETURN n.uid AS uid,n.boundaryRecordsJson AS segments,collect({uid:r.uid,participant:p.uid,properties:properties(r)}) AS participants ORDER BY uid'
    q['Q11']='MATCH (i:D03V01:EntranceInterface {exampleId:"E"}) OPTIONAL MATCH (i)-[r:INTERFACE_OF]->(p) RETURN i.uid AS uid,properties(i) AS inputs,collect({role:r.role,participant:p.uid}) AS roles ORDER BY uid'
    q['Q12']='MATCH (a:D03V01)-[r:DIRECT_ACCESS_TO {exampleId:"E"}]->(b:D03V01) RETURN a.uid AS source,b.uid AS target,properties(r) AS inputs ORDER BY r.uid'
    q['Q13']='MATCH (n:D03V01 {exampleId:"E"}) WHERE n.polygonJson IS NOT NULL RETURN n.uid AS uid,labels(n) AS labels,n.polygonJson AS polygon,n.level AS level,n.coordinateFrame AS frame,n.geometryBasis AS basis,n.unit AS unit,n.geometryVersion AS version ORDER BY uid'
    q['Q14']='MATCH (s:D03V01:Space {exampleId:"E"}) OPTIONAL MATCH (s)-[r:HAS_SOURCE]->(e:Source) RETURN s.uid AS uid,s.useState AS state,s.useValues AS uses,s.useContext AS context,s.useScope AS scope,e.uid AS source,r.locator AS locator,r.fields AS fields ORDER BY uid'
    q['Q15']='MATCH (a:D03V01)-[r:PLAN_POSITION]->(b:D03V01) RETURN a.uid AS subject,b.uid AS reference,properties(r) AS cached ORDER BY r.uid'
    return q
