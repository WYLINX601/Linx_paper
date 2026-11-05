// Q01_identity
MATCH (n:V01) RETURN n.uid AS uid,n.name AS name,labels(n) AS labels,n.datasetId AS dataset ORDER BY uid;

// Q02_dimensions
MATCH (n:V01) WHERE n.uid IN $dimensionUids RETURN n.uid AS uid,n.widthM AS widthM,n.depthM AS depthM,n.groundZM AS groundZM,n.eaveZM AS eaveZM,n.eaveZM-n.groundZM AS ownEaveHeightM,n.widthM/n.depthM AS widthDepthRatio,(n.eaveZM-n.groundZM)/n.widthM AS ownEaveHeightWidthRatio,n.measurementBoundaryBasis AS basis ORDER BY uid;

// Q03_comparison
MATCH (c:V01 {uid:'V01:CMP01'})
OPTIONAL MATCH (c)-[ar:COMPARES_SUBJECT]->(a)
OPTIONAL MATCH (c)-[br:COMPARES_REFERENCE]->(b)
OPTIONAL MATCH (a)-[sa:HAS_SOURCE]->(asrc) WHERE sa.id=ar.sourceRelationId AND 'eaveZM' IN sa.fields
OPTIONAL MATCH (b)-[sb:HAS_SOURCE]->(bsrc) WHERE sb.id=br.sourceRelationId AND 'eaveZM' IN sb.fields
OPTIONAL MATCH (a)-[da:USES_DATUM]->(ad) WHERE 'eaveZM' IN da.fields
OPTIONAL MATCH (b)-[db:USES_DATUM]->(bd) WHERE 'eaveZM' IN db.fields
WITH c,a,b,coalesce(a.unit='m' AND b.unit='m' AND a.geometryActive=true AND b.geometryActive=true AND ad=bd AND da.frameVersion=$version AND db.frameVersion=$version AND a.scenario=b.scenario AND c.scenario=a.scenario AND a.geometryVersion=$version AND b.geometryVersion=$version AND ar.geometryVersion=a.geometryVersion AND br.geometryVersion=b.geometryVersion AND c.inputGeometryVersion=ar.geometryVersion AND c.inputGeometryVersion=br.geometryVersion AND ar.expectedSourceVersion=sa.sourceVersion AND ar.expectedSourceVersion=asrc.sourceVersion AND br.expectedSourceVersion=sb.sourceVersion AND br.expectedSourceVersion=bsrc.sourceVersion AND a.eaveZM IS NOT NULL AND b.eaveZM IS NOT NULL,false) AS valid
RETURN c.uid AS uid,a.uid AS subject,b.uid AS reference,valid,CASE WHEN valid THEN a.eaveZM-b.eaveZM ELSE null END AS valueM,CASE WHEN valid THEN abs(c.valueM-(a.eaveZM-b.eaveZM))<1e-9 ELSE false END AS cacheAgreement;

// Q04_boundary
MATCH (c:V01 {uid:'V01:S05'})-[r:BOUNDARY_PARTICIPANT]->(p) RETURN c.uid AS courtyard,p.uid AS participant,p.name AS name,r.uid AS relationshipUid,r.boundaryId AS boundaryId,r.participantRole AS role,r.analysisSliceZM AS sliceZM,r.referenceLengthM AS lengthM,r.solidIntervalBoundsM AS intervals,r.netContributionM AS netContributionM ORDER BY boundaryId,participant;

// Q05_interfaces
MATCH (i:V01)-[r:INTERFACE_OF]->(p) WHERE i.uid IN ['V01:I04','V01:I05'] RETURN i.uid AS interface,p.uid AS participant,r.role AS role,r.uid AS relationshipUid,i.referenceMode AS referenceMode,i.relativePosition AS relativePosition,i.sideBoundaryMappingsJson AS sideMappings ORDER BY interface,role;

// Q06_outward_path
MATCH p=(a:V01 {uid:'V01:S06'})-[rs:DIRECT_ACCESS_TO*1..8]-(b:V01 {uid:'V01:S04'})
WHERE all(n IN nodes(p) WHERE n.uid IN $externalUids)
AND all(idx IN range(0,size(rs)-1) WHERE rs[idx].contextId='V01-walk-baseline' AND rs[idx].snapshot='V01-synthetic-T0' AND rs[idx].actor='正常成人步行（旧合成情境断言）' AND (startNode(rs[idx])=nodes(p)[idx] OR rs[idx].bidirectional=true))
RETURN [n IN nodes(p)|n.uid] AS nodes,[r IN rs|r.viaUid] AS via,size(rs) AS crossings ORDER BY crossings LIMIT 1;

// Q07_return_path
MATCH p=(a:V01 {uid:'V01:S04'})-[rs:DIRECT_ACCESS_TO*1..8]-(b:V01 {uid:'V01:S06'})
WHERE all(n IN nodes(p) WHERE n.uid IN $externalUids)
AND all(idx IN range(0,size(rs)-1) WHERE rs[idx].contextId='V01-walk-baseline' AND rs[idx].snapshot='V01-synthetic-T0' AND rs[idx].actor='正常成人步行（旧合成情境断言）' AND (startNode(rs[idx])=nodes(p)[idx] OR rs[idx].bidirectional=true))
RETURN [n IN nodes(p)|n.uid] AS nodes,[r IN rs|r.viaUid] AS via,size(rs) AS crossings ORDER BY crossings LIMIT 1;

// Q08_local_area_inputs
MATCH (u:V01 {uid:'V01:U01'}),(n:V01) WHERE n.uid IN ['V01:S04','V01:S05'] RETURN u.areaScopeId AS scopeId,u.areaScopePolygonXY AS scope,n.uid AS uid,n.footprintXY AS polygon,n.groundZM AS groundZM,n.geometryVersion AS geometryVersion ORDER BY uid;

// Q09_uses
MATCH (n:V01)-[r:HAS_SOURCE]->(src) WHERE n.uid IN $externalUids AND n.useState='known' AND all(f IN ['useState','useValues','useScope'] WHERE f IN r.fields) AND r.sourceVersion=src.sourceVersion UNWIND n.useValues AS use RETURN use,collect(DISTINCT n.uid) AS spaceUids,count(DISTINCT n.uid) AS spaceCount ORDER BY use;

// Q10_sources
MATCH (n:V01)-[r:HAS_SOURCE]->(s) WHERE n.uid IN $dimensionUids RETURN n.uid AS uid,s.uid AS source,r.fields AS fields,r.locator AS locator,r.sourceVersion AS sourceVersion,s.sourceVersion AS actualSourceVersion ORDER BY uid,source;

// Q11_roles_and_scope
MATCH (a:V01)-[r]->(b:V01) WHERE type(r) IN ['BOT_HAS_SPACE','BOT_HAS_BUILDING','MEMBER_OF_ZONE','PART_OF','PLAN_POSITION'] RETURN a.uid AS source,b.uid AS target,type(r) AS type,r.role AS role,r.scope AS scope ORDER BY type,source,target;

// Q12_no_duplicates
MATCH (n) RETURN count(CASE WHEN n.uid STARTS WITH 'D01V01:' OR n.uid STARTS WITH 'D03V01:' THEN 1 END) AS legacyActiveNodes,count(CASE WHEN n.uid='V01:S05' THEN 1 END) AS courtyardIdentity,count(CASE WHEN n.uid='V01:S01' THEN 1 END) AS hallIdentity;

// Q13_legacy_topology
MATCH (a:V01)-[r]->(b:V01) WHERE type(r) IN ['AXIS_JOINS','ENVELOPE_INTERSECTS','SHARES_BOUNDARY'] RETURN type(r) AS type,count(r) AS count ORDER BY type;

// Q14_facade_records
MATCH (o:V01)-[r:FACADE_PARTICIPANT]->(h:V01) RETURN o.uid AS owner,h.uid AS host,r.regionId AS regionId,r.role AS role,h.facadeRecordsJson AS localRecords,r.assertionLocator AS assertionLocator ORDER BY host;

// Q15_facade_openings
MATCH (i:V01)-[r:INTERFACE_OF]->(h:V01) WHERE h.uid IN ['V01:W03','V01:W10'] AND r.role='opening-host' RETURN h.uid AS host,i.uid AS opening,i.geometryJson AS geometry,r.uid AS relation ORDER BY host,opening;

// Q16_collection
MATCH (c:V01 {uid:'V01:CG01'})-[r:HAS_ANALYSIS_MEMBER]->(b:V01) OPTIONAL MATCH (u:V01)-[:BOT_HAS_BUILDING]->(b) RETURN c.uid AS collection,labels(c) AS collectionLabels,b.uid AS building,r.ordinal AS ordinal,r.role AS role,collect(u.uid) AS dwellingOwners,b.footprintXY AS footprint,b.groundZM AS groundZM,b.eaveZM AS eaveZM,b.ridgeZM AS ridgeZM ORDER BY ordinal;

// Q17_street_sides
MATCH (s:V01 {uid:'V01:ST01'})-[r:STREET_BOUNDARY_PARTICIPANT]->(p:V01) RETURN s.uid AS street,s.geometryJson AS geometry,p.uid AS participant,r.side AS side,r.role AS role,r.segmentsJson AS segments,r.geometryVersion AS version ORDER BY side;

// Q18_ground_reference
MATCH (b:V01)-[r:REFERENCES_GROUND]->(p:V01) RETURN b.uid AS building,p.uid AS profile,p.geometryJson AS geometry,p.groundState AS state,r.pointIndex AS pointIndex,r.objectPointField AS objectPointField,b.groundPointXYZ AS objectPoint ORDER BY building;

// Q19_explicit_local_pair
MATCH (i:V01 {uid:'V01:I05'})-[h:INTERFACE_OF {role:'opening-host'}]->(w:V01 {uid:'V01:W10'}),(i)-[s:INTERFACE_OF {role:'side-a'}]->(c:V01 {uid:'V01:S05'}),(o:V01)-[f:FACADE_PARTICIPANT]->(w) RETURN i.uid AS via,w.uid AS host,c.uid AS courtyard,o.uid AS owner,f.regionId AS localRegion,h.uid AS hostRelationship,s.uid AS courtyardRelationship;

// Q20_extension_sources
MATCH (n:V01)-[r:HAS_SOURCE]->(s:V01) WHERE r.id STARTS WITH 'X-SRC-' RETURN n.uid AS object,s.uid AS source,r.fields AS fields,r.locator AS locator,r.sourceVersion AS expectedVersion,s.sourceVersion AS actualVersion ORDER BY object;
