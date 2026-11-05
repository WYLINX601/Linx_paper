CALL { UNWIND $oldNodes AS row MATCH (n:KGItem {uid:row.properties.uid})
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
CALL { UNWIND $nodes0 AS row CREATE (n:`Demo`:`Element`:`Entity`:`KGItem`:`RoofSurface`:`V01`) SET n = row.properties RETURN count(*) AS madeNodes0 }
CALL { UNWIND $rels0 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`AXIS_JOINS`]->(b) SET r = row.properties RETURN count(*) AS madeRels0 }
CALL { UNWIND $rels1 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`DOCUMENTS`]->(b) SET r = row.properties RETURN count(*) AS madeRels1 }
CALL { UNWIND $rels2 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`ENVELOPE_INTERSECTS`]->(b) SET r = row.properties RETURN count(*) AS madeRels2 }
CALL { UNWIND $rels3 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`PART_OF`]->(b) SET r = row.properties RETURN count(*) AS madeRels3 }
CALL { UNWIND $rels4 AS row MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target}) CREATE (a)-[r:`SHARES_BOUNDARY`]->(b) SET r = row.properties RETURN count(*) AS madeRels4 }
RETURN updatedNodes,deletedNodes,deletedRelationships,2 AS createdNodes,25 AS createdRelationships
