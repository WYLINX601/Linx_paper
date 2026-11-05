"""Construct an additive 2.2 candidate from the frozen, committed 2.1 source."""
from pathlib import Path
import copy,hashlib,json,sys
W=Path(__file__).parent;sys.path.insert(0,str(W/'tools'))
from semantics import ring,RULE,SPACE_IDS,REQUIRED_NEW
OLD='V01-unified-2.1';NEW='V01-unified-2.2'
raw=(W/'baseline/model-2.1.json').read_bytes();base=json.loads(raw);m=copy.deepcopy(base)
def upgrade(v):
 if isinstance(v,dict):return {k:upgrade(x) for k,x in v.items()}
 if isinstance(v,list):return [upgrade(x) for x in v]
 return NEW if v==OLD else v
m['modelVersion']=NEW;m['meta'].update(updated='2026-11-02',revision=NEW,previousSourceSha256=hashlib.sha256(raw).hexdigest())
m['analysisContract']=upgrade(m['analysisContract'])
m['prototypePolicy']['scope']='D01/D03/D04/D05/D06复用同一原型；基础关系局部定位和派生查询；D02内部构架继续暂停，D07暂缓、D08不纳入'
m['modelBoundary']['neo4jMapping']='唯一V01 JSON为维护主源；LPG与审核页为投影。当前执行以Neo4j/基础关系修订回执/verification.json为准；不是完整BOT/OWL推理。'
for row in m['nodes']+m['relationships']:row['properties']=upgrade(row['properties'])
N={n['id']:n for n in m['nodes']}
for sid in SPACE_IDS:
 n=N[sid];p=n['properties'];p.update(analysisSliceZM=1.,overallCoverType='enclosed-covered-space' if sid in ['S01','S02','S03'] else 'covered-open-sided-space' if sid=='S04' else 'open-air-space-character',coverStateMeaning='overall-space-character-not-zero-projection')
 if sid in ['S01','S02','S03']:p['coverState']='covered'
 p['boundaryBasis']='既有房间分析矩形，主体采用内侧净边界；S01南侧为开放理论分界。保持原几何，不声明完整净三维体。' if sid in ['S01','S02','S03'] else '前廊既有轴线/分界分析矩形，非统一净空间；墙端转角仅作几何候选，不新增持久边。' if sid=='S04' else '院内墙面及北侧开放分界构成的既有分析矩形；边段属性，不另建节点。' if sid=='S05' else '院门外出入分析裁切矩形；北界对应W10外表面，其余边为理论裁切线，不因无墙称未知或自动形成围合。'
 if sid!='S05':p['boundarySegments']=[{'id':bid,'polyline':xy,'state':'known','boundaryMeaning':'declared-analysis-boundary-not-physical-closure'} for bid,xy in ring(n).items()]
 else:p['boundaryCoverStateMeaning']='旧侧向性格/廊关联说明，不承诺该边每一点均有或没有顶盖；逐点顶盖另作RF01投影查询。'
 for f in ['boundaryBasis','analysisSliceZM','boundarySegments','overallCoverType','coverStateMeaning']:
  n.setdefault('propertyOrigins',{})[f]={'status':'research-working-interpretation-of-synthetic-geometry','ruleVersion':RULE,'source':'EV01','locator':f'/nodes/{m["nodes"].index(n)}/geometry'}
 src=next(r for r in m['relationships'] if r['id']=='SRC-'+sid);src['properties']['fields']=sorted(set(src['properties']['fields'])|{'coverState','boundaryBasis','analysisSliceZM','boundarySegments','overallCoverType','coverStateMeaning'}|({'boundaryCoverStateMeaning'} if sid=='S05' else set()))
for r in m['relationships']:
 if r['type']=='BOUNDARY_PARTICIPANT':
  p=r['properties'];p.update(localBoundaryIds=[p['boundaryId']] if r['source']=='S05' else list(ring(N[r['source']])),rangeState='localized-by-existing-geometry',analysisSliceZM=1.,geometryVersion=NEW,localRuleVersion=RULE,localRangeBasis='z=1m有限墙柱截面裁取本空间已声明边界；按宿主扣洞；重叠只在空间边段汇总中求并集')
for sid,tid in REQUIRED_NEW:
 p={'boundaryId':'S' if sid=='S04' else 'N','localBoundaryIds':['S' if sid=='S04' else 'N'],'participantRole':'column-section' if tid.startswith('C') else 'wall-boundary','participantKind':'column' if tid.startswith('C') else 'wall','rangeState':'localized-by-existing-geometry','analysisSliceZM':1.,'geometryVersion':NEW,'localRuleVersion':RULE,'semanticOrigin':'research-extension','scope':'前廊南界本侧柱截面，不复制院落侧范围' if sid=='S04' else '院门外侧北界W10局部；扣除I05后保留门洞两旁实体段','localRangeBasis':'本空间边界独立裁取；z=1m；扣宿主开口；不推受力、三维包含或通行'}
 m['relationships'].append({'id':'BOUND-'+sid+'-'+tid,'type':'BOUNDARY_PARTICIPANT','source':sid,'target':tid,'properties':p,'status':'synthetic_assignment','evidence':['EV01','EV02']})
for idx,r in enumerate(m['relationships']):
 p=r['properties'];p.update(assertionSourceUid='V01:EV01',assertionSourceVersion=NEW,assertionLocator='/relationships/'+str(idx))
 if r['id'] not in {old['id'] for old in base['relationships']}:
  p.update(sourceUid='V01:EV01',sourceVersion=NEW,locator='/relationships/'+str(idx))
  p.setdefault('evidenceRole','synthetic_assignment')
m['analysisContract']['basicRelations']={'ruleVersion':RULE,'spaceIds':SPACE_IDS,'persistentAdditions':[list(p) for p in REQUIRED_NEW],'sourceVersion':NEW,'sliceZM':1.,'roofProviderId':'RF01','interfaceId':'I04','streetReferencePair':['S06','ST01'],'queries':['具体空间有哪些局部墙柱参与及来源？','同一柱在前廊/院落两侧分别裁取哪段？','指定屋顶覆盖哪些空间及多少投影面积？','开放分界内哪些柱占用、平面剩余哪些段？','S06与哪个街段投影及层位对应？','每一对象哪些关系为必须/可选/不适用/未知？'],'candidateBoundaryPolicy':'S04与W04/W05墙端及W08/W09转角只列几何候选；不持久化语义边，不把残余自动当开放。','roofPolicy':'计算RF01投影与空间交集，不增加覆盖边或覆盖区节点；总体开敞不等于全域零覆盖。','interfacePolicy':'由两侧空间的边界参与裁取柱占用；不增I04柱宿主或通行边。','stoppingBoundary':'合成二维/切片复算及应用义务检查，不证明完整建筑语义、真实净空、受力或类型有效性。'}
assert [n['id'] for n in m['nodes']]==[n['id'] for n in base['nodes']]
m['analysisContract']['basicRelations']['objectSourceFields']={n['id']:sorted(n['properties']) for n in m['nodes'] if n['class'] not in ['Evidence','Source']}
m['analysisContract']['basicRelations']['memberTargets']={r['source']:r['target'] for r in base['relationships'] if r['type']=='MEMBER_OF_ZONE'}
local_fields={'localBoundaryIds','rangeState','analysisSliceZM','geometryVersion','localRuleVersion','localRangeBasis'}
for old in base['relationships']:
 cur=next(r for r in m['relationships'] if r['id']==old['id']);expected=upgrade(old)
 allowed=local_fields if old['type']=='BOUNDARY_PARTICIPANT' else {'fields'} if old['id'] in {'SRC-'+s for s in SPACE_IDS} else set()
 assert {k:v for k,v in cur.items() if k!='properties'}=={k:v for k,v in expected.items() if k!='properties'},old['id']
 assert {k:v for k,v in cur['properties'].items() if k not in allowed}=={k:v for k,v in expected['properties'].items() if k not in allowed},('Unapproved old relationship field change',old['id'])
assert all(n['geometry']==N[n['id']]['geometry'] for n in base['nodes'])
oldids={r['id'] for r in base['relationships']};newids=[r['id'] for r in m['relationships'] if r['id'] not in oldids]
assert len(newids)==len(REQUIRED_NEW)
for p,v in [('candidate/model.json',m),('candidate/fix-map.json',{'fromVersion':OLD,'toVersion':NEW,'preservedNodeIds':[n['id'] for n in base['nodes']],'preservedRelationshipIds':[r['id'] for r in base['relationships']],'newRelationshipIds':newids,'newNodeIds':[],'geometryChanged':False,'oldSourceSHA256':hashlib.sha256(raw).hexdigest(),'paperBeforeVersion':'V01-unified-2.0','publicationDebt':'2.1 was committed before Paper publication; merge pending 2.1 docs, do not replay old migration'})]:
 (W/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print('Candidate built',NEW,len(m['nodes']),len(m['relationships']),newids)
