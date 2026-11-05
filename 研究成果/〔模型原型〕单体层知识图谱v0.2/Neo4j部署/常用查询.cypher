// 1. 文献图：返回节点和关系列，在 Neo4j Browser 中显示 Graph 视图
MATCH (a:KGItem:Entity:Literature)-[r]->(b:KGItem:Entity:Literature)
RETURN a, r, b;

// 2. 虚构演示图：单独返回节点和关系列，在 Neo4j Browser 中显示 Graph 视图
MATCH (a:KGItem:Entity:Demo)-[r]->(b:KGItem:Entity:Demo)
RETURN a, r, b;

// 3. 全部领域实体之间的展示关系（表格；每条边携带 assertionId 与 qualifiers JSON）
MATCH (a:KGItem:Entity)-[r]->(b:KGItem:Entity)
WHERE a:Literature OR a:Demo
RETURN a.datasetKind AS dataset, a.label AS fromLabel, type(r) AS relation,
       b.label AS toLabel, r.assertionId AS assertionId,
       r.sourceField AS sourceField, r.qualifiers AS qualifiers
ORDER BY dataset, fromLabel, relation, toLabel;

// 4. 仅文献案例中的领域实体及实体间展示关系（表格）
MATCH (a:KGItem:Entity:Literature)-[r]->(b:KGItem:Entity:Literature)
RETURN a.label AS fromLabel, type(r) AS relation, b.label AS toLabel,
       r.assertionId AS assertionId, r.sourceField AS sourceField,
       r.qualifiers AS qualifiers
ORDER BY fromLabel, relation, toLabel;

// 5. 仅虚构空间关系演示中的领域实体及实体间展示关系（表格）
MATCH (a:KGItem:Entity:Demo)-[r]->(b:KGItem:Entity:Demo)
RETURN a.label AS fromLabel, type(r) AS relation, b.label AS toLabel,
       r.assertionId AS assertionId, r.sourceField AS sourceField,
       r.qualifiers AS qualifiers
ORDER BY fromLabel, relation, toLabel;

// 6. 周湖8号的原始特征断言及其证据、来源回溯
MATCH (record:KGItem:Entity:Literature {uid: 'kgv02:literature:entity:R_8'})
MATCH (a:KGItem:Assertion:Literature)-[:SUBJECT]->(record)
OPTIONAL MATCH (a)-[:EVIDENCED_BY]->(ev:KGItem:Evidence:Literature)-[:FROM_SOURCE]->(src:KGItem:Source:Literature)
RETURN a.sourceId AS assertionId, a.predicate AS feature, a.valueJson AS valueJson,
       a.scope AS scope, a.status AS status, a.attribution AS attribution,
       ev.sourceId AS evidenceId, ev.locator AS locator, ev.summary AS evidence,
       src.title AS sourceTitle
ORDER BY feature, evidenceId;

// 7. 堂屋与前廊的显式通行断言：同时检查方向、界面、情境和证据
MATCH (a:KGItem:Assertion:Demo {predicate: 'direct_access_to'})
MATCH (a)-[:SUBJECT]->(from:KGItem:Entity:Demo)
MATCH (a)-[:OBJECT]->(to:KGItem:Entity:Demo)
MATCH (a)-[:VIA]->(via:KGItem:Entity:Demo)
MATCH (a)-[:EVIDENCED_BY]->(ev:KGItem:Evidence:Demo)-[:FROM_SOURCE]->(src:KGItem:Source:Demo)
RETURN a.sourceId AS assertionId, from.label AS from, to.label AS to,
       via.label AS interface, a.accessContextJson AS accessContext,
       a.valueJson AS allowed, ev.sourceId AS evidenceId, ev.summary AS evidence,
       src.title AS source
ORDER BY assertionId;

// 8. 分类比较：分类决策、四项判据 JSON、输入断言与证据
MATCH (c:KGItem:Classification:Literature)-[:SUBJECT]->(subject:KGItem:Entity:Literature)
MATCH (c)-[:TYPE]->(type:KGItem:Entity:Literature)
MATCH (c)-[:SCHEME]->(scheme:KGItem:Entity:Literature)
OPTIONAL MATCH (c)-[:INPUT]->(input:KGItem:Assertion:Literature)
OPTIONAL MATCH (c)-[:EVIDENCED_BY]->(ev:KGItem:Evidence:Literature)
RETURN c.sourceId AS classificationId, subject.label AS subject,
       type.label AS type, scheme.label AS scheme, c.decision AS decision,
       c.criteriaResultsJson AS criteriaResultsJson,
       collect(DISTINCT input.sourceId) AS inputAssertions,
       collect(DISTINCT ev.sourceId) AS evidence
ORDER BY classificationId;

// 9. 周湖1号屋面争议图：支持证据用 EVIDENCED_BY，冲突来源用 CONFLICTING_EVIDENCE
MATCH (a:KGItem:Assertion:Literature {uid: 'kgv02:literature:assertion:F_1_roof_layered'})
OPTIONAL MATCH (a)-[supports:EVIDENCED_BY]->(support:KGItem:Evidence:Literature)
OPTIONAL MATCH (a)-[conflicts:CONFLICTING_EVIDENCE]->(conflict:KGItem:Evidence:Literature)
OPTIONAL MATCH (support)-[supportSourceRel:FROM_SOURCE]->(supportSource:KGItem:Source:Literature)
OPTIONAL MATCH (conflict)-[conflictSourceRel:FROM_SOURCE]->(conflictSource:KGItem:Source:Literature)
RETURN a, supports, support, supportSourceRel, supportSource,
       conflicts, conflict, conflictSourceRel, conflictSource;

// 10. 从来源回溯支持或冲突证据被哪些断言/分类使用
MATCH (claim:KGItem)-[:EVIDENCED_BY]->(ev:KGItem:Evidence)-[:FROM_SOURCE]->(src:KGItem:Source)
WHERE claim:Assertion OR claim:Classification
RETURN src.datasetKind AS dataset, src.title AS source,
       ev.sourceId AS evidenceId, ev.locator AS locator,
       labels(claim) AS claimLabels, claim.sourceId AS claimId,
       claim.predicate AS predicate, claim.decision AS decision,
       'supporting' AS evidenceRole
UNION
MATCH (claim:KGItem)-[:CONFLICTING_EVIDENCE]->(ev:KGItem:Evidence)-[:FROM_SOURCE]->(src:KGItem:Source)
WHERE claim:Assertion
RETURN src.datasetKind AS dataset, src.title AS source,
       ev.sourceId AS evidenceId, ev.locator AS locator,
       labels(claim) AS claimLabels, claim.sourceId AS claimId,
       claim.predicate AS predicate, claim.decision AS decision,
       'conflicting' AS evidenceRole
ORDER BY dataset, source, evidenceId, claimId;
