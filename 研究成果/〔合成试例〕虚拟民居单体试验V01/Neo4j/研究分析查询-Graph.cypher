// V01研究分析查询：Graph返回版
// 2026-11-06；全部只读。逐组执行，不替换原Q01—Q26审核主源。
// 返回原生节点／关系／路径，切换Neo4j Browser的Graph视图查看。
// C20/C22不返回直接关系；不得为画线伪造覆盖／包含／通行。

// C01 对象层级、构件成员与平面参照
// 图中呈现实际登记的组织与位置关系，不把成员归属升格为三维包含。
MATCH (a:V01)-[r]->(b:V01)
WHERE type(r) IN ['BOT_HAS_SPACE','BOT_HAS_BUILDING','MEMBER_OF_ZONE','PART_OF','PLAN_POSITION']
RETURN a AS anchor,r AS relation,b AS neighbor,null AS path;

// C02 面宽、进深、自身檐高和比例
// 显示量测对象及来源／基准背景；比例和自身檐高仍从Table版读取，不为普通尺寸另造节点。
MATCH (n:V01)
WHERE n.uid IN ['V01:B01','V01:B02','V01:S01','V01:S02','V01:S03','V01:S04','V01:S05','V01:S06']
OPTIONAL MATCH (n)-[r:HAS_SOURCE|USES_DATUM]->(ref:V01)
RETURN n AS anchor,r AS relation,ref,null AS path;

// C03 侧房减主屋的共同基准檐口高差
// 保留Table版的来源／基准／版本资格检查，显示比较结果节点及实际角色关系，不增HIGHER_THAN边。
MATCH (c:V01 {uid:'V01:CMP01'})
OPTIONAL MATCH (c)-[ar:COMPARES_SUBJECT]->(a)
OPTIONAL MATCH (c)-[br:COMPARES_REFERENCE]->(b)
OPTIONAL MATCH (a)-[sa:HAS_SOURCE]->(asrc) WHERE sa.id=ar.sourceRelationId AND 'eaveZM' IN sa.fields
OPTIONAL MATCH (b)-[sb:HAS_SOURCE]->(bsrc) WHERE sb.id=br.sourceRelationId AND 'eaveZM' IN sb.fields
OPTIONAL MATCH (a)-[da:USES_DATUM]->(ad) WHERE 'eaveZM' IN da.fields
OPTIONAL MATCH (b)-[db:USES_DATUM]->(bd) WHERE 'eaveZM' IN db.fields
WITH c,a,b,ar,br,sa,sb,asrc,bsrc,da,db,ad,bd,coalesce(a.unit='m' AND b.unit='m' AND a.geometryActive=true AND b.geometryActive=true AND ad=bd AND da.frameVersion="V01-unified-2.2" AND db.frameVersion="V01-unified-2.2" AND a.scenario=b.scenario AND c.scenario=a.scenario AND a.geometryVersion="V01-unified-2.2" AND b.geometryVersion="V01-unified-2.2" AND ar.geometryVersion=a.geometryVersion AND br.geometryVersion=b.geometryVersion AND c.inputGeometryVersion=ar.geometryVersion AND c.inputGeometryVersion=br.geometryVersion AND ar.expectedSourceVersion=sa.sourceVersion AND ar.expectedSourceVersion=asrc.sourceVersion AND br.expectedSourceVersion=sb.sourceVersion AND br.expectedSourceVersion=bsrc.sourceVersion AND a.eaveZM IS NOT NULL AND b.eaveZM IS NOT NULL,false) AS valid
RETURN c AS anchor,ar AS relation,a,br,b,sa,asrc,sb,bsrc,da,ad,db,bd,
       null AS path,valid,
       CASE WHEN valid THEN a.eaveZM-b.eaveZM ELSE null END AS valueM,
       CASE WHEN valid THEN abs(c.valueM-(a.eaveZM-b.eaveZM))<1e-9 ELSE false END AS cacheAgreement;

// C04 外部屋顶系统与几何坡面的描述
// 屋顶系统与几何坡面保持不同身份，只显示已存在的归属边。
MATCH (g:V01)
WHERE g:Roof OR g:RoofSurface
OPTIONAL MATCH (g)-[r:PART_OF|MEMBER_OF_ZONE]->(owner:V01)
RETURN g AS anchor,r AS relation,owner,null AS path;

// C05 墙轴交接、墙柱包络相交、坡面共边
// 图中显示原限定几何关系；边的几何字段可点击查看，不升级为受力或构造连接。
MATCH (a:V01)-[r:AXIS_JOINS|ENVELOPE_INTERSECTS|SHARES_BOUNDARY]->(b:V01)
RETURN a AS anchor,r AS relation,b AS neighbor,null AS path;

// C06 前院由哪些墙、柱和过渡空间参与界定
// 前院的边界参与网络，不是围合长度的并集计算结果。
MATCH (s:V01 {uid:'V01:S05'})-[r:BOUNDARY_PARTICIPANT]->(p:V01)
RETURN s AS anchor,r AS relation,p AS participant,null AS path;

// C07 入口的两侧空间、宿主及相对位置
// 显示两侧空间与宿主角色；点击边查看role，不能把宿主和空间侧混同。
MATCH (i:V01)-[r:INTERFACE_OF]->(p:V01)
WHERE i.uid IN ['V01:I04','V01:I05']
RETURN i AS anchor,r AS relation,p AS participant,null AS path;

// C08 院外参照经前院到前廊的路径
// 返回原生PATH；保留三个外部空间、情境、快照、行动者及双向许可。Graph为最少跨界路径，不是步行净空验证。
MATCH p=(a:V01 {uid:'V01:S06'})-[rs:DIRECT_ACCESS_TO*1..8]-(b:V01 {uid:'V01:S04'})
WHERE all(n IN nodes(p) WHERE n.uid IN ["V01:S04", "V01:S05", "V01:S06"])
AND all(idx IN range(0,size(rs)-1) WHERE rs[idx].contextId='V01-walk-baseline' AND rs[idx].snapshot='V01-synthetic-T0' AND rs[idx].actor='正常成人步行（旧合成情境断言）' AND (startNode(rs[idx])=nodes(p)[idx] OR rs[idx].bidirectional=true))
RETURN a AS anchor,null AS relation,p AS path,size(rs) AS crossings
ORDER BY crossings LIMIT 1;

// C09 局部面积窗口与空间轮廓
// 仅显示局部分析窗所属对象与空间的实际层级背景；图上的包含路径不代表面积比例已经计算。
MATCH (u:V01 {uid:'V01:U01'}),(n:V01)
WHERE n.uid IN ['V01:S04','V01:S05']
OPTIONAL MATCH p=(u)-[:BOT_HAS_BUILDING|BOT_HAS_SPACE*1..2]->(n)
RETURN u AS anchor,null AS relation,n,p AS path;

// C10 有来源支持的空间用途分布
// 用途是空间属性；Graph显示有据用途的空间与来源，不为每个用途字符串虚构节点。频数看Table版。
MATCH (n:V01)-[r:HAS_SOURCE]->(src:V01)
WHERE n.uid IN ['V01:S04','V01:S05','V01:S06']
  AND n.useState='known'
  AND all(f IN ['useState','useValues','useScope'] WHERE f IN r.fields)
  AND r.sourceVersion=src.sourceVersion
RETURN n AS anchor,r AS relation,src,null AS path,n.useValues AS useValues;

// C11 局部立面、投影、材料分区及来源
// 局部立面保存在墙的JSON属性中；Graph显示所有者与宿主，不把局部记录编号冒充独立实体。
MATCH (o:V01)-[r:FACADE_PARTICIPANT]->(h:V01)
RETURN o AS anchor,r AS relation,h AS host,null AS path,h.facadeRecordsJson AS localRecords;

// C12 指定局部的开口数量与描述性候选归类
// 显示指定墙面与每个开口；候选类型是返回的派生标量，不创建类型节点。因展开开口，Graph返回行数与Table版不同。
MATCH (o:V01)-[f:FACADE_PARTICIPANT]->(w:V01:Wall)
WHERE w.uid IN ['V01:W03','V01:W10']
  AND f.geometryVersion='V01-unified-2.2'
OPTIONAL MATCH (i:V01:Interface)-[:INTERFACE_OF {role:'opening-host'}]->(w)
WITH o,w,f,count(DISTINCT i) AS openingCount
OPTIONAL MATCH (opening:V01:Interface)-[hostRel:INTERFACE_OF {role:'opening-host'}]->(w)
RETURN o AS anchor,f AS relation,w,opening,hostRel,null AS path,openingCount,
       CASE WHEN openingCount=1 THEN 'single-opening-local'
            WHEN openingCount>=2 THEN 'multiple-openings-local'
            ELSE '需核对覆盖，不将未记录当作无' END AS candidate,
       'D06-local-candidate-0.1' AS ruleVersion;

// C13 材料标签按构件类别分别计数
// 材料仍是用户选定的标签方案；Graph显示含材料标签的构件及已有归属，不画不存在的Material节点／材料关系。
MATCH (e:V01:Element)
WHERE any(label IN labels(e) WHERE label STARTS WITH '材质_')
OPTIONAL MATCH (e)-[r:MEMBER_OF_ZONE]->(owner:V01)
RETURN e AS anchor,r AS relation,owner,null AS path,
       [label IN labels(e) WHERE label STARTS WITH '材质_'] AS materialLabels;

// C14 建筑组成员、归属与高程比较矩阵
// 显示分析集合及实际宅院归属；B03无U01归属仍保留，B01/B02不能被当作两个独立宅院。
MATCH (c:V01 {uid:'V01:CG01'})-[r:HAS_ANALYSIS_MEMBER]->(b:V01)
OPTIONAL MATCH (u:V01)-[ownerRel:BOT_HAS_BUILDING]->(b)
RETURN c AS anchor,r AS relation,b,u,ownerRel,null AS path;

// C15 街段两侧构成与局部里程
// 图中为街段左右侧参与网络；side、segmentsJson及计算所需几何在属性里。
MATCH (s:V01 {uid:'V01:ST01'})-[r:STREET_BOUNDARY_PARTICIPANT]->(p:V01)
RETURN s AS anchor,r AS relation,p AS participant,null AS path;

// C16 建筑与独立地面剖面的对应
// 显示建筑与地面剖面的实际引用；不是地形适应动机、坡面几何或净通行的结论图。
MATCH (b:V01)-[r:REFERENCES_GROUND]->(p:V01)
RETURN b AS anchor,r AS relation,p AS profile,null AS path;

// C17 院墙局部—院门—前院的显式配对
// 保留院墙—院门—前院的明确局部配对；没有任意立面与院落的笛卡尔组合，也不创造新的配对边。
MATCH (i:V01 {uid:'V01:I05'})-[h:INTERFACE_OF {role:'opening-host'}]->(w:V01 {uid:'V01:W10'}),
      (i)-[s:INTERFACE_OF {role:'side-a'}]->(c:V01 {uid:'V01:S05'}),
      (o:V01)-[f:FACADE_PARTICIPANT]->(w)
RETURN i AS anchor,h AS relation,w,s,c,o,f,null AS path;

// C18 关键属性的来源、字段支持范围和版本
// Graph查看对象与来源，支持哪些字段／定位／版本仍在HAS_SOURCE边属性中，不把同源资料当独立互证。
MATCH (n:V01)-[r:HAS_SOURCE]->(s:V01)
WHERE n.uid IN ['V01:B01','V01:B02','V01:S04','V01:S05','V01:W03','V01:W10']
RETURN n AS anchor,r AS relation,s AS source,null AS path;

// C19 哪些界面的另一侧空间尚未实例化
// 只显示另一侧尚未实例化界面的已知参与网络；不会补造“未知空间”节点或把缺边当不存在。
MATCH (i:V01:Interface)
OPTIONAL MATCH (i)-[sideRel:INTERFACE_OF]->(space:V01:Space)
WHERE sideRel.role IN ['side-a','side-b']
WITH i,count(DISTINCT space) AS knownSides
WHERE knownSides<2
OPTIONAL MATCH (i)-[r:INTERFACE_OF]->(participant:V01)
RETURN i AS anchor,r AS relation,participant,null AS path,knownSides;

// C20 指定屋顶覆盖各空间的复算输入
// 仅返回待求交的空间与指定屋顶节点，查询未返回覆盖边，可能显示孤立节点。当前覆盖为几何派生，不能为画线伪造已存覆盖关系。
MATCH (s:V01:Space),(roof:V01 {uid:'V01:RF01'})
RETURN s AS anchor,null AS relation,roof,null AS path;

// C21 开放分界经两侧空间定位柱占用
// 返回界面→两侧空间→柱的原生PATH。柱在两侧的路径不是两根柱；几何占用须按UID去重并裁切。
MATCH p=(i:V01 {uid:'V01:I04'})-[a:INTERFACE_OF]->(s:V01:Space)-[b:BOUNDARY_PARTICIPANT]->(c:V01:Column)
WHERE a.role IN ['side-a','side-b']
RETURN i AS anchor,null AS relation,p AS path;

// C22 院外参照区与街段的空间对应输入
// 只返回S06与ST01两节点，没有直接关系是当前模型的真实状态。投影／层位对应须复算，不强加包含或通行线。
MATCH (s:V01 {uid:'V01:S06'}),(street:V01 {uid:'V01:ST01'})
RETURN s AS anchor,null AS relation,street,null AS path;
