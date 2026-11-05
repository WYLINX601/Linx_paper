MATCH (n:D01V01 {datasetId:$datasetId})
WITH collect(n) AS targets
WHERE size(targets) = $nodeCount
 AND all(n IN targets WHERE n.sourceModelSha256 = $sourceModelSha256)
 AND NOT EXISTS { MATCH (a)-[r]-(b) WHERE a IN targets AND NOT b IN targets }
WITH targets, size(targets) AS deletedNodes
FOREACH (n IN targets | DETACH DELETE n)
RETURN deletedNodes
