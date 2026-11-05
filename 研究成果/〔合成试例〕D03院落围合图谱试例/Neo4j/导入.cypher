WITH $nodes AS ns,$relationships AS rs,$datasetId AS ds,$prefix AS prefix
WHERE ds='D03V01' AND prefix='D03V01:' AND size(ns)>0 AND size(rs)>0
 AND size(reduce(ids=[],n IN ns | CASE WHEN n.properties.uid IN ids THEN ids ELSE ids+[n.properties.uid] END))=size(ns)
 AND size(reduce(ids=[],r IN rs | CASE WHEN r.properties.uid IN ids THEN ids ELSE ids+[r.properties.uid] END))=size(rs)
 AND all(n IN ns WHERE n.properties.uid STARTS WITH prefix AND n.properties.caseId=ds AND n.properties.datasetId=ds
     AND 'KGItem' IN n.labels AND 'D03V01' IN n.labels AND all(l IN n.labels WHERE l IN ["Building","ClassificationScheme","Courtyard","D03V01","DwellingUnit","Element","EntranceInterface","Interface","KGItem","Source","Space","SyntheticSource","Wall","Zone"])
     AND n.properties.sourceModelSha256=$sourceModelSha256)
 AND all(r IN rs WHERE r.properties.uid STARTS WITH prefix AND r.properties.caseId=ds AND r.properties.datasetId=ds
     AND r.properties.sourceModelSha256=$sourceModelSha256
     AND r.type IN ["BOT_CONTAINS_ELEMENT","BOT_HAS_BUILDING","BOT_HAS_SPACE","BOUNDARY_PARTICIPANT","CLASSIFIED_BY","HAS_SOURCE","INTERFACE_OF"]
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
