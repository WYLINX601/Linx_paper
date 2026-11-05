// Q00: graph inspection; read-only
MATCH (a:D03V01)-[r]->(b:D03V01) RETURN a,r,b;

// Q01
MATCH (u:DwellingUnit {caseId:$caseId})-[:BOT_HAS_SPACE]->(c:Courtyard) WHERE u.exampleId IN ['A','B','C','D']
OPTIONAL MATCH (u)-[:BOT_HAS_BUILDING]->(b:Building)
RETURN u.exampleId AS example,u.uid AS unit,c.uid AS courtyard,collect(b.uid) AS buildings,c.geometryState AS geometryState ORDER BY example;

// Q02
MATCH (c:Courtyard {caseId:$caseId}) WHERE c.exampleId IN ['A','B','C','D'] UNWIND range(0,size(c.boundaryIds)-1) AS i
OPTIONAL MATCH (c)-[p:BOUNDARY_PARTICIPANT]->(n) WHERE p.boundaryId=c.boundaryIds[i]
RETURN c.exampleId AS example,c.uid AS courtyard,c.boundaryIds[i] AS side,c.boundaryStates[i] AS state,c.boundaryKinds[i] AS kind,n.uid AS participant,p.participantScope AS participantScope ORDER BY example,i;

// Q03
MATCH (i:EntranceInterface {caseId:$caseId}) WHERE i.exampleId IN ['A','B','C','D']
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
 i.farSideStatus AS farSideStatus,i.passabilityStatus AS passabilityStatus ORDER BY example;

// Q04
MATCH (n:D03V01)-[s:HAS_SOURCE]->(e:Source)
RETURN n.uid AS object,e.uid AS source,s.fields AS fields,s.locator AS locator,s.locatorKind AS locatorKind,s.sourceVersion AS expectedVersion,e.sourceVersion AS actualVersion,s.evidenceRole AS evidenceRole ORDER BY object;

// Q05
MATCH (c:Courtyard {caseId:$caseId}) WHERE c.exampleId IN ['A','B','C','D']
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
 AND assignment.inputFields=["boundaryIds","boundaryKinds","boundaryStates","shapeCode","boundaryParticipantUids","boundaryLocators","geometryVersion"]
 AND assignment.sourceRelationUid=sources[0].edge.uid
 AND sources[0].src.sourceVersion=assignment.inputVersion
 AND sources[0].edge.sourceVersion=assignment.inputVersion
 AND c.dataVersion=assignment.inputModelVersion
 AND c.geometryVersion=assignment.inputBoundaryVersion
 AND sources[0].edge.locator=c.sourceLocator
 AND all(k IN ["boundaryIds","boundaryKinds","boundaryStates","shapeCode","boundaryParticipantUids","boundaryLocators","geometryVersion"] WHERE k IN sources[0].edge.fields)
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
WITH c,scheme,inputValid,cachedType,cachedStatus,
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
WITH *,CASE WHEN resultStatus='candidate-assigned' THEN matches[0] ELSE '' END AS candidateType
RETURN c.uid AS courtyard,c.exampleId AS example,patternKey,resultStatus,candidateType,
 CASE WHEN resultStatus IN ['candidate-assigned','known-unmatched','rule-conflict'] THEN matches ELSE [] END AS matches,
 scheme.ruleVersion AS ruleVersion,cachedType,cachedStatus,
 coalesce(resultStatus=cachedStatus AND candidateType=cachedType,false) AS cacheConsistent,
 c.boundaryIds AS boundaryIds,c.boundaryKinds AS boundaryKinds,c.boundaryStates AS boundaryStates,
 c.boundaryParticipantUids AS participants,c.boundaryLocators AS sourceLocators,
 c.geometryVersion AS geometryVersion,c.dataVersion AS inputModelVersion ORDER BY example;

// Q06
CALL { MATCH (c:Courtyard {caseId:$caseId}) WHERE c.exampleId IN ['A','B','C','D']
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
 AND assignment.inputFields=["boundaryIds","boundaryKinds","boundaryStates","shapeCode","boundaryParticipantUids","boundaryLocators","geometryVersion"]
 AND assignment.sourceRelationUid=sources[0].edge.uid
 AND sources[0].src.sourceVersion=assignment.inputVersion
 AND sources[0].edge.sourceVersion=assignment.inputVersion
 AND c.dataVersion=assignment.inputModelVersion
 AND c.geometryVersion=assignment.inputBoundaryVersion
 AND sources[0].edge.locator=c.sourceLocator
 AND all(k IN ["boundaryIds","boundaryKinds","boundaryStates","shapeCode","boundaryParticipantUids","boundaryLocators","geometryVersion"] WHERE k IN sources[0].edge.fields)
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
WITH c,scheme,inputValid,cachedType,cachedStatus,
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
WITH *,CASE WHEN resultStatus='candidate-assigned' THEN matches[0] ELSE '' END AS candidateType
RETURN c.uid AS courtyard,c.exampleId AS example,patternKey,resultStatus,candidateType,
 CASE WHEN resultStatus IN ['candidate-assigned','known-unmatched','rule-conflict'] THEN matches ELSE [] END AS matches,
 scheme.ruleVersion AS ruleVersion,cachedType,cachedStatus,
 coalesce(resultStatus=cachedStatus AND candidateType=cachedType,false) AS cacheConsistent,
 c.boundaryIds AS boundaryIds,c.boundaryKinds AS boundaryKinds,c.boundaryStates AS boundaryStates,
 c.boundaryParticipantUids AS participants,c.boundaryLocators AS sourceLocators,
 c.geometryVersion AS geometryVersion,c.dataVersion AS inputModelVersion ORDER BY example } RETURN collect({example:example,courtyard:courtyard,pattern:patternKey,status:resultStatus,candidateType:candidateType,ruleVersion:ruleVersion,cacheConsistent:cacheConsistent,boundaryIds:boundaryIds,boundaryKinds:boundaryKinds,boundaryStates:boundaryStates,participants:participants,sourceLocators:sourceLocators,geometryVersion:geometryVersion,inputModelVersion:inputModelVersion}) AS d06Comparison;

// Q07
MATCH (a)-[r]->(b) WHERE coalesce(a.caseId=$caseId,false) <> coalesce(b.caseId=$caseId,false) RETURN count(r) AS crossDatasetEdges;

// Q08
MATCH (n:D03V01) WITH labels(n) AS labels,count(*) AS n RETURN labels,n ORDER BY labels;

// Q09
MATCH (n:D03V01:Space {exampleId:"E"}) RETURN n.uid AS uid,properties(n) AS inputs ORDER BY uid;

// Q10
MATCH (n:D03V01:Courtyard {exampleId:"E"}) OPTIONAL MATCH (n)-[r:BOUNDARY_PARTICIPANT]->(p) RETURN n.uid AS uid,n.boundaryRecordsJson AS segments,collect({uid:r.uid,participant:p.uid,properties:properties(r)}) AS participants ORDER BY uid;

// Q11
MATCH (i:D03V01:EntranceInterface {exampleId:"E"}) OPTIONAL MATCH (i)-[r:INTERFACE_OF]->(p) RETURN i.uid AS uid,properties(i) AS inputs,collect({role:r.role,participant:p.uid}) AS roles ORDER BY uid;

// Q12
MATCH (a:D03V01)-[r:DIRECT_ACCESS_TO {exampleId:"E"}]->(b:D03V01) RETURN a.uid AS source,b.uid AS target,properties(r) AS inputs ORDER BY r.uid;

// Q13
MATCH (n:D03V01 {exampleId:"E"}) WHERE n.polygonJson IS NOT NULL RETURN n.uid AS uid,labels(n) AS labels,n.polygonJson AS polygon,n.level AS level,n.coordinateFrame AS frame,n.geometryBasis AS basis,n.unit AS unit,n.geometryVersion AS version ORDER BY uid;

// Q14
MATCH (s:D03V01:Space {exampleId:"E"}) OPTIONAL MATCH (s)-[r:HAS_SOURCE]->(e:Source) RETURN s.uid AS uid,s.useState AS state,s.useValues AS uses,s.useContext AS context,s.useScope AS scope,e.uid AS source,r.locator AS locator,r.fields AS fields ORDER BY uid;

// Q15
MATCH (a:D03V01)-[r:PLAN_POSITION]->(b:D03V01) RETURN a.uid AS subject,b.uid AS reference,properties(r) AS cached ORDER BY r.uid;
