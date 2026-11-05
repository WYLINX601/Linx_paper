"""Build explicitly synthetic D03 external-scope extension; never infer real facts."""
import copy,json
from workspace import W,CASE,candidate
m=json.loads((W/'originals'/CASE/'案例模型.json').read_text())
m['modelVersion']='1.1'
m['purpose']='D03-T01—T06当前外部范围的逐项表达与合成检验；不是室内完整化或真实样本验证'
m['authorization']='2026-10-30用户审核通过首例，并授权完整D03拆解、一并更新既有审核视图。新增实施细节仍待本轮审核。'
m['review']={'firstExample':'user-approved-limited-synthetic-expression','firstExampleQuote':'可以，审核通过','scopeQuote':'可以，我觉得拆解没问题，我们可以继续了，完整D03所有的拆解吧，一并更新到D03的审核视图.html中','extension':'new-details-awaiting-user-review','empiricalValidity':'not-validated'}
m['classificationScheme']['status']='user-approved-working-rule-limited-synthetic-scope'
m['scope']['implemented']=['D03-T01外部空间、层位、边界与缺失','D03-T02逐段参与、开放、覆盖与限定净实体长度比','D03-T03入口身份、角色、唯一参照里程与未知另一侧','D03-T04有显式情境证据的外部局部有向通行与已知子图路径','D03-T05同层二维轮廓、面积集合去重、声明分母与几何位置比较','D03-T06有字段来源的合成多用途、未知与空间去重','D06限定围合分型与同型变体接口']
m['scope']['notImplemented']=[x for x in m['scope']['notImplemented'] if x!='D03完整六项']
m['basis'][2]['items']=['D03-T%02d'%i for i in range(1,7)]
def ring(x0,y0,x1,y1):return [[float(x0),float(y0)],[float(x1),float(y0)],[float(x1),float(y1)],[float(x0),float(y1)],[float(x0),float(y0)]]
def obj(id,name,labels,poly=None,**p):
    if poly is not None:p.update(polygon=poly,geometryVersion='E-1.0',geometryComplete=True,geometryBasis='same-level-plan-analysis-footprint',coordinateFrame='E-local-xy',unit='m',level='E-ground',floorZM=0.0)
    return {'id':id,'name':name,'labels':labels,**p}
objects=[
obj('E-U01','E例外部宅院分析范围',['Zone','DwellingUnit'],ring(0,0,16,16),boundaryBasis='人工声明分析用地；不是产权或实测地籍',axisXY=[0.0,1.0],axisBasis='从入口向院内的人工参照正方向；不推社会位序',networkCoverage='partial-external-known-subgraph'),
obj('E-C01','E例前部院落',['Zone','Space','Courtyard'],ring(2,2,10,8),spaceKind='courtyard',coverState='uncovered',boundaryBasis='按平面围合与开放理论划界人工声明',useState='known',useValues=['晾晒','临时停留'],useContext='人工日常情境E-use-1；非田野观察',useEvidenceRole='synthetic-assignment',useScope='this-space',useLocator='/externalExtension/objects/1/useValues'),
obj('E-C02','E例后部院落',['Zone','Space','Courtyard'],ring(2,10,10,14),spaceKind='courtyard',coverState='uncovered',boundaryBasis='按平面围合与开放理论划界人工声明',useState='unknown',useValues=[],useContext='本合成例未声明用途',useEvidenceRole='synthetic-assignment',useScope='this-space',useLocator='/externalExtension/objects/2/useValues'),
obj('E-G01','E例有盖开放过渡廊',['Zone','Space','ExternalTransition'],ring(2,8,10,10),spaceKind='covered-transition',coverState='covered-open-sided',boundaryBasis='人工划定外部有盖空间；不等于封闭室内',useState='known',useValues=['通行','临时停留'],useContext='人工日常情境E-use-1；非田野观察',useEvidenceRole='synthetic-assignment',useScope='this-space',useLocator='/externalExtension/objects/3/useValues'),
obj('E-P01','E例入口平台',['Zone','Space','ExternalTransition'],ring(2,0,10,2),spaceKind='entry-platform',coverState='uncovered',boundaryBasis='入口前平台的理论分析范围',useState='unknown',useValues=[],useContext='未从平台形状推断用途',useEvidenceRole='synthetic-assignment',useScope='this-space',useLocator='/externalExtension/objects/4/useValues'),
obj('E-B01','E例东侧建筑',['Zone','Building'],ring(10,2,14,14),boundaryBasis='建筑地面外包投影；不记录室内隔间'),
obj('E-B02','E例北侧建筑',['Zone','Building'],ring(2,14,10,16),boundaryBasis='建筑地面外包投影；不记录室内隔间'),
obj('E-W01','E例南侧院墙',['Element','Wall'],boundaryBasis='地面分析层位上的院墙载体；不据此断言承重',geometryVersion='E-1.0')]
def seg(id,coords,kind,participant,solid,cover='uncovered'):
    return {'id':id,'polyline':coords,'kind':kind,'state':'known','participantId':participant,'solidIntervalsM':solid,'solidState':'known','coverState':cover,'basis':'声明分析层位上的线段；实体段扣入口，廊盖不计实体围合；无三维闭合含义'}
boundaries={
'E-C01':[seg('N',[[2.,8.],[10.,8.]],'covered-transition','E-G01',[], 'covered-open-sided'),seg('E',[[10.,8.],[10.,2.]],'building','E-B01',[[0.,6.]]),seg('S',[[10.,2.],[2.,2.]],'wall','E-W01',[[0.,3.],[5.,8.]]),seg('W',[[2.,2.],[2.,8.]],'open',None,[])],
'E-C02':[seg('N',[[2.,14.],[10.,14.]],'building','E-B02',[[0.,8.]]),seg('E',[[10.,14.],[10.,10.]],'building','E-B01',[[0.,4.]]),seg('S',[[10.,10.],[2.,10.]],'covered-transition','E-G01',[],'covered-open-sided'),seg('W',[[2.,10.],[2.,14.]],'open',None,[])]}
for o in objects:
    if o['id'] in boundaries:o['boundaries']=boundaries[o['id']]
entrances=[]
for id,name,c,b,s,e,a,z,host in [('E-I01','E例院门','E-C01','S',3.,5.,'E-P01','E-C01','E-W01'),('E-I02','E例院落—廊开放分界','E-C01','N',2.,4.,'E-C01','E-G01',None),('E-I03','E例廊—后院开放分界','E-C02','S',3.,5.,'E-G01','E-C02',None),('E-I04','E例后院西侧局部入口线索','E-C02','W',1.,2.,'E-C02',None,None)]:
    entrances.append({'id':id,'name':name,'referenceSpaceId':c,'referenceBoundaryId':b,'referenceGeometryVersion':'E-1.0','startChainageM':s,'endChainageM':e,'correspondence':'unique-on-reference-line','fromSpaceId':a,'toSpaceId':z,'hostId':host,'farSideState':'known' if z else 'unknown','unit':'m','level':'E-ground','clearWidthM':e-s,'clearHeightState':'known' if z else 'unknown',**({'clearHeightM':2.1,'stepHeightM':0.0} if z else {}),'geometryBasis':'人工界面分析范围；不将净宽高换算为普适可通行阈值'})
access=[]
for via,a,b in [('E-I01','E-P01','E-C01'),('E-I01','E-C01','E-P01'),('E-I02','E-C01','E-G01'),('E-I02','E-G01','E-C01'),('E-I03','E-G01','E-C02')]:
    access.append({'id':'ACCESS-'+a+'-'+b,'from':a,'to':b,'via':via,'contextId':'E-walk-1','actor':'正常成人步行（人工情境）','doorState':'无门扇阻挡（人工声明）','obstacleState':'该方向已确认无障碍（人工声明）','observationTime':'synthetic-snapshot-E-1','state':'passable-asserted','evidenceRole':'synthetic-explicit-passage-assertion','reversePolicy':'仅存明确方向；缺少反向记录不等于反向不可达'})
m['externalExtension']={'id':'E','name':'双院落—外部过渡—局部通行与用途','version':'E-1.0','source':{'id':'EV02','name':'D03外部六项合成设定','sourceVersion':'E-1.0','sourceKind':'synthetic-not-observation','sourcePath':m['authoritativePath'],'creator':'研究协作过程人工试例设计','supportScope':'仅说明E例假设及预期计算；不支持真实通行、用途、地方类型或文化解释'},'objects':objects,'entrances':entrances,'access':access,'rules':{'id':'R02','version':'D03-external-1.0','name':'D03外部六项操作规则','geometry':'二维简单有效多边形；同一层位、坐标系、米制；未定尺度不算面积。集合并集去重，子集检查后除完整声明范围。','enclosure':'只按声明层位的逐段实体线长；扣门洞，开放廊不因有盖计为实体。未知时停算全周比。','entry':'唯一同一折线参照，中心为起止里程均值；不使用弦中点。','access':'仅有证据的同情境、明确方向、完整两端与via；最少跨界次数限已知外部子图，不是步行距离或全宅最短。','use':'用途原值归空间，多值不重复计空间；类型层主张不得赋予具名空间。','classification':'E例含过渡廊，不套R01四侧类别；不自动新增地方类型。'},'comparisons':[{'id':'POS-E-C02-E-C01','subject':'E-C02','reference':'E-C01','axisFrom':'E-U01','meaning':'几何中心沿入口向内参照的位移；不是社会位序或通行串联'}],'pathRequests':[{'from':'E-P01','to':'E-C02','contextId':'E-walk-1'},{'from':'E-C02','to':'E-P01','contextId':'E-walk-1'}],'typeLevelClaims':[{'text':'仅类型层的用途线索不能分配给具体空间','evidenceRole':'synthetic-counterexample-not-literature','appliesTo':'type-only','assignedToInstance':False}]}
objects[0].update(passageContextId='E-walk-1',passageActor='正常成人步行（人工情境）',passageSnapshot='synthetic-snapshot-E-1')
p=candidate(CASE+'/案例模型.json',json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print(p)
