// 研究分析路径与Cypher：基于2026-11-06读取的V01-unified-2.2
// 全部只读；参数已按当前版本内联。每次选择一组执行。
// 当前为合成演示，不是景宁真实样本结论；input-only查询尚需几何/分类后处理。

// C01 共同骨架 | 对象层级、构件成员与平面参照
// 模式：关系检索
// 边界：区域包含、构件成员、几何面归属和相对位置分开返回，不把成员关系说成三维包含。
MATCH (a:V01)-[r]->(b:V01) WHERE type(r) IN ['BOT_HAS_SPACE','BOT_HAS_BUILDING','MEMBER_OF_ZONE','PART_OF','PLAN_POSITION'] RETURN a.uid AS source,b.uid AS target,type(r) AS type,r.role AS role,r.scope AS scope ORDER BY type,source,target;

// C02 D01-T01/T02 | 面宽、进深、自身檐高和比例
// 模式：直接计算
// 边界：沿用各对象自己的量测边界；空值保持未知。不同对象的轴网与外包口径不能无条件混比。
MATCH (n:V01) WHERE n.uid IN ["V01:B01", "V01:B02", "V01:S01", "V01:S02", "V01:S03", "V01:S04", "V01:S05", "V01:S06"] RETURN n.uid AS uid,n.widthM AS widthM,n.depthM AS depthM,n.groundZM AS groundZM,n.eaveZM AS eaveZM,n.eaveZM-n.groundZM AS ownEaveHeightM,CASE WHEN n.depthM>0 THEN n.widthM/n.depthM ELSE null END AS widthDepthRatio,CASE WHEN n.widthM>0 THEN (n.eaveZM-n.groundZM)/n.widthM ELSE null END AS ownEaveHeightWidthRatio,n.measurementBoundaryBasis AS basis ORDER BY uid;

// C03 D01-T05 | 侧房减主屋的共同基准檐口高差
// 模式：带资格检查的直接计算
// 边界：核对来源支持字段、单位、共同基准、情境和版本；valid=false时拒绝计算。自身檐高与共同基准高差不同。
MATCH (c:V01 {uid:'V01:CMP01'})
OPTIONAL MATCH (c)-[ar:COMPARES_SUBJECT]->(a)
OPTIONAL MATCH (c)-[br:COMPARES_REFERENCE]->(b)
OPTIONAL MATCH (a)-[sa:HAS_SOURCE]->(asrc) WHERE sa.id=ar.sourceRelationId AND 'eaveZM' IN sa.fields
OPTIONAL MATCH (b)-[sb:HAS_SOURCE]->(bsrc) WHERE sb.id=br.sourceRelationId AND 'eaveZM' IN sb.fields
OPTIONAL MATCH (a)-[da:USES_DATUM]->(ad) WHERE 'eaveZM' IN da.fields
OPTIONAL MATCH (b)-[db:USES_DATUM]->(bd) WHERE 'eaveZM' IN db.fields
WITH c,a,b,coalesce(a.unit='m' AND b.unit='m' AND a.geometryActive=true AND b.geometryActive=true AND ad=bd AND da.frameVersion="V01-unified-2.2" AND db.frameVersion="V01-unified-2.2" AND a.scenario=b.scenario AND c.scenario=a.scenario AND a.geometryVersion="V01-unified-2.2" AND b.geometryVersion="V01-unified-2.2" AND ar.geometryVersion=a.geometryVersion AND br.geometryVersion=b.geometryVersion AND c.inputGeometryVersion=ar.geometryVersion AND c.inputGeometryVersion=br.geometryVersion AND ar.expectedSourceVersion=sa.sourceVersion AND ar.expectedSourceVersion=asrc.sourceVersion AND br.expectedSourceVersion=sb.sourceVersion AND br.expectedSourceVersion=bsrc.sourceVersion AND a.eaveZM IS NOT NULL AND b.eaveZM IS NOT NULL,false) AS valid
RETURN c.uid AS uid,a.uid AS subject,b.uid AS reference,valid,CASE WHEN valid THEN a.eaveZM-b.eaveZM ELSE null END AS valueM,CASE WHEN valid THEN abs(c.valueM-(a.eaveZM-b.eaveZM))<1e-9 ELSE false END AS cacheAgreement;

// C04 外部屋顶/原拓扑 | 外部屋顶系统与几何坡面的描述
// 模式：属性检索
// 边界：只读取既有外部屋顶与坡面属性，不恢复内部构架。坡面是GeometryRepresentation，不是物理屋顶构件。
MATCH (r:V01)
WHERE r:Roof OR r:RoofSurface
RETURN r.uid AS uid,r.name AS name,labels(r) AS labels,
       r.form AS form,r.slopeDeg AS slopeDeg,
       r.ridgeAzimuthDeg AS ridgeAzimuthDeg,
       r.overhangM AS overhangM,r.areaM2 AS areaM2
ORDER BY uid;

// C05 原拓扑 | 墙轴交接、墙柱包络相交、坡面共边
// 模式：既有关系检索
// 边界：使用有方向的存储端返回atSource/atTarget；这些限定几何关系不证明实体接触、受力或真实构造连接。
MATCH (a:V01)-[r:AXIS_JOINS|ENVELOPE_INTERSECTS|SHARES_BOUNDARY]->(b:V01)
RETURN a.uid AS source,b.uid AS target,type(r) AS relation,
       r.atSource AS atSource,r.atTarget AS atTarget,
       r.junctionXY AS junctionXY,r.intersectionKind AS intersectionKind,
       r.boundaryRole AS boundaryRole,r.ruleId AS ruleId
ORDER BY relation,source,target;

// C06 D03-T02 | 前院由哪些墙、柱和过渡空间参与界定
// 模式：分析输入提取
// 边界：返回边界参与和已登记区间；围合长度需要按同一切片求区间并集，不能在任意空间直接相加，不能将残余自动称开放。
MATCH (c:V01 {uid:'V01:S05'})-[r:BOUNDARY_PARTICIPANT]->(p) RETURN c.uid AS courtyard,p.uid AS participant,p.name AS name,r.uid AS relationshipUid,r.boundaryId AS boundaryId,r.participantRole AS role,r.analysisSliceZM AS sliceZM,r.referenceLengthM AS lengthM,r.solidIntervalBoundsM AS intervals,r.netContributionM AS netContributionM ORDER BY boundaryId,participant;

// C07 D03-T03 | 入口的两侧空间、宿主及相对位置
// 模式：关系与属性检索
// 边界：side-a/side-b是空间角色，opening-host是宿主角色；开口跨度不是已验证净通行宽度。
MATCH (i:V01)-[r:INTERFACE_OF]->(p) WHERE i.uid IN ['V01:I04','V01:I05'] RETURN i.uid AS interface,p.uid AS participant,r.role AS role,r.uid AS relationshipUid,i.referenceMode AS referenceMode,i.relativePosition AS relativePosition,i.sideBoundaryMappingsJson AS sideMappings ORDER BY interface,role;

// C08 D03-T04 | 院外参照经前院到前廊的路径
// 模式：已知子图路径计算
// 边界：限定三个外部空间、合成情境、快照、行动者与双向许可；最少跨界数不是步行距离，未验证真实净空。
MATCH p=(a:V01 {uid:'V01:S06'})-[rs:DIRECT_ACCESS_TO*1..8]-(b:V01 {uid:'V01:S04'})
WHERE all(n IN nodes(p) WHERE n.uid IN ["V01:S04", "V01:S05", "V01:S06"])
AND all(idx IN range(0,size(rs)-1) WHERE rs[idx].contextId='V01-walk-baseline' AND rs[idx].snapshot='V01-synthetic-T0' AND rs[idx].actor='正常成人步行（旧合成情境断言）' AND (startNode(rs[idx])=nodes(p)[idx] OR rs[idx].bidirectional=true))
RETURN [n IN nodes(p)|n.uid] AS nodes,[r IN rs|r.viaUid] AS via,size(rs) AS crossings ORDER BY crossings LIMIT 1;

// C09 D03-T05 | 局部面积窗口与空间轮廓
// 模式：分析输入提取
// 边界：返回U01声明窗口与S04/S05轮廓。面积并集、子集和层位检查由现有几何程序完成，不冒称全宅比例。
MATCH (u:V01 {uid:'V01:U01'}),(n:V01) WHERE n.uid IN ['V01:S04','V01:S05'] RETURN u.areaScopeId AS scopeId,u.areaScopePolygonXY AS scope,n.uid AS uid,n.footprintXY AS polygon,n.groundZM AS groundZM,n.geometryVersion AS geometryVersion ORDER BY uid;

// C10 D03-T06 | 有来源支持的空间用途分布
// 模式：分组计数
// 边界：只统计声明外部范围内useState=known且来源支持用途字段的对象；同一用途按空间UID去重。
MATCH (n:V01)-[r:HAS_SOURCE]->(src) WHERE n.uid IN ["V01:S04", "V01:S05", "V01:S06"] AND n.useState='known' AND all(f IN ['useState','useValues','useScope'] WHERE f IN r.fields) AND r.sourceVersion=src.sourceVersion UNWIND n.useValues AS use RETURN use,collect(DISTINCT n.uid) AS spaceUids,count(DISTINCT n.uid) AS spaceCount ORDER BY use;

// C11 D04-T01/T03/T04/T05/T06 | 局部立面、投影、材料分区及来源
// 模式：分析输入提取
// 边界：facadeRecordsJson是JSON字符串。此查询不计算扣洞净域或材料面积占比；色彩未启用、装饰未知，不记为无。
MATCH (o:V01)-[r:FACADE_PARTICIPANT]->(h:V01) RETURN o.uid AS owner,h.uid AS host,r.regionId AS regionId,r.role AS role,h.facadeRecordsJson AS localRecords,r.assertionLocator AS assertionLocator ORDER BY host;

// C12 D04-T02/D06-T03 | 指定局部的开口数量与描述性候选归类
// 模式：固定合成范围的计数与候选归类
// 边界：限W03北侧与W10南侧各一个已声明局部；计数宿主上的Interface而非窗格。CASE只对应现行开口数候选，不是地方立面型或完整配置归类；没有记录时不当作确定无开口。
MATCH (o:V01)-[f:FACADE_PARTICIPANT]->(w:V01:Wall)
WHERE w.uid IN ['V01:W03','V01:W10']
  AND f.geometryVersion='V01-unified-2.2'
OPTIONAL MATCH (i:V01:Interface)-[:INTERFACE_OF {role:'opening-host'}]->(w)
WITH o,w,f,count(DISTINCT i) AS openingCount
RETURN o.uid AS owner,w.uid AS host,f.regionId AS localRegion,
       openingCount,
       CASE WHEN openingCount=1 THEN 'single-opening-local'
            WHEN openingCount>=2 THEN 'multiple-openings-local'
            ELSE '需核对覆盖，不将未记录当作无' END AS candidate,
       'D06-local-candidate-0.1' AS ruleVersion
ORDER BY host;

// C13 D04/共同材料检索 | 材料标签按构件类别分别计数
// 模式：分组计数
// 边界：统计含材料标签的对象数，不是表层面积、体积或质量比例；多材料标签会重复落入不同材料组，不得相加为独立对象总数。
MATCH (e:V01:Element)
WITH e,CASE WHEN e:Wall THEN 'Wall' WHEN e:Column THEN 'Column'
            WHEN e:Roof THEN 'Roof' ELSE e.class END AS objectClass
UNWIND [label IN labels(e) WHERE label STARTS WITH '材质_'] AS material
RETURN objectClass,material,count(DISTINCT e) AS objectCount
ORDER BY objectClass,material;

// C14 D05-T01/T05、D06-T01 | 建筑组成员、归属与高程比较矩阵
// 模式：矩阵输入提取
// 边界：CG01是分析集合，不强作BOT Zone；B01/B02同属U01，不作为两个独立宅院。ordinal是声明成员顺序，不是几何可见轮廓。
MATCH (c:V01 {uid:'V01:CG01'})-[r:HAS_ANALYSIS_MEMBER]->(b:V01) OPTIONAL MATCH (u:V01)-[:BOT_HAS_BUILDING]->(b) RETURN c.uid AS collection,labels(c) AS collectionLabels,b.uid AS building,r.ordinal AS ordinal,r.role AS role,collect(u.uid) AS dwellingOwners,b.footprintXY AS footprint,b.groundZM AS groundZM,b.eaveZM AS eaveZM,b.ridgeZM AS ridgeZM ORDER BY ordinal;

// C15 D05-T03 | 街段两侧构成与局部里程
// 模式：分析输入提取
// 边界：返回指定街段左右侧和分段；连续界定比例、宽高序列须进一步复算，未知段不能当开敞。
MATCH (s:V01 {uid:'V01:ST01'})-[r:STREET_BOUNDARY_PARTICIPANT]->(p:V01) RETURN s.uid AS street,s.geometryJson AS geometry,p.uid AS participant,r.side AS side,r.role AS role,r.segmentsJson AS segments,r.geometryVersion AS version ORDER BY side;

// C16 D05-T04 | 建筑与独立地面剖面的对应
// 模式：分析输入提取
// 边界：返回地表样点及对象对应点；不是用屋顶高差代替地形，也不据此说明适应动机或入口净通行。
MATCH (b:V01)-[r:REFERENCES_GROUND]->(p:V01) RETURN b.uid AS building,p.uid AS profile,p.geometryJson AS geometry,p.groundState AS state,r.pointIndex AS pointIndex,r.objectPointField AS objectPointField,b.groundPointXYZ AS objectPoint ORDER BY building;

// C17 D06-T02/T05 | 院墙局部—院门—前院的显式配对
// 模式：跨维度关系检索
// 边界：仅W10—I05—S05有明确配对；不把北墙与前院任意组合，不自动汇总整栋频数或推出文化因果。
MATCH (i:V01 {uid:'V01:I05'})-[h:INTERFACE_OF {role:'opening-host'}]->(w:V01 {uid:'V01:W10'}),(i)-[s:INTERFACE_OF {role:'side-a'}]->(c:V01 {uid:'V01:S05'}),(o:V01)-[f:FACADE_PARTICIPANT]->(w) RETURN i.uid AS via,w.uid AS host,c.uid AS courtyard,o.uid AS owner,f.regionId AS localRegion,h.uid AS hostRelationship,s.uid AS courtyardRelationship;

// C18 全部模块/证据追溯 | 关键属性的来源、字段支持范围和版本
// 模式：来源检索
// 边界：一条HAS_SOURCE只支持fields所列字段；当前来源是合成来源。未来真实文献需作者、题名、Zotero与页码，不能虚构这些字段。
MATCH (n:V01)-[r:HAS_SOURCE]->(s:V01)
WHERE n.uid IN ['V01:B01','V01:B02','V01:S04','V01:S05','V01:W03','V01:W10']
RETURN n.uid AS object,s.uid AS source,s.name AS sourceName,
       r.fields AS fields,r.locator AS locator,
       r.sourceVersion AS expectedVersion,s.sourceVersion AS actualVersion,
       s.isRealWorldEvidence AS isRealWorldEvidence
ORDER BY object,source,locator;

// C19 完整性/未知检查 | 哪些界面的另一侧空间尚未实例化
// 模式：质量检查
// 边界：单侧未实例化是已知资料边界，不直接称建模错误，也不据缺边认定该空间不存在。
MATCH (i:V01:Interface)
OPTIONAL MATCH (i)-[r:INTERFACE_OF]->(s:V01:Space)
WHERE r.role IN ['side-a','side-b']
WITH i,count(DISTINCT s) AS knownSides
WHERE knownSides<2
RETURN i.uid AS interface,i.name AS name,knownSides,
       '另一侧未实例化，不等于不存在或建模错误' AS meaning
ORDER BY interface;

// C20 D03/基础关系审03 | 指定屋顶覆盖各空间的复算输入
// 模式：分析输入提取
// 边界：返回各空间与指定RF01的实际几何。投影交集由几何程序计算；没有覆盖边并不表示没有覆盖。
MATCH (s:V01:Space),(r:V01 {uid:'V01:RF01'}) RETURN s.uid AS space,s.geometryJson AS spaceGeometry,s.overallCoverType AS overallType,s.coverStateMeaning AS coverMeaning,r.uid AS provider,r.geometryJson AS roofGeometry,s.geometryVersion AS spaceVersion,r.geometryVersion AS roofVersion ORDER BY space;

// C21 D03/基础关系审04 | 开放分界经两侧空间定位柱占用
// 模式：多跳输入提取
// 边界：通过INTERFACE_OF→BOUNDARY_PARTICIPANT取几何，不强造I04柱宿主。结果含两侧各一次记录，几何计算需按同一柱UID去重并裁切；平面剩余不是已验证净通行。
MATCH (i:V01 {uid:'V01:I04'})-[a:INTERFACE_OF]->(s:Space)-[b:BOUNDARY_PARTICIPANT]->(c:Column) WHERE a.role IN ['side-a','side-b'] RETURN i.uid AS interface,s.uid AS side,c.uid AS column,i.geometryJson AS interfaceGeometry,c.geometryJson AS columnGeometry,b.uid AS boundaryRelationship ORDER BY side,column;

// C22 D05/基础关系审06 | 院外参照区与街段的空间对应输入
// 模式：分析输入提取
// 边界：S06与ST01保留不同身份；投影及层位对应不等于已存包含边或已证通行。
MATCH (s:V01 {uid:'V01:S06'}),(t:V01 {uid:'V01:ST01'}) RETURN s.uid AS space,t.uid AS street,labels(s) AS spaceLabels,labels(t) AS referenceLabels,s.geometryJson AS spaceGeometry,t.geometryJson AS streetGeometry,s.groundZM AS spaceLevel,s.geometryVersion AS spaceVersion,t.geometryVersion AS streetVersion;
