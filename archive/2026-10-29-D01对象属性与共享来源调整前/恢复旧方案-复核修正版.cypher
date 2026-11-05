// 仅用于人工确认恢复；必须同时恢复快照中的案例主源与文档。未执行恢复。
OPTIONAL MATCH (n)
WHERE n.datasetId=$datasetId OR n.uid STARTS WITH $prefix
WITH collect(n) AS oldNodes
WHERE size(oldNodes)=size($expectedNodes)
AND size($nodes)>0
AND all(row IN $nodes WHERE row.properties.datasetId=$datasetId AND row.properties.uid STARTS WITH $prefix AND 'KGItem' IN row.labels AND 'D01V01' IN row.labels)
AND size(reduce(ids=[],row IN $nodes | CASE WHEN row.properties.uid IN ids THEN ids ELSE ids+[row.properties.uid] END))=size($nodes)
AND size(reduce(ids=[],row IN $relationships | CASE WHEN row.properties.uid IN ids THEN ids ELSE ids+[row.properties.uid] END))=size($relationships)
AND all(row IN $relationships WHERE row.properties.datasetId=$datasetId AND row.properties.uid STARTS WITH $prefix AND any(n IN $nodes WHERE n.properties.uid=row.source) AND any(n IN $nodes WHERE n.properties.uid=row.target))
AND all(n IN oldNodes WHERE any(row IN $expectedNodes WHERE n.uid=row.properties.uid AND properties(n)=row.properties AND size(labels(n))=size(row.labels) AND all(l IN labels(n) WHERE l IN row.labels)))
CALL {
 WITH oldNodes
 OPTIONAL MATCH (a)-[r]->(b) WHERE a IN oldNodes OR b IN oldNodes
 RETURN collect(CASE WHEN r IS NOT NULL THEN {edge:r,source:a,target:b} END) AS oldEdges
}
WITH oldNodes,oldEdges
WHERE size(oldEdges)=size($expectedRelationships)
AND all(e IN oldEdges WHERE e.source IN oldNodes AND e.target IN oldNodes)
AND all(e IN oldEdges WHERE any(row IN $expectedRelationships WHERE e.source.uid=row.source AND e.target.uid=row.target AND type(e.edge)=row.type AND properties(e.edge)=row.properties))
CALL {
 WITH oldEdges
 UNWIND oldEdges AS e WITH e.edge AS r DELETE r
 RETURN count(*) AS relationshipsRemoved
}
CALL {
 WITH oldNodes
 UNWIND oldNodes AS n DELETE n
 RETURN count(*) AS nodesRemoved
}
CALL {
 UNWIND $nodes AS row
 CREATE (n:$(row.labels)) SET n=row.properties
 RETURN count(n) AS nodesCreated
}
CALL {
 UNWIND $relationships AS row
 MATCH (a:KGItem {uid:row.source}),(b:KGItem {uid:row.target})
 WHERE a.datasetId=$datasetId AND b.datasetId=$datasetId
 CREATE (a)-[r:$(row.type)]->(b) SET r=row.properties
 RETURN count(r) AS relationshipsCreated
}
RETURN nodesRemoved,relationshipsRemoved,nodesCreated,relationshipsCreated;
