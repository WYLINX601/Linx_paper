// 入口与待定项
MATCH p=(v:ModelVersion {uid:'kgmodel:single:v01:ModelVersion:root'})-[:HAS_OPEN_ISSUE]->() RETURN p;

// 实体关系总览
MATCH p=(a:ModelEntityType)-[:ALLOWS_RELATION]->(r:ModelRelation)-[:TO_TYPE]->(b:ModelEntityType) WHERE a.uid STARTS WITH 'kgmodel:single:v01:' AND r.id IN ['has_building','has_space','has_element','bounds','has_surface','interface_of','realized_by'] RETURN p;

// 查看空间属性
MATCH p=(t:ModelEntityType {uid:'kgmodel:single:v01:ModelEntityType:Space'})-[:HAS_PROPERTY]->(f) RETURN p;

// 查看体量错落依据
MATCH p=(i:ModelResearchItem {uid:'kgmodel:single:v01:ModelResearchItem:B402'})-[r:USES_ENTITY_TYPE|USES_PROPERTY|USES_RELATION|REFERENCES_EVIDENCE]->() RETURN p;

// 堂屋前廊关系设计
MATCH p=(r:ModelRelation)-[:TO_TYPE]->(t:ModelEntityType) WHERE r.uid STARTS WITH 'kgmodel:single:v01:' AND r.id IN ['adjacent_to','direct_access_to','interface_of','realized_by'] RETURN p;

// 某个分析需要什么
MATCH p=(q:ModelAnalysisQuestion {uid:'kgmodel:single:v01:ModelAnalysisQuestion:Q03'})-[r:REQUIRES_PROPERTY|REQUIRES_RELATION|ANALYSES_ITEM]->() RETURN p;

// 属性完整字典
MATCH (p:ModelProperty) WHERE p.uid STARTS WITH 'kgmodel:single:v01:' RETURN p.id,p.name,p.definition,p.datatype,p.unit,p.storage ORDER BY p.id;

// 原条目证据定位
MATCH (i:ModelResearchItem {uid:'kgmodel:single:v01:ModelResearchItem:B402'}) RETURN i.definitionJson;

// 候选版本数量
MATCH (n:ModelDefinition) WHERE n.uid STARTS WITH 'kgmodel:single:v01:' RETURN n.kind,count(*) ORDER BY n.kind;
