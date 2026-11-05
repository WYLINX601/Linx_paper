"""Read-only Cypher capability checks for the one active prototype."""
VERSION='V01-unified-2.0'
def queries():
 return {
 'Q01_identity':"MATCH (n:V01) RETURN n.uid AS uid,n.name AS name,labels(n) AS labels,n.datasetId AS dataset ORDER BY uid",
 'Q02_dimensions':"MATCH (n:V01) WHERE n.uid IN $dimensionUids RETURN n.uid AS uid,n.widthM AS widthM,n.depthM AS depthM,n.groundZM AS groundZM,n.eaveZM AS eaveZM,n.eaveZM-n.groundZM AS ownEaveHeightM,n.widthM/n.depthM AS widthDepthRatio,(n.eaveZM-n.groundZM)/n.widthM AS ownEaveHeightWidthRatio,n.measurementBoundaryBasis AS basis ORDER BY uid",
 'Q03_comparison':'''MATCH (c:V01 {uid:'V01:CMP01'})
OPTIONAL MATCH (c)-[ar:COMPARES_SUBJECT]->(a)
OPTIONAL MATCH (c)-[br:COMPARES_REFERENCE]->(b)
OPTIONAL MATCH (a)-[sa:HAS_SOURCE]->(asrc) WHERE sa.id=ar.sourceRelationId AND 'eaveZM' IN sa.fields
OPTIONAL MATCH (b)-[sb:HAS_SOURCE]->(bsrc) WHERE sb.id=br.sourceRelationId AND 'eaveZM' IN sb.fields
OPTIONAL MATCH (a)-[da:USES_DATUM]->(ad) WHERE 'eaveZM' IN da.fields
OPTIONAL MATCH (b)-[db:USES_DATUM]->(bd) WHERE 'eaveZM' IN db.fields
WITH c,a,b,coalesce(a.unit='m' AND b.unit='m' AND a.geometryActive=true AND b.geometryActive=true AND ad=bd AND da.frameVersion=$version AND db.frameVersion=$version AND a.scenario=b.scenario AND c.scenario=a.scenario AND a.geometryVersion=$version AND b.geometryVersion=$version AND ar.geometryVersion=a.geometryVersion AND br.geometryVersion=b.geometryVersion AND c.inputGeometryVersion=ar.geometryVersion AND c.inputGeometryVersion=br.geometryVersion AND ar.expectedSourceVersion=sa.sourceVersion AND ar.expectedSourceVersion=asrc.sourceVersion AND br.expectedSourceVersion=sb.sourceVersion AND br.expectedSourceVersion=bsrc.sourceVersion AND a.eaveZM IS NOT NULL AND b.eaveZM IS NOT NULL,false) AS valid
RETURN c.uid AS uid,a.uid AS subject,b.uid AS reference,valid,CASE WHEN valid THEN a.eaveZM-b.eaveZM ELSE null END AS valueM,CASE WHEN valid THEN abs(c.valueM-(a.eaveZM-b.eaveZM))<1e-9 ELSE false END AS cacheAgreement''',
 'Q04_boundary':"MATCH (c:V01 {uid:'V01:S05'})-[r:BOUNDARY_PARTICIPANT]->(p) RETURN c.uid AS courtyard,p.uid AS participant,p.name AS name,r.uid AS relationshipUid,r.boundaryId AS boundaryId,r.participantRole AS role,r.analysisSliceZM AS sliceZM,r.referenceLengthM AS lengthM,r.solidIntervalBoundsM AS intervals,r.netContributionM AS netContributionM ORDER BY boundaryId,participant",
 'Q05_interfaces':"MATCH (i:V01)-[r:INTERFACE_OF]->(p) WHERE i.uid IN ['V01:I04','V01:I05'] RETURN i.uid AS interface,p.uid AS participant,r.role AS role,r.uid AS relationshipUid,i.referenceMode AS referenceMode,i.relativePosition AS relativePosition,i.sideBoundaryMappingsJson AS sideMappings ORDER BY interface,role",
 'Q06_outward_path':'''MATCH p=(a:V01 {uid:'V01:S06'})-[rs:DIRECT_ACCESS_TO*1..8]-(b:V01 {uid:'V01:S04'})
WHERE all(n IN nodes(p) WHERE n.uid IN $externalUids)
AND all(idx IN range(0,size(rs)-1) WHERE rs[idx].contextId='V01-walk-baseline' AND rs[idx].snapshot='V01-synthetic-T0' AND rs[idx].actor='正常成人步行（旧合成情境断言）' AND (startNode(rs[idx])=nodes(p)[idx] OR rs[idx].bidirectional=true))
RETURN [n IN nodes(p)|n.uid] AS nodes,[r IN rs|r.viaUid] AS via,size(rs) AS crossings ORDER BY crossings LIMIT 1''',
 'Q07_return_path':'''MATCH p=(a:V01 {uid:'V01:S04'})-[rs:DIRECT_ACCESS_TO*1..8]-(b:V01 {uid:'V01:S06'})
WHERE all(n IN nodes(p) WHERE n.uid IN $externalUids)
AND all(idx IN range(0,size(rs)-1) WHERE rs[idx].contextId='V01-walk-baseline' AND rs[idx].snapshot='V01-synthetic-T0' AND rs[idx].actor='正常成人步行（旧合成情境断言）' AND (startNode(rs[idx])=nodes(p)[idx] OR rs[idx].bidirectional=true))
RETURN [n IN nodes(p)|n.uid] AS nodes,[r IN rs|r.viaUid] AS via,size(rs) AS crossings ORDER BY crossings LIMIT 1''',
 'Q08_local_area_inputs':"MATCH (u:V01 {uid:'V01:U01'}),(n:V01) WHERE n.uid IN ['V01:S04','V01:S05'] RETURN u.areaScopeId AS scopeId,u.areaScopePolygonXY AS scope,n.uid AS uid,n.footprintXY AS polygon,n.groundZM AS groundZM,n.geometryVersion AS geometryVersion ORDER BY uid",
 'Q09_uses':"MATCH (n:V01)-[r:HAS_SOURCE]->(src) WHERE n.uid IN $externalUids AND n.useState='known' AND all(f IN ['useState','useValues','useScope'] WHERE f IN r.fields) AND r.sourceVersion=src.sourceVersion UNWIND n.useValues AS use RETURN use,collect(DISTINCT n.uid) AS spaceUids,count(DISTINCT n.uid) AS spaceCount ORDER BY use",
 'Q10_sources':"MATCH (n:V01)-[r:HAS_SOURCE]->(s) WHERE n.uid IN $dimensionUids RETURN n.uid AS uid,s.uid AS source,r.fields AS fields,r.locator AS locator,r.sourceVersion AS sourceVersion,s.sourceVersion AS actualSourceVersion ORDER BY uid,source",
 'Q11_roles_and_scope':"MATCH (a:V01)-[r]->(b:V01) WHERE type(r) IN ['BOT_HAS_SPACE','BOT_HAS_BUILDING','MEMBER_OF_ZONE','PART_OF','PLAN_POSITION'] RETURN a.uid AS source,b.uid AS target,type(r) AS type,r.role AS role,r.scope AS scope ORDER BY type,source,target",
 'Q12_no_duplicates':"MATCH (n) RETURN count(CASE WHEN n.uid STARTS WITH 'D01V01:' OR n.uid STARTS WITH 'D03V01:' THEN 1 END) AS legacyActiveNodes,count(CASE WHEN n.uid='V01:S05' THEN 1 END) AS courtyardIdentity,count(CASE WHEN n.uid='V01:S01' THEN 1 END) AS hallIdentity",
 'Q13_legacy_topology':"MATCH (a:V01)-[r]->(b:V01) WHERE type(r) IN ['AXIS_JOINS','ENVELOPE_INTERSECTS','SHARES_BOUNDARY'] RETURN type(r) AS type,count(r) AS count ORDER BY type"
 }
def query_params():return {'version':VERSION,'dimensionUids':['V01:'+s for s in ['B01','B02','S01','S02','S03','S04','S05','S06']],'externalUids':['V01:S04','V01:S05','V01:S06']}
