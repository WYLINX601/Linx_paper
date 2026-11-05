CALL { UNWIND $oldNodes AS row MATCH (n) WHERE elementId(n)=row.elementId WITH n ORDER BY elementId(n) SET n.uid=n.uid RETURN count(n) AS lockedNodes }
CALL { UNWIND $lockRels0 AS rid MATCH ()-[r]->() WHERE elementId(r)=rid WITH r ORDER BY elementId(r) SET r.`assertionId`=r.`assertionId` RETURN count(r) AS lockedRels0 }
CALL { UNWIND $lockRels1 AS rid MATCH ()-[r]->() WHERE elementId(r)=rid WITH r ORDER BY elementId(r) SET r.`linkId`=r.`linkId` RETURN count(r) AS lockedRels1 }
CALL { UNWIND $lockRels2 AS rid MATCH ()-[r]->() WHERE elementId(r)=rid WITH r ORDER BY elementId(r) SET r.`projectionId`=r.`projectionId` RETURN count(r) AS lockedRels2 }
CALL { MATCH (n) RETURN count(n) AS liveNodes }
CALL { MATCH ()-[r]->() RETURN count(r) AS liveRels }
CALL { UNWIND $oldNodes AS row OPTIONAL MATCH (n) WHERE elementId(n)=row.elementId
RETURN collect(n) AS oldNodeObjects, sum(CASE WHEN n IS NOT NULL AND properties(n)=row.properties AND size(labels(n))=size(row.labels) AND all(l IN row.labels WHERE l IN labels(n)) THEN 1 ELSE 0 END) AS equalNodes }
CALL { UNWIND $oldRels AS row OPTIONAL MATCH (a)-[r]->(b) WHERE elementId(r)=row.elementId
RETURN sum(CASE WHEN r IS NOT NULL AND a.uid=row.source AND b.uid=row.target AND type(r)=row.type AND properties(r)=row.properties THEN 1 ELSE 0 END) AS equalRels }
WITH * WHERE lockedNodes=liveNodes AND lockedRels0+lockedRels1+lockedRels2=liveRels AND liveNodes=size($oldNodes) AND liveRels=size($oldRels) AND equalNodes=liveNodes AND equalRels=liveRels
CALL { UNWIND $oldRels AS row MATCH ()-[r]->() WHERE elementId(r)=row.elementId DELETE r RETURN count(*) AS archivedRelationships }
CALL { WITH oldNodeObjects UNWIND oldNodeObjects AS n DELETE n RETURN count(*) AS archivedNodes }
CALL { UNWIND $nodes0 AS row CREATE (n:`Building`:`Demo`:`Entity`:`KGItem`:`V01`) SET n = row.properties RETURN count(*) AS madeNodes0 }
CALL { UNWIND $nodes1 AS row CREATE (n:`Column`:`Demo`:`Element`:`Entity`:`KGItem`:`V01`:`材质_木`) SET n = row.properties RETURN count(*) AS madeNodes1 }
CALL { UNWIND $nodes2 AS row CREATE (n:`DatasetSnapshot`:`Demo`:`KGItem`) SET n = row.properties RETURN count(*) AS madeNodes2 }
CALL { UNWIND $nodes3 AS row CREATE (n:`Demo`:`Element`:`Entity`:`KGItem`:`Roof`:`V01`:`材质_木`:`材质_陶瓦`) SET n = row.properties RETURN count(*) AS madeNodes3 }
CALL { UNWIND $nodes4 AS row CREATE (n:`Demo`:`Element`:`Entity`:`KGItem`:`V01`:`Wall`:`材质_灰泥`:`材质_砖`) SET n = row.properties RETURN count(*) AS madeNodes4 }
CALL { UNWIND $nodes5 AS row CREATE (n:`Demo`:`Entity`:`Interface`:`KGItem`:`V01`) SET n = row.properties RETURN count(*) AS madeNodes5 }
CALL { UNWIND $nodes6 AS row CREATE (n:`Demo`:`Entity`:`KGItem`:`Space`:`V01`) SET n = row.properties RETURN count(*) AS madeNodes6 }
CALL { UNWIND $nodes7 AS row CREATE (n:`Demo`:`Evidence`:`KGItem`:`V01`) SET n = row.properties RETURN count(*) AS madeNodes7 }
CALL { UNWIND $rels0 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`ASSOCIATED_WITH`]->(b) SET r = row.properties RETURN count(*) AS madeRels0 }
CALL { UNWIND $rels1 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`BOUNDED_BY`]->(b) SET r = row.properties RETURN count(*) AS madeRels1 }
CALL { UNWIND $rels2 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`DIRECT_ACCESS_TO`]->(b) SET r = row.properties RETURN count(*) AS madeRels2 }
CALL { UNWIND $rels3 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`DOCUMENTS`]->(b) SET r = row.properties RETURN count(*) AS madeRels3 }
CALL { UNWIND $rels4 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`INTERFACE_OF`]->(b) SET r = row.properties RETURN count(*) AS madeRels4 }
CALL { UNWIND $rels5 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`PART_OF`]->(b) SET r = row.properties RETURN count(*) AS madeRels5 }
CALL { UNWIND $rels6 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`REALIZED_IN`]->(b) SET r = row.properties RETURN count(*) AS madeRels6 }
CALL { UNWIND $rels7 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`SPATIAL_RELATION`]->(b) SET r = row.properties RETURN count(*) AS madeRels7 }
CALL { UNWIND $rels8 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`SUPPORTS_SYSTEM`]->(b) SET r = row.properties RETURN count(*) AS madeRels8 }
RETURN archivedNodes, 41 AS expectedNodes, 166 AS expectedRelationships
