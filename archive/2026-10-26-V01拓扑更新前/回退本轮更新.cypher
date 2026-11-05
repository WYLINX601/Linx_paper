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

RETURN updatedNodes,deletedNodes,deletedRelationships,0 AS createdNodes,0 AS createdRelationships
