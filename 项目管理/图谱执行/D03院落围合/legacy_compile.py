"""Compile the JSON maintenance source into guarded LPG and read-only queries."""
import copy, hashlib, json, math, re
from pathlib import Path
from mcp_client import save
PREFIX='D03V01:'; DS='D03V01'
PACKAGE='研究成果/〔合成试例〕D03院落围合图谱试例'
MODEL=PACKAGE+'/案例模型.json'
BOT='https://w3id.org/bot#'
KINDS=['building','wall','open','unknown']
ALLOWED_LABELS={'KGItem','D03V01','Zone','DwellingUnit','Space','Courtyard','Building','Element','Wall','Interface','EntranceInterface','Source','SyntheticSource','ClassificationScheme'}
ALLOWED_RELS={'BOT_HAS_SPACE','BOT_HAS_BUILDING','BOT_CONTAINS_ELEMENT','BOUNDARY_PARTICIPANT','INTERFACE_OF','HAS_SOURCE','CLASSIFIED_BY'}
INPUT_FIELDS=['boundaryIds','boundaryKinds','boundaryStates','shapeCode','boundaryParticipantUids','boundaryLocators','geometryVersion']

def require(condition,message='Invalid model or payload'):
    if not condition: raise ValueError(message)

def dumps(v): return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def patterns(scheme):
    out=[]
    for rule in scheme['rules']:
        p=rule['pattern']; variants=[p]
        if scheme['allowReflection']: variants.append(list(reversed(p)))
        keys=set()
        for v in variants:
            for i in range(len(v)) if scheme['allowRotation'] else [0]: keys.add('|'.join(v[i:]+v[:i]))
        out.extend((k,rule['code']) for k in sorted(keys))
    return out

_DEFAULT_IDS=object()
def classify(kinds,states,scheme,valid=True,shape='rectangular-reference',ids=_DEFAULT_IDS):
    if ids is _DEFAULT_IDS: ids=scheme['sideIds']
    arrays=[kinds,states,ids]
    if (valid is not True or not isinstance(shape,str) or not shape
        or any(not isinstance(v,list) or not v or any(not isinstance(x,str) or not x for x in v) for v in arrays)
        or not len(kinds)==len(states)==len(ids) or len(ids)!=len(set(ids))
        or any(k not in KINDS for k in kinds) or any(s not in ['known','unknown'] for s in states)
        or any((k=='unknown')!=(s=='unknown') for k,s in zip(kinds,states))): return 'invalid-input',[]
    if shape!=scheme['applicableShape'] or len(ids)!=len(scheme['sideIds']): return 'out-of-scope',[]
    if ids!=scheme['sideIds']: return 'invalid-input',[]
    if 'unknown' in states: return 'unknown',[]
    matches=sorted(set(code for key,code in patterns(scheme) if key=='|'.join(kinds)))
    return ('known-unmatched' if not matches else 'rule-conflict' if len(matches)>1 else 'candidate-assigned'),matches

# The same expression is used by persisted graph queries and parameter-only tests.
CORE='''WITH c,scheme,inputValid,cachedType,cachedStatus,
 CASE WHEN valueType(c.boundaryKinds) STARTS WITH 'LIST<STRING' THEN c.boundaryKinds ELSE [] END AS kinds,
 CASE WHEN valueType(c.boundaryStates) STARTS WITH 'LIST<STRING' THEN c.boundaryStates ELSE [] END AS states,
 CASE WHEN valueType(c.boundaryIds) STARTS WITH 'LIST<STRING' THEN c.boundaryIds ELSE [] END AS ids,
 CASE WHEN valueType(scheme.sideIds) STARTS WITH 'LIST<STRING' THEN scheme.sideIds ELSE [] END AS sideIds,
 CASE WHEN valueType(scheme.patternKeys) STARTS WITH 'LIST<STRING' THEN scheme.patternKeys ELSE [] END AS pkeys,
 CASE WHEN valueType(scheme.patternCodes) STARTS WITH 'LIST<STRING' THEN scheme.patternCodes ELSE [] END AS pcodes
WITH *,reduce(s='',kind IN kinds | s + CASE WHEN s='' THEN '' ELSE '|' END + kind) AS patternKey
WITH *,reduce(found=[],i IN range(0,size(pkeys)-1) |
 CASE WHEN pkeys[i]=patternKey AND NOT pcodes[i] IN found THEN found+[pcodes[i]] ELSE found END) AS matches
WITH c,scheme,cachedType,cachedStatus,patternKey,matches,
 CASE WHEN NOT coalesce(inputValid=true,false)
           OR size(kinds)=0 OR size(states)<>size(kinds) OR size(ids)<>size(kinds)
           OR size(sideIds)=0 OR size(pkeys)=0 OR size(pkeys)<>size(pcodes)
           OR c.shapeCode IS NULL OR c.shapeCode='' OR valueType(c.shapeCode)<>'STRING NOT NULL'
           OR scheme.applicableShape IS NULL OR scheme.applicableShape=''
           OR any(k IN kinds WHERE k IS NULL OR NOT k IN ['building','wall','open','unknown'])
           OR any(s IN states WHERE s IS NULL OR NOT s IN ['known','unknown'])
           OR any(i IN range(0,size(kinds)-1) WHERE (kinds[i]='unknown')<>(states[i]='unknown'))
           OR any(id IN ids WHERE id IS NULL OR id='')
           OR size(reduce(u=[],id IN ids | CASE WHEN id IN u THEN u ELSE u+[id] END))<>size(ids) THEN 'invalid-input'
      WHEN c.shapeCode<>scheme.applicableShape OR size(ids)<>size(sideIds) THEN 'out-of-scope'
      WHEN ids<>sideIds THEN 'invalid-input'
      WHEN 'unknown' IN states THEN 'unknown'
      WHEN size(matches)=0 THEN 'known-unmatched'
      WHEN size(matches)>1 THEN 'rule-conflict'
      ELSE 'candidate-assigned' END AS resultStatus
'''
RETURN_CLASS="""WITH *,CASE WHEN resultStatus='candidate-assigned' THEN matches[0] ELSE '' END AS candidateType
RETURN c.uid AS courtyard,c.exampleId AS example,patternKey,resultStatus,candidateType,
 CASE WHEN resultStatus IN ['candidate-assigned','known-unmatched','rule-conflict'] THEN matches ELSE [] END AS matches,
 scheme.ruleVersion AS ruleVersion,cachedType,cachedStatus,
 coalesce(resultStatus=cachedStatus AND candidateType=cachedType,false) AS cacheConsistent,
 c.boundaryIds AS boundaryIds,c.boundaryKinds AS boundaryKinds,c.boundaryStates AS boundaryStates,
 c.boundaryParticipantUids AS participants,c.boundaryLocators AS sourceLocators,
 c.geometryVersion AS geometryVersion,c.dataVersion AS inputModelVersion ORDER BY example"""
DB_PREFIX='''MATCH (c:Courtyard {caseId:$caseId})
OPTIONAL MATCH (c)-[ass:CLASSIFIED_BY]->(sc:ClassificationScheme)
WITH c,[a IN collect({edge:ass,scheme:sc}) WHERE a.edge IS NOT NULL] AS assignments
WITH c,assignments,assignments[0].edge AS assignment,assignments[0].scheme AS scheme
OPTIONAL MATCH (c)-[hs:HAS_SOURCE]->(src:Source)
WITH c,assignments,assignment,scheme,[s IN collect({edge:hs,src:src}) WHERE s.edge IS NOT NULL] AS sources
OPTIONAL MATCH (c)-[bp:BOUNDARY_PARTICIPANT]->(participant)
WITH c,assignments,assignment,scheme,sources,[p IN collect({edge:bp,node:participant}) WHERE p.edge IS NOT NULL] AS participants
WITH c,scheme,assignment.candidateType AS cachedType,assignment.status AS cachedStatus,
 size(assignments)=1 AND size(sources)=1 AND sources[0].src.uid=assignment.sourceUid
 AND c.sourceModelSha256=$modelSha AND properties(scheme)=$expectedRule
 AND assignment.inputFields=__INPUT_FIELDS__
 AND assignment.sourceRelationUid=sources[0].edge.uid
 AND sources[0].src.sourceVersion=assignment.inputVersion
 AND sources[0].edge.sourceVersion=assignment.inputVersion
 AND c.dataVersion=assignment.inputModelVersion
 AND c.geometryVersion=assignment.inputBoundaryVersion
 AND sources[0].edge.locator=c.sourceLocator
 AND all(k IN __INPUT_FIELDS__ WHERE k IN sources[0].edge.fields)
 AND assignment.ruleVersion=scheme.ruleVersion
 AND assignment.ruleDefinitionSha256=scheme.definitionSha256
 AND EXISTS { MATCH (u:DwellingUnit)-[:BOT_HAS_SPACE]->(c) WHERE u.uid=c.unitUid AND u.exampleId=c.exampleId AND u.caseId=c.caseId }
 AND size(c.boundaryParticipantUids)=size(c.boundaryIds) AND size(c.boundaryLocators)=size(c.boundaryIds)
 AND all(i IN range(0,size(c.boundaryIds)-1) WHERE
   CASE WHEN c.boundaryKinds[i] IN ['building','wall'] THEN
     size([p IN participants WHERE p.edge.boundaryId=c.boundaryIds[i]])=1
     AND all(p IN [p IN participants WHERE p.edge.boundaryId=c.boundaryIds[i]] WHERE
       p.edge.sourceUid=assignment.sourceUid AND p.edge.sourceVersion=assignment.inputVersion
       AND p.edge.locator=c.boundaryLocators[i]
       AND p.node.uid=c.boundaryParticipantUids[i] AND p.node.exampleId=c.exampleId AND p.node.caseId=c.caseId
       AND EXISTS { MATCH (u:DwellingUnit)-[owned]->(pn) WHERE u.uid=c.unitUid AND pn=p.node AND type(owned) IN ['BOT_HAS_BUILDING','BOT_CONTAINS_ELEMENT'] }
       AND p.edge.participantKind=c.boundaryKinds[i]
       AND ((c.boundaryKinds[i]='building' AND 'Building' IN labels(p.node)) OR (c.boundaryKinds[i]='wall' AND 'Wall' IN labels(p.node))))
   ELSE size([p IN participants WHERE p.edge.boundaryId=c.boundaryIds[i]])=0 AND c.boundaryParticipantUids[i]='' END)
 AND all(p IN participants WHERE p.edge IS NULL OR p.edge.boundaryId IN c.boundaryIds) AS inputValid
'''.replace('__INPUT_FIELDS__',dumps(INPUT_FIELDS))
IMPORT='''WITH $nodes AS ns,$relationships AS rs,$datasetId AS ds,$prefix AS prefix
WHERE ds='D03V01' AND prefix='D03V01:' AND size(ns)>0 AND size(rs)>0
 AND size(reduce(ids=[],n IN ns | CASE WHEN n.properties.uid IN ids THEN ids ELSE ids+[n.properties.uid] END))=size(ns)
 AND size(reduce(ids=[],r IN rs | CASE WHEN r.properties.uid IN ids THEN ids ELSE ids+[r.properties.uid] END))=size(rs)
 AND all(n IN ns WHERE n.properties.uid STARTS WITH prefix AND n.properties.caseId=ds AND n.properties.datasetId=ds
     AND 'KGItem' IN n.labels AND 'D03V01' IN n.labels AND all(l IN n.labels WHERE l IN __LABELS__)
     AND n.properties.sourceModelSha256=$sourceModelSha256)
 AND all(r IN rs WHERE r.properties.uid STARTS WITH prefix AND r.properties.caseId=ds AND r.properties.datasetId=ds
     AND r.properties.sourceModelSha256=$sourceModelSha256
     AND r.type IN __RELS__
     AND size([n IN ns WHERE n.properties.uid=r.source])=1
     AND size([n IN ns WHERE n.properties.uid=r.target])=1)
OPTIONAL MATCH (existing)
WHERE existing.datasetId=ds OR existing.caseId=ds OR existing.uid STARTS WITH prefix
WITH ns,rs,ds,prefix,count(existing) AS collisions
WHERE collisions=0
OPTIONAL MATCH ()-[existingRel]->()
WHERE existingRel.datasetId=ds OR existingRel.caseId=ds OR existingRel.uid STARTS WITH prefix
WITH ns,rs,ds,prefix,count(existingRel) AS collisions
WHERE collisions=0
CALL { WITH ns UNWIND ns AS row CREATE (n:$(row.labels)) SET n=row.properties RETURN count(n) AS nodesCreated }
CALL { WITH rs,ds UNWIND rs AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target})
 WHERE a.caseId=ds AND b.caseId=ds CREATE (a)-[r:$(row.type)]->(b) SET r=row.properties RETURN count(r) AS relationshipsCreated }
RETURN nodesCreated,relationshipsCreated
'''.replace('__LABELS__',dumps(sorted(ALLOWED_LABELS))).replace('__RELS__',dumps(sorted(ALLOWED_RELS)))

def validate_payload(payload,path,expected_sha):
    """Compile from frozen source; never trust payload self-declarations."""
    require(hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected_sha,'Source changed since review')
    _,expected,_=compile_model(path)
    require(payload==expected,'Payload differs from exact compiled source')
    require(payload['datasetId']==DS and payload['prefix']==PREFIX,'Wrong namespace')
    for n in payload['nodes']: require(set(n['labels'])<=ALLOWED_LABELS,'Unexpected label')
    for r in payload['relationships']: require(r['type'] in ALLOWED_RELS,'Unexpected relationship')
    return True

def query_params(payload):
    return {'caseId':DS,'modelSha':payload['sourceModelSha256'],'expectedRule':next(n['properties'] for n in payload['nodes'] if n['id']=='R01')}

def compile_model(path):
    path=Path(path); raw=path.read_bytes(); model=json.loads(raw)
    sha=hashlib.sha256(raw).hexdigest(); nodes=[];rels=[]; scheme=model['classificationScheme']; pairs=patterns(scheme)
    require(model['datasetId']==DS and model['status']=='synthetic-candidate-awaiting-user-review','Wrong model scope/status')
    sv=model['source']['sourceVersion'];mv=model['modelVersion']
    require(all(isinstance(v,str) and v for v in [sv,mv,scheme['version']]),'Missing versions')
    rule_hash=hashlib.sha256(dumps(scheme).encode()).hexdigest()
    def node(id,labels,p,example=None):
        common={'uid':PREFIX+id,'id':id,'caseId':DS,'datasetId':DS,'dataMode':'synthetic','recordStatus':'synthetic-assignment','sourceModelSha256':sha,'dataVersion':model['modelVersion']}
        if example: common['exampleId']=example
        props={**common,**p};nodes.append({'id':id,'labels':['KGItem','D03V01',*labels],'properties':props});return props
    def edge(id,type,source,target,props=None):
        p={'uid':PREFIX+id,'id':id,'caseId':DS,'datasetId':DS,'dataMode':'synthetic','sourceModelSha256':sha,'semanticOrigin':'research-extension',**(props or {})}
        if 'sourceVersion' in p:p['sourceVersion']=sv
        rels.append({'id':id,'type':type,'source':PREFIX+source,'target':PREFIX+target,'properties':p});return p
    def source(id,p,pointer):
        excluded={'uid','id','caseId','datasetId','dataMode','recordStatus','sourceModelSha256','exampleId'}
        fields=sorted(set(p)-excluded)
        edge('SRC-'+id,'HAS_SOURCE',id,'EV01',{'fields':fields,'locator':pointer,'locatorKind':'JSON-pointer','sourceVersion':sv,'evidenceRole':'synthetic-assignment','reviewStatus':'user-review-pending','projection':'字段由该JSON对象及其boundary数组投影；不是独立外部实证'})
    node('EV01',['Source','SyntheticSource'],model['source'])
    node('R01',['ClassificationScheme'],{'name':scheme['name'],'recordStatus':'research-candidate','ruleVersion':scheme['version'],'schemeMode':scheme['mode'],'applicableShape':scheme['applicableShape'],'sideIds':scheme['sideIds'],'patternKeys':[x[0] for x in pairs],'patternCodes':[x[1] for x in pairs],'typeCodes':[r['code'] for r in scheme['rules']],'typeNames':[r['name'] for r in scheme['rules']],'definitionJson':dumps(scheme),'definitionSha256':rule_hash,'sourceLocator':'/classificationScheme','reviewStatus':'user-review-pending'})
    assignments=[]
    for ei,ex in enumerate(model['examples']):
        x=ex['id'];base='/examples/'+str(ei);u=ex['unit'];c=ex['courtyard'];wall=ex['wall'];ent=ex['entrance'];bs=ex['boundary']
        require(bs and len({b['id'] for b in bs})==len(bs),'Duplicate or empty boundaries')
        require(all(b['state'] in ('known','unknown') and ((b['kind']=='unknown')==(b['state']=='unknown')) for b in bs),'Inconsistent state/kind')
        require(all(bs[i]['endXY']==bs[(i+1)%len(bs)]['startXY'] for i in range(len(bs))),'Nonclosing reference boundary')
        local_ids={a['id'] for a in ex['buildings']}|{wall['id']}
        require(all((b['participantId'] in local_ids) if b['kind'] in ['building','wall'] else b['participantId'] is None for b in bs),'Bad participant identity')
        up=node(u['id'],['Zone','DwellingUnit'],{**u,'botClassIri':BOT+'Zone','geometryState':'synthetic-declared-containment; geometry not computed'},x);source(u['id'],up,base+'/unit')
        lengths=[math.dist(b['startXY'],b['endXY']) for b in bs]
        cp=node(c['id'],['Zone','Space','Courtyard'],{**c,'botClassIri':BOT+'Space','unitUid':PREFIX+u['id'],'sourceLocator':base,'identityBasis':'人工合成声明Space身份；不是从二维闭合或参与边推定','boundaryIds':[b['id'] for b in bs],'boundaryKinds':[b['kind'] for b in bs],'boundaryStates':[b['state'] for b in bs],'boundaryParticipantUids':[PREFIX+b['participantId'] if b['participantId'] else '' for b in bs],'boundaryLocators':[base+'/boundary/'+str(j) for j in range(len(bs))],'boundaryLengthsM':lengths,'boundarySegmentsJson':dumps(bs),'analysisItems':['D03-T01','D03-T02']},x);source(c['id'],cp,base)
        edge(x+'-CONTAINS-C','BOT_HAS_SPACE',u['id'],c['id'],{'botPropertyIri':BOT+'hasSpace','semanticOrigin':'BOT-aligned-synthetic-assertion','sourceUid':PREFIX+'EV01','sourceVersion':'1.0','locator':base,'fields':['source','target','type']})
        for bi,b in enumerate(ex['buildings']):
            bp=node(b['id'],['Zone','Building'],{**b,'botClassIri':BOT+'Building'},x);source(b['id'],bp,base+'/buildings/'+str(bi))
            edge(x+'-CONTAINS-'+b['id'],'BOT_HAS_BUILDING',u['id'],b['id'],{'botPropertyIri':BOT+'hasBuilding','semanticOrigin':'BOT-aligned-synthetic-assertion','sourceUid':PREFIX+'EV01','sourceVersion':'1.0','locator':base,'fields':['source','target','type']})
        wp=node(wall['id'],['Element','Wall'],{**wall,'botClassIri':BOT+'Element'},x);source(wall['id'],wp,base+'/wall')
        edge(x+'-CONTAINS-W','BOT_CONTAINS_ELEMENT',u['id'],wall['id'],{'botPropertyIri':BOT+'containsElement','semanticOrigin':'BOT-aligned-synthetic-assertion','sourceUid':PREFIX+'EV01','sourceVersion':'1.0','locator':base,'fields':['source','target','type'],'interpretation':'整体分析范围包含院墙；并非院墙属于院落空间的构件组成'})
        for j,b in enumerate(bs):
            if b['participantId']:
                edge(x+'-BOUNDARY-'+b['id'],'BOUNDARY_PARTICIPANT',c['id'],b['participantId'],{'boundaryId':b['id'],'participantKind':b['kind'],'participantScope':b['participantScope'],'sourceUid':PREFIX+'EV01','sourceVersion':'1.0','locator':base+'/boundary/'+str(j),'fields':['source','target','type','boundaryId','participantKind','participantScope'],'evidenceRole':'synthetic-assignment','mappingBoundary':'二维/语义参与，不断言BOT邻接、实体接触或承重'})
        idx=next(i for i,b in enumerate(bs) if b['id']==ent['referenceBoundaryId']);L=lengths[idx]
        require(0<=ent['startChainageM']<ent['endChainageM']<=L and L>0,'Invalid entrance interval')
        require(ent['hostId']==bs[idx]['participantId']==wall['id'],'Entrance host mismatch')
        ip=node(ent['id'],['Interface','EntranceInterface'],{**{k:v for k,v in ent.items() if k!='hostId'},'expectedHostUid':PREFIX+ent['hostId'],'expectedCourtyardUid':PREFIX+c['id'],'sourceLocator':base,'inputSourceVersion':sv,'referenceLengthM':L,'referenceGeometryVersion':c['geometryVersion'],'botClassIri':BOT+'Interface','analysisItems':['D03-T03']},x);source(ent['id'],ip,base)
        for role,target in [('courtyard-side',c['id']),('opening-host',ent['hostId'])]:
            edge(x+'-ENTRY-'+role,'INTERFACE_OF',ent['id'],target,{'role':role,'botPropertyIri':BOT+'interfaceOf','semanticOrigin':'BOT-aligned-with-research-role','sourceUid':PREFIX+'EV01','sourceVersion':'1.0','locator':base+'/entrance','fields':['source','target','type','role']})
        status,matches=classify(cp['boundaryKinds'],cp['boundaryStates'],scheme,shape=c['shapeCode'],ids=cp['boundaryIds'])
        require(status!='invalid-input','Invalid classification inputs')
        assignment={'status':status,'candidateType':matches[0] if status=='candidate-assigned' else '', 'ruleVersion':scheme['version'],'ruleDefinitionSha256':rule_hash,'inputVersion':sv,'inputModelVersion':mv,'sourceUid':PREFIX+'EV01','sourceRelationUid':PREFIX+'SRC-'+c['id'],'inputFields':INPUT_FIELDS,'inputBoundaryVersion':c['geometryVersion'],'analysisItems':['D06-T01','D06-T03'],'recordStatus':'derived-candidate','evidenceRole':'derived-not-independent-evidence','reviewStatus':'user-review-pending'}
        edge(x+'-CLASS','CLASSIFIED_BY',c['id'],'R01',assignment);assignments.append({'example':x,**assignment})
    ids=[n['properties']['uid'] for n in nodes];rids=[r['properties']['uid'] for r in rels]
    require(len(ids)==len(set(ids)) and len(rids)==len(set(rids)),'Duplicate identifiers')
    require(all(r['source'] in ids and r['target'] in ids for r in rels),'Missing endpoint')
    for row in nodes+rels:
        for k,v in row['properties'].items():
            require(isinstance(v,(str,bool,int,float,list)),str((row['id'],k,type(v))))
            if isinstance(v,list): require(not v or len({type(t) for t in v})==1,'Mixed property array')
    payload={'nodes':nodes,'relationships':rels,'datasetId':DS,'prefix':PREFIX,'sourceModelSha256':sha,'allowedRelationshipTypes':sorted({r['type'] for r in rels})}
    return model,payload,assignments

Q3='''MATCH (i:EntranceInterface {caseId:$caseId})
OPTIONAL MATCH (i)-[participation:INTERFACE_OF]->(participant)
WITH i,[p IN collect({edge:participation,node:participant}) WHERE p.edge IS NOT NULL] AS allParts
WITH i,allParts,[p IN allParts WHERE p.edge.role='courtyard-side'] AS courts,[p IN allParts WHERE p.edge.role='opening-host'] AS hosts
OPTIONAL MATCH (i)-[s:HAS_SOURCE]->(source:Source)
WITH i,allParts,courts,hosts,[p IN collect({edge:s,node:source}) WHERE p.edge IS NOT NULL] AS sources
WITH i,allParts,courts,hosts,sources,courts[0].node AS c,hosts[0].node AS host,courts[0].edge AS a,hosts[0].edge AS h,sources[0].edge AS hs,sources[0].node AS src
WITH *,[k IN range(0,size(c.boundaryIds)-1) WHERE c.boundaryIds[k]=i.referenceBoundaryId] AS indices
WITH i,c,host,
 coalesce(size(allParts)=2 AND size(courts)=1 AND size(hosts)=1 AND size(sources)=1
 AND 'Courtyard' IN labels(c) AND 'Wall' IN labels(host)
 AND i.exampleId=c.exampleId AND i.exampleId=host.exampleId AND i.caseId=c.caseId AND i.caseId=host.caseId
 AND i.expectedCourtyardUid=c.uid AND i.expectedHostUid=host.uid
 AND a.sourceUid=src.uid AND h.sourceUid=src.uid AND hs.locator=i.sourceLocator
 AND a.locator=i.sourceLocator+'/entrance' AND h.locator=i.sourceLocator+'/entrance'
 AND size(indices)=1 AND i.unit='m' AND c.unit='m' AND i.referenceLengthM>0
 AND i.referenceLengthM=c.boundaryLengthsM[indices[0]]
 AND i.referenceGeometryVersion=c.geometryVersion
 AND i.startChainageM>=0 AND i.endChainageM>i.startChainageM AND i.endChainageM<=i.referenceLengthM
 AND hs.sourceVersion=i.inputSourceVersion AND src.sourceVersion=i.inputSourceVersion
 AND a.sourceVersion=i.inputSourceVersion AND h.sourceVersion=i.inputSourceVersion
 AND all(f IN ['startChainageM','endChainageM','referenceLengthM','referenceBoundaryId','referenceGeometryVersion'] WHERE f IN hs.fields)
 AND EXISTS { MATCH (c)-[bp:BOUNDARY_PARTICIPANT]->(host) WHERE bp.boundaryId=i.referenceBoundaryId },false) AS valid
RETURN i.uid AS entrance,i.exampleId AS example,c.uid AS courtyard,host.uid AS host,i.referenceBoundaryId AS boundary,
 i.startChainageM AS startM,i.endChainageM AS endM,i.referenceLengthM AS lengthM,valid,
 CASE WHEN valid THEN (i.startChainageM+i.endChainageM)/2.0/i.referenceLengthM ELSE null END AS relativePosition,
 i.farSideStatus AS farSideStatus,i.passabilityStatus AS passabilityStatus ORDER BY example'''

def queries():
    q={}
    q['Q01']='''MATCH (u:DwellingUnit {caseId:$caseId})-[:BOT_HAS_SPACE]->(c:Courtyard)
OPTIONAL MATCH (u)-[:BOT_HAS_BUILDING]->(b:Building)
RETURN u.exampleId AS example,u.uid AS unit,c.uid AS courtyard,collect(b.uid) AS buildings,c.geometryState AS geometryState ORDER BY example'''
    q['Q02']='''MATCH (c:Courtyard {caseId:$caseId}) UNWIND range(0,size(c.boundaryIds)-1) AS i
OPTIONAL MATCH (c)-[p:BOUNDARY_PARTICIPANT]->(n) WHERE p.boundaryId=c.boundaryIds[i]
RETURN c.exampleId AS example,c.uid AS courtyard,c.boundaryIds[i] AS side,c.boundaryStates[i] AS state,c.boundaryKinds[i] AS kind,n.uid AS participant,p.participantScope AS participantScope ORDER BY example,i'''
    q['Q03']=Q3
    q['Q04']='''MATCH (n:D03V01)-[s:HAS_SOURCE]->(e:Source)
RETURN n.uid AS object,e.uid AS source,s.fields AS fields,s.locator AS locator,s.locatorKind AS locatorKind,s.sourceVersion AS expectedVersion,e.sourceVersion AS actualVersion,s.evidenceRole AS evidenceRole ORDER BY object'''
    q['Q05']=DB_PREFIX+CORE+RETURN_CLASS
    q['Q06']='CALL { '+q['Q05']+' } RETURN collect({example:example,courtyard:courtyard,pattern:patternKey,status:resultStatus,candidateType:candidateType,ruleVersion:ruleVersion,cacheConsistent:cacheConsistent,boundaryIds:boundaryIds,boundaryKinds:boundaryKinds,boundaryStates:boundaryStates,participants:participants,sourceLocators:sourceLocators,geometryVersion:geometryVersion,inputModelVersion:inputModelVersion}) AS d06Comparison'
    q['Q07']='''MATCH (a)-[r]->(b) WHERE coalesce(a.caseId=$caseId,false) <> coalesce(b.caseId=$caseId,false) RETURN count(r) AS crossDatasetEdges'''
    q['Q08']='''MATCH (n:D03V01) WITH labels(n) AS labels,count(*) AS n RETURN labels,n ORDER BY labels'''
    return q

if __name__=='__main__':
    import sys
    d=Path(sys.argv[1]); model,payload,assignments=compile_model(d/'candidates'/MODEL)
    out=d/'generated';out.mkdir(exist_ok=True)
    save(out/'payload.json',payload);save(out/'assignments.json',assignments);save(out/'queries.json',queries())
    save(out/'query-params.json',query_params(payload))
    (out/'import.cypher').write_text(IMPORT)
    (out/'审核查询.cypher').write_text('// 完整参数见查询参数.json（程序生成时为query-params.json）：caseId、modelSha、expectedRule；Q05/Q06不能只传caseId。\n// Q00为可选图显示，不计入查询验收。\nMATCH (a:D03V01)-[r]->(b:D03V01) RETURN a,r,b;\n\n'+'\n\n'.join('// '+k+'\n'+v+';' for k,v in queries().items()))
    print(json.dumps({'nodes':len(payload['nodes']),'relationships':len(payload['relationships']),'modelSHA256':payload['sourceModelSha256'],'assignments':[(x['example'],x['status'],x['candidateType']) for x in assignments]},ensure_ascii=False))
