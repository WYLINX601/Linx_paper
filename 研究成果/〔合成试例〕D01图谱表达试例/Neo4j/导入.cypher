OPTIONAL MATCH (existing)
WHERE existing.datasetId = $datasetId OR existing.uid STARTS WITH $prefix
WITH count(existing) AS collisions
WHERE collisions = 0
CALL {
 UNWIND $nodes AS row
 CREATE (n:$(row.labels))
 SET n = row.properties
 RETURN count(n) AS nodesCreated
}
CALL {
 UNWIND $relationships AS row
 MATCH (a:KGItem {uid:row.source}), (b:KGItem {uid:row.target})
 WHERE a.datasetId = $datasetId AND b.datasetId = $datasetId
 CREATE (a)-[r:$(row.type)]->(b)
 SET r = row.properties
 RETURN count(r) AS relationshipsCreated
}
RETURN nodesCreated, relationshipsCreated
