"""Analyze actual readback records; synthetic results, not empirical findings."""
import collections,copy,json,math
from shapely.geometry import Polygon
from shapely.ops import unary_union
from compile_model import VERSION,PREFIX,merge_intervals,pair,require,boundary_qualification

def qualified_dimension(n,relationships,N,fields):
 p=n['properties'];uid=p['uid'];issues=[]
 if p.get('unit')!='m':issues.append('unit-not-m')
 if p.get('geometryActive') is not True:issues.append('geometry-not-active')
 if p.get('geometryVersion')!=VERSION:issues.append('geometry-version')
 if p.get('scenario')!='V01-T0':issues.append('scenario')
 for f in fields:
  if type(p.get(f)) not in (int,float) or not math.isfinite(p[f]):issues.append('missing-or-invalid-'+f)
  elif f in ('widthM','depthM') and p[f]<=0:issues.append('nonpositive-'+f)
  src=[]
  for r in relationships:
   q=r['properties']
   if r['type']=='HAS_SOURCE' and r['source']==uid and f in q.get('fields',[]):
    s=N.get(r['target'],{}).get('properties',{})
    if q.get('sourceVersion')==s.get('sourceVersion') and q.get('locator','').startswith('/nodes/') and s.get('sourceKind') in ('synthetic_assignment','archived_synthetic_assignment'):src.append(r)
  if not src:issues.append('unsupported-'+f)
 datums=[r for r in relationships if r['type']=='USES_DATUM' and r['source']==uid and set(fields)<=set(r['properties'].get('fields',[])) and r['properties'].get('frameVersion')==VERSION]
 if len(datums)!=1:issues.append('datum-ambiguous-or-missing')
 return issues,datums[0]['target'] if len(datums)==1 else None

def analyze(graph,extensions=True):
 from projection import rehydrate,validate_extension_sources
 N={n['properties']['uid']:n for n in graph['nodes']};R=sorted(graph['relationships'],key=lambda r:r['properties']['uid']);M=rehydrate(graph);contract=M['analysisContract'];result={'version':VERSION,'sourceModelSha256':N['V01:SOURCE']['properties']['sourceModelSha256'],'evidenceStatus':'synthetic-only','D01':{},'D03':{}}
 dims=[]
 for id in contract['D01']['objects']:
  n=N[PREFIX+id];p=n['properties'];fields=['widthM','depthM','groundZM']+(['eaveZM','ridgeZM'] if 'Building' in n['labels'] else [])
  issues,datum=qualified_dimension(n,R,N,fields);q={'uid':PREFIX+id,'name':p['name'],'status':'invalid-input' if issues else 'computed-synthetic','issues':issues,'datum':datum,'widthM':p.get('widthM'),'depthM':p.get('depthM'),'basis':p['measurementBoundaryBasis'],'groundZM':p.get('groundZM')}
  if not issues:
   q['widthDepthRatio']=p['widthM']/p['depthM']
   if 'Building' in n['labels']:q.update(eaveElevationM=p['eaveZM'],ownEaveHeightM=p['eaveZM']-p['groundZM'],ownRidgeHeightM=p['ridgeZM']-p['groundZM'],ownEaveHeightWidthRatio=(p['eaveZM']-p['groundZM'])/p['widthM'])
  dims.append(q)
 result['D01']['dimensions']=dims
 cmp=N['V01:CMP01']['properties'];inputs={r['type']:r for r in R if r['source']=='V01:CMP01' and r['type'] in ['COMPARES_SUBJECT','COMPARES_REFERENCE']};issues=[];datums=[];values=[]
 for role in ['COMPARES_SUBJECT','COMPARES_REFERENCE']:
  r=inputs.get(role)
  if not r:issues.append('missing-'+role);continue
  n=N[r['target']];p=n['properties'];q=r['properties'];err,datum=qualified_dimension(n,R,N,['eaveZM']);issues+=err;datums.append(datum)
  bindings=[s for s in R if s['source']==r['target'] and s['type']=='HAS_SOURCE' and s['properties'].get('id')==q['sourceRelationId'] and 'eaveZM' in s['properties'].get('fields',[])]
  if len(bindings)!=1:issues.append('comparison-source-binding')
  elif q.get('expectedSourceVersion')!=bindings[0]['properties'].get('sourceVersion') or q.get('expectedSourceVersion')!=N[bindings[0]['target']]['properties'].get('sourceVersion'):issues.append('pinned-source-version-mismatch')
  if cmp.get('scenario')!=p.get('scenario') or cmp.get('scenario')!='V01-T0':issues.append('comparison-scenario-mismatch')
  if q.get('geometryVersion')!=p.get('geometryVersion') or cmp['inputGeometryVersion']!=q.get('geometryVersion'):issues.append('pinned-geometry-version-mismatch')
  values.append(p.get('eaveZM'))
 if len(set(datums))!=1 or None in datums:issues.append('different-datum')
 value=None if issues else values[0]-values[1]
 if value is not None and not math.isclose(value,cmp['valueM'],abs_tol=1e-9):issues.append('comparison-cache-mismatch')
 result['D01']['comparison']={'uid':'V01:CMP01','status':'invalid-input' if issues else 'computed-synthetic','issues':issues,'subject':'V01:B02','reference':'V01:B01','valueM':None if issues else value,'meaning':'侧房减主屋的共同基准檐口高程差；不是自身檐高之差','cacheAgreement':not issues}
 ext=contract['D03'];spaces=[N[PREFIX+i] for i in ext['externalSpaces']]
 result['D03']['T01']=[{'uid':n['properties']['uid'],'name':n['properties']['name'],'geometryVersion':n['properties']['geometryVersion'],'groundZM':n['properties']['groundZM'],'coverState':n['properties']['coverState'],'rangeBasis':n['properties']['measurementBoundaryBasis'],'useState':n['properties']['useState'],'threeDimensionalBoundaryState':'not-fully-declared'} for n in spaces]
 c=N['V01:S05']['properties'];segments=json.loads(c['boundarySegmentsJson']);bound=[];expected_boundary=boundary_qualification(M)
 for b in segments:
  rels=[r for r in R if r['source']=='V01:S05' and r['type']=='BOUNDARY_PARTICIPANT' and r['properties'].get('boundaryId')==b['id']];a,z=b['polyline'];L=math.dist(a,z);ints=[];participants=[]
  for r in rels:
   p=r['properties'];require(p.get('analysisSliceZM')==c['analysisSliceZM'] and p.get('geometryVersion')==VERSION and p.get('derivationRule')=='V01-boundary-slice-union-v1','Unqualified boundary relationship')
   require(all(p.get(k)==v for k,v in expected_boundary[p['id']].items()),'Boundary cache differs from source geometry')
   v=pair(p['solidIntervalBoundsM']);ints+=v;participants.append({'uid':r['target'],'name':N[r['target']]['properties']['name'],'relationshipUid':p['uid'],'role':p['participantRole'],'intervalsM':v,'contributionM':p['netContributionM']})
  require(rels and b['state']=='known','Missing boundary status/participants')
  merged=merge_intervals(ints,L);bound.append({'id':b['id'],'lengthM':L,'solidIntervalsM':merged,'solidLengthM':sum(e-s for s,e in merged),'coverState':b['coverState'],'participants':participants})
 perimeter=sum(x['lengthM'] for x in bound);solid=sum(x['solidLengthM'] for x in bound)
 result['D03']['T02']={'uid':'V01:S05','analysisSliceZM':c['analysisSliceZM'],'perimeterM':perimeter,'netSolidBoundaryM':solid,'netSolidRatio':solid/perimeter,'classifiedState':'out-of-scope-for-legacy-four-side-rule','boundaryCoverage':1.0,'segments':bound,'meaning':'z=1m切片与内院分析边界；墙扣院门，柱计局部截面，有盖不计连续实体；不是三维围合度或建筑类型已验证'}
 entrances=[]
 for id in ext['entrances']:
  uid=PREFIX+id;n=N[uid];p=n['properties'];rels=[r for r in R if r['type']=='INTERFACE_OF' and r['source']==uid]
  entrances.append({'uid':uid,'name':p['name'],'widthM':p['widthM'],'widthMeaning':p.get('widthMeaning','旧开口分析跨度，不等于当前成人净通行宽度验证'),'relativePosition':p['relativePosition'],'referenceMode':p['referenceMode'],'startChainageM':p['startChainageM'],'endChainageM':p['endChainageM'],'referenceLengthM':p['referenceLengthM'],'referenceCenterXY':p['referenceCenterXY'],'sideBoundaryMappings':json.loads(p['sideBoundaryMappingsJson']),'participation':[{'target':r['target'],'role':r['properties']['role'],'relationshipUid':r['properties']['uid']} for r in rels],'clearanceState':'not-geometrically-validated'})
 result['D03']['T03']=entrances
 validspaces={PREFIX+i for i in ext['externalSpaces']};adj={u:[] for u in validspaces};selected=[]
 for r in R:
  p=r['properties']
  if r['type']!='DIRECT_ACCESS_TO' or r['source'] not in validspaces or r['target'] not in validspaces:continue
  require(p.get('contextId')==ext['passageContextId'] and p.get('snapshot')=='V01-synthetic-T0' and p.get('actor')=='正常成人步行（旧合成情境断言）','Passage context mismatch')
  via=p['viaUid'];ends={x['target'] for x in R if x['source']==via and x['type']=='INTERFACE_OF' and x['properties'].get('role') in ('side-a','side-b')}
  require(ends=={r['source'],r['target']},'Passage endpoints do not match interface')
  adj[r['source']].append((r['target'],via,p['uid']));selected.append(p['uid'])
  if p.get('bidirectional') is True:adj[r['target']].append((r['source'],via,p['uid']))
 paths=[]
 for req in ext['pathRequests']:
  start=PREFIX+req['from'];goal=PREFIX+req['to'];queue=collections.deque([(start,[start],[],[])]);seen={start};found=None
  while queue:
   u,seq,via,rs=queue.popleft()
   if u==goal:found={'nodes':seq,'via':via,'relationships':rs,'crossings':len(via)};break
   for v,i,r in adj[u]:
    if v not in seen:seen.add(v);queue.append((v,seq+[v],via+[i],rs+[r]))
  paths.append({'from':start,'to':goal,'status':'known-subgraph-path' if found else 'not-demonstrated-in-known-subgraph','path':found})
 result['D03']['T04']={'contextId':ext['passageContextId'],'actor':'正常成人步行（旧合成情境断言）','snapshot':'V01-synthetic-T0','relationships':selected,'paths':paths,'meaning':'最少跨界数仅在已知外部子图内；bidirectional旧断言显式双向处理；不证明净空、真实可达、步行距离或全宅最短路'}
 u=N['V01:U01']['properties'];window=Polygon(pair(u['areaScopePolygonXY']));require(window.is_valid and window.area>0,'Bad area scope');areas=[];shapes=[]
 for id in ext['localAreaSpaces']:
  p=N[PREFIX+id]['properties'];poly=Polygon(pair(p['footprintXY']));require(poly.is_valid and window.covers(poly),'External space outside declared window')
  require(p['groundZM']==u['areaScopeLevelZM'] and p['coordinateFrame']=='V01-local-XYZ' and p['geometryVersion']==u['areaScopeVersion'],'Mixed floor/frame/version')
  shapes.append(poly);areas.append({'uid':PREFIX+id,'areaM2':poly.area,'ratioToLocalWindow':poly.area/window.area})
 union=unary_union(shapes);overlap=sum(s.area for s in shapes)-union.area;overlap=0.0 if abs(overlap)<1e-10 else overlap;pos=next(r['properties'] for r in R if r['type']=='PLAN_POSITION' and r['source']=='V01:S04' and r['target']=='V01:S05')
 result['D03']['T05']={'scopeId':u['areaScopeId'],'levelZM':u['areaScopeLevelZM'],'scopePolygonXY':u['areaScopePolygonXY'],'scopeAreaM2':window.area,'scopeBasis':u['areaScopeBasis'],'includedSpaces':[PREFIX+i for i in ext['localAreaSpaces']],'excludedSpaces':[PREFIX+i for i in ext['excludedAreaSpaces']],'excludedBuildings':[PREFIX+i for i in ext['excludedAreaBuildings']],'areas':areas,'spaceUnionAreaM2':union.area,'unionRatioToLocalWindow':union.area/window.area,'overlapDeductedM2':overlap,'deductionPolicy':'按空间既有声明矩形，不扣柱；不与包含廊的建筑投影求和。围合长度另在z=1m切片计算，分母不是净使用面积','wholeDwellingRatio':None,'wholeDwellingState':'not-established-overall-boundary-incomplete','position':{'subject':'V01:S04','reference':'V01:S05','deltaXM':pos['deltaXM'],'deltaYM':pos['deltaYM'],'alongAxisM':pos['alongAxisM'],'meaning':'廊相对前院中心，不是双院序列'}}
 uses={};missing=[]
 for n in spaces:
  p=n['properties'];supported=any(r['source']==p['uid'] and r['type']=='HAS_SOURCE' and {'useState','useValues','useScope'}<=set(r['properties'].get('fields',[])) and r['properties'].get('sourceVersion')==N[r['target']]['properties'].get('sourceVersion') and r['properties'].get('locator','').startswith('/nodes/') and N[r['target']]['properties'].get('sourceKind') in ('synthetic_assignment','archived_synthetic_assignment') for r in R)
  if not supported or p['useState']!='known':missing.append(p['uid']);continue
  for val in set(p['useValues']):uses.setdefault(val,set()).add(p['uid'])
 result['D03']['T06']={'scope':[n['properties']['uid'] for n in spaces],'byUse':[{'use':u,'spaceUids':sorted(ids),'spaceCount':len(ids)} for u,ids in sorted(uses.items())],'knownSpaceCount':len(spaces)-len(missing),'unknownOrUnsupported':missing,'assignmentCount':sum(len(ids) for ids in uses.values()),'meaning':'沿用各空间自己的合成用途；同一用途内按空间UID去重，不由E例或形态新增用途，不升级为全宅用途统计'}
 result['identityReuse']={'mainBuilding':'V01:B01','hall':'V01:S01','courtyard':'V01:S05','veranda':'V01:S04','gate':'V01:I05','legacyDuplicateNodes':sorted(k for k in N if k.startswith(('D01V01:','D03V01:'))),'courtyardUsedBy':['D01尺寸','D03-T01','D03-T02','D03-T03','D03-T04','D03-T05','D03-T06'],'noMeasurementRecordNodes':not any('MeasurementInput' in n['labels'] for n in N.values())}
 if extensions and 'D04' in contract:
  import d04,d05,d06
  current=M;validate_extension_sources(current)
  result.update(D04=d04.analyze(current),D05=d05.analyze(current),D06=d06.analyze(current))
  import semantics
  expected=semantics.qualified_boundaries(current)
  for r in R:
   if r['type']=='BOUNDARY_PARTICIPANT':require(all(r['properties'].get(k)==v for k,v in expected[r['properties']['id']].items()),'Local boundary cache differs from actual geometry')
  result['basicRelations']=semantics.analyze(current)
  result['identityReuse']['extendedObjects']=['V01:B01','V01:B02','V01:S05','V01:W03','V01:W10','V01:I05','V01:I08','V01:I09','V01:I10']
  result['identityReuse']['newDistinctObjects']=['V01:B03','V01:CG01','V01:ST01','V01:TP01']
 return result

if __name__=='__main__':
 import sys
 from pathlib import Path
 g=json.loads(Path(sys.argv[1]).read_text());a=analyze(g);Path(sys.argv[2]).write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'comparison':a['D01']['comparison'],'enclosure':{k:v for k,v in a['D03']['T02'].items() if k!='segments'},'area':a['D03']['T05'],'identityReuse':a['identityReuse']},ensure_ascii=False,indent=2))
