"""V01 bounded relationship audit and planar derivations; not a general ontology reasoner.
Actual LPG inputs are rehydrated by projection.py before calling these functions.
No roof/contact/access edges are inferred or persisted by this module.
"""
import json,math
from shapely.geometry import LineString,Polygon,Point,box,mapping
from shapely.ops import unary_union
RULE='V01-local-boundary-coverage-v1'
SPACE_IDS=['S01','S02','S03','S04','S05','S06']
REQUIRED_NEW=[('S04','C01'),('S04','C02'),('S04','C03'),('S04','C04'),('S06','W10')]
def require(ok,msg):
 if not ok:raise ValueError(msg)
def nodes(m):return {n['id']:n for n in m['nodes']}
def length(xs):return sum(b-a for a,b in xs)
def rect(n):
 g=n['geometry'];return box(*g['min'][:2],*g['max'][:2])
def ring(n):
 a,b=n['geometry']['min'],n['geometry']['max'];x0,y0=a[:2];x1,y1=b[:2]
 return {'N':[[x0,y1],[x1,y1]],'E':[[x1,y1],[x1,y0]],'S':[[x1,y0],[x0,y0]],'W':[[x0,y0],[x0,y1]]}
def merged(xs,L):
 from compile_model import merge_intervals
 return merge_intervals(xs,L)
def difference(xs,cuts,L):
 from compile_model import subtract
 return subtract(xs,cuts,L)
def wall_slice(n,z):
 g=n['geometry'];a,b=g['a'],g['b'];t=g['thickness']/2
 require(a[0]==b[0] or a[1]==b[1],'Only axis-aligned finite walls supported')
 require(g['thickness']>0,'Invalid wall thickness')
 if g['heightMode']=='constant':h=g['height']
 else:
  require(g['heightMode']=='roof_profile' and g.get('topProfile'),'Unknown wall-height model')
  h=min(p[2] for p in g['topProfile'])
  require(z<h,'Slice crosses variable wall-top; not supported by this bounded rule')
 if not 0<=z<h:return Polygon()
 return box(round(min(a[0],b[0])-(t if a[0]==b[0] else 0),10),round(min(a[1],b[1])-(t if a[1]==b[1] else 0),10),round(max(a[0],b[0])+(t if a[0]==b[0] else 0),10),round(max(a[1],b[1])+(t if a[1]==b[1] else 0),10))
def intervals(m,n,line,z):
 from compile_model import geometry_intervals,column_intervals
 if 'Column' in n['labels']:return column_intervals(line,n,z),[]
 require('Wall' in n['labels'],'Unsupported solid participant')
 xs=geometry_intervals(line,wall_slice(n,z));N=nodes(m);cuts=[];opening_ids=[]
 g=n['geometry'];vertical=g['a'][0]==g['b'][0]
 # Openings are extruded across host thickness before clipping, including wall-end cuts.
 for r in m['relationships']:
  if r['type']!='INTERFACE_OF' or r['target']!=n['id'] or r['properties'].get('role')!='opening-host':continue
  o=N[r['source']]['geometry'];a,b=o['a'],o['b']
  if not o['z'][0]<=z<o['z'][1]:continue
  require((a[0]==b[0]==g['a'][0]) if vertical else (a[1]==b[1]==g['a'][1]),'Opening off host axis')
  t=g['thickness']/2
  region=box(a[0]-t,min(a[1],b[1]),a[0]+t,max(a[1],b[1])) if vertical else box(min(a[0],b[0]),a[1]-t,max(a[0],b[0]),a[1]+t)
  region=Polygon([(round(x,10),round(y,10)) for x,y in region.exterior.coords])
  cut=geometry_intervals(line,region)
  if cut:cuts+=cut;opening_ids.append(r['source'])
 return difference(xs,cuts,line.length),sorted(opening_ids)
def local_ranges(m,r):
 N=nodes(m);s=N[r['source']];p=r['properties'];z=s['properties']['analysisSliceZM'];out=[]
 for bid in p['localBoundaryIds']:
  line=LineString(ring(s)[bid]);xs,ops=([],[]) if p['participantRole']=='covered-open-transition' else intervals(m,N[r['target']],line,z)
  if xs or p['participantRole']=='covered-open-transition':out.append({'boundaryId':bid,'referencePolylineXY':[list(c) for c in line.coords],'referenceLengthM':line.length,'intervalsM':xs,'netLengthM':length(xs),'deductedOpeningIds':ops})
 return out
def qualified_boundaries(m):
 out={}
 for r in sorted(m['relationships'],key=lambda r:r['id']):
  if r['type']!='BOUNDARY_PARTICIPANT':continue
  ranges=local_ranges(m,r)
  out[r['id']]={'localRangesJson':json.dumps(ranges,ensure_ascii=False,sort_keys=True,separators=(',',':')),'localNetLengthM':sum(v['netLengthM'] for v in ranges),'localRuleVersion':RULE,'localGeometryVersion':m['modelVersion']}
 return out
def roof_coverage(m):
 N=nodes(m);roof=N['RF01'];g=roof['geometry'];require(g['kind']=='gable_roof','Unsupported roof projection')
 rp=box(g['x'][0],g['y'][0],g['x'][1],g['y'][1]);require(rp.area>0,'Invalid roof projection')
 rows=[]
 for id in SPACE_IDS:
  s=N[id];p=rect(s);hit=p.intersection(rp);area=hit.area
  rows.append({'spaceUid':'V01:'+id,'providerUid':'V01:RF01','spaceAreaM2':p.area,'coveredAreaM2':area,'coverageRatio':area/p.area,'state':'none-from-this-provider' if area<1e-10 else 'full-projection' if abs(area-p.area)<1e-9 else 'partial-projection','intersectionGeoJSON':mapping(hit),'overallCoverType':s['properties']['overallCoverType'],'ruleVersion':RULE,'geometryVersion':m['modelVersion'],'sourceUid':'V01:EV01','sourceVersion':N['EV01']['properties']['sourceVersion'],'sourceLocators':[f'/nodes/{m["nodes"].index(s)}/geometry',f'/nodes/{m["nodes"].index(roof)}/geometry'],'scope':'指定RF01的XY投影；不是所有顶盖清单、三维包含、防雨或净空验证'})
 return json.loads(json.dumps(rows,ensure_ascii=False))
def interface_occupancy(m):
 N=nodes(m);i=N['I04'];line=LineString([i['geometry']['a'],i['geometry']['b']]);z=1.0
 sides=sorted(r['target'] for r in m['relationships'] if r['source']=='I04' and r['type']=='INTERFACE_OF' and r['properties'].get('role') in ['side-a','side-b'])
 rs=sorted([r for r in m['relationships'] if r['type']=='BOUNDARY_PARTICIPANT' and r['source'] in sides and 'Column' in N[r['target']]['labels']],key=lambda r:r['id']);columns=sorted(set(r['target'] for r in rs));rows=[];occupied=[]
 for id in columns:
  xs,_=intervals(m,N[id],line,z);occupied+=xs
  rows.append({'uid':'V01:'+id,'intervalsM':xs,'role':'positive-column-occupation' if xs else 'endpoint-limit-no-positive-occupation','viaRelationships':['V01:'+r['id'] for r in rs if r['target']==id]})
 solid=merged(occupied,line.length);free=difference([[0.,line.length]],solid,line.length)
 return {'interfaceUid':'V01:I04','sourcePath':['INTERFACE_OF(side-a/side-b)','BOUNDARY_PARTICIPANT(column-section)'],'participants':rows,'referencePolylineXY':[list(c) for c in line.coords],'spanM':line.length,'analysisSliceZM':z,'occupiedIntervalsM':solid,'planOpenIntervalsM':free,'planOpenSegmentsXY':[[list(line.interpolate(t).coords)[0] for t in pair] for pair in free],'planOpenLengthsM':[b-a for a,b in free],'clearanceValidated':False,'passageConclusion':'not-established','geometryVersion':m['modelVersion'],'ruleVersion':RULE,'sourceUid':'V01:EV01','meaning':'只扣现有柱的平面开敞段；不得当作已验证的连续净宽或三条通道'}
def street_reference(m):
 N=nodes(m);s=N['S06'];st=N['ST01'];g=st['geometry'];p=Polygon(list(zip(g['surfaceXY'][::2],g['surfaceXY'][1::2])));hit=rect(s).intersection(p)
 return {'spaceUid':'V01:S06','referenceUid':'V01:ST01','intersectionAreaM2':hit.area,'spaceAreaM2':rect(s).area,'fullyWithinPlanProjection':p.covers(rect(s)),'sameDeclaredLevel':math.isclose(s['properties']['groundZM'],g['surfaceZM'],abs_tol=1e-9),'spaceGroundZM':s['properties']['groundZM'],'streetSurfaceZM':g['surfaceZM'],'geometryVersion':m['modelVersion'],'sourceUid':'V01:EV01','ruleVersion':RULE,'semanticRelationPersisted':False,'passageConclusion':'not-established','meaning':'平面范围与声明层位对应；不合并身份、不推出BOT包含或通行'}
def boundary_summary(m):
 N=nodes(m);rows=[]
 for sid in SPACE_IDS:
  s=N[sid];z=s['properties']['analysisSliceZM'];relations=[r for r in m['relationships'] if r['source']==sid and r['type']=='BOUNDARY_PARTICIPANT'];segments=[]
  for bid,xy in ring(s).items():
   line=LineString(xy);registered=[];participants=[]
   for r in relations:
    for loc in local_ranges(m,r):
     if loc['boundaryId']!=bid:continue
     registered+=loc['intervalsM'];participants.append({'uid':'V01:'+r['target'],'relationshipUid':'V01:'+r['id'],**loc})
   solid=merged(registered,line.length);candidates=[];unregistered=[]
   for id,n in sorted(N.items()):
    if not set(n['labels'])&{'Wall','Column'} or any(r['target']==id for r in relations):continue
    xs,_=intervals(m,n,line,z)
    if not xs:continue
    unregistered+=xs;candidates.append({'uid':'V01:'+id,'intervalsM':xs,'decision':'geometry-only-candidate-not-persisted','basis':'finite section crosses analysis boundary; no independent semantic assertion'})
   additional=difference(unregistered,solid,line.length)
   segments.append({'id':bid,'lengthM':line.length,'registeredSolidIntervalsM':solid,'registeredSolidLengthM':length(solid),'overlapDeductedM':max(0.,length(registered)-length(solid)),'participants':participants,'geometryCandidates':candidates,'additionalCandidateIntervalsM':additional,'unassignedLengthM':line.length-length(solid),'unassignedMeaning':'未被已登记实体占用，不自动等于开放；候选、理论裁切线及未知保持区分'})
  rows.append({'spaceUid':'V01:'+sid,'boundaryBasis':s['properties']['boundaryBasis'],'analysisSliceZM':z,'segments':segments,'perimeterM':sum(r['lengthM'] for r in segments),'registeredSolidLengthM':sum(r['registeredSolidLengthM'] for r in segments),'candidateState':'resolved-as-unasserted-geometric-candidates' if any(r['geometryCandidates'] for r in segments) else 'none-in-declared-inputs','notThreeDimensionalEnclosure':True})
 return rows

def validate(m):
 N=nodes(m);version=m['modelVersion'];rs=m['relationships'];by_pair={}
 require(m['analysisContract']['basicRelations']['ruleVersion']==RULE,'Basic-relation rule changed without implementation')
 contract=m['analysisContract']['basicRelations'];source=N['EV01']
 require({'Source','SyntheticSource'}<=set(source['labels']) and source['properties'].get('sourceVersion')==version,'Local assertion source object/version')
 for i,r in enumerate(rs):
  p=r['properties'];require(r['source'] in N and r['target'] in N,'Application endpoint absent')
  require(p.get('assertionSourceUid')=='V01:EV01' and p.get('assertionSourceVersion')==version and p.get('assertionLocator')==f'/relationships/{i}','Local relationship provenance '+r['id'])
 for id,fields in contract['objectSourceFields'].items():
  require(id in N and set(fields)<=set(N[id]['properties']),'Missing application source field '+id)
  supported=set()
  for r in rs:
   if r['source']!=id or r['type']!='HAS_SOURCE':continue
   p=r['properties'];s=N[r['target']];fs=p.get('fields',[])
   require(fs and len(fs)==len(set(fs)) and set(fs)<=set(N[id]['properties']),'Empty/invalid source fields '+r['id'])
   require({'Source','SyntheticSource'}<=set(s['labels']) and p.get('sourceUid')=='V01:'+r['target'] and p.get('sourceVersion')==s['properties'].get('sourceVersion'),'Application source identity/version '+r['id'])
   loc=f'/nodes/{m["nodes"].index(N[id])}/properties'
   if r['target']=='EV09':
    require(id=='B02' and s['properties'].get('sourceVersion')=='1.1' and len(s['properties'].get('sourceSha256',''))==64,'Historical source qualification')
    loc=s['properties']['sourceLocator']
   else:require(r['target']=='EV01' and p['sourceVersion']==version,'Unexpected application source')
   require(p.get('locatorKind')=='json_pointer' and p.get('locator')==loc,'Application source locator '+r['id'])
   supported.update(fs)
  require(set(fields)<=supported,'Missing application field support '+id)
 for n in m['nodes']:
  p=n['properties']
  if n['class']=='Evidence':require(p.get('locator')==n['id'] and p.get('geometryVersion')==version and p.get('isRealWorldEvidence') is False and p.get('evidenceKind') in ['synthetic_spec','synthetic_drawing'],'Evidence metadata '+n['id'])
  if n['class']=='Source':require(p.get('sourcePath') and p.get('sourceVersion') and p.get('sourceLocator') and p.get('isRealWorldEvidence') is False,'Source metadata '+n['id'])
 for r in rs:
  if r['type']=='BOUNDARY_PARTICIPANT':by_pair.setdefault((r['source'],r['target']),[]).append(r)
 for pair in REQUIRED_NEW:require(len(by_pair.get(pair,[]))==1,'Missing/duplicate required local boundary '+str(pair))
 for sid in SPACE_IDS:
  n=N[sid];p=n['properties'];require(all(f in p for f in ['boundarySegments','analysisSliceZM','boundaryBasis','overallCoverType','coverStateMeaning']),'Missing actual basic-relation field '+sid);require(p.get('analysisSliceZM')==1.,'Unsupported boundary slice '+sid)
  require({b['id']:b['polyline'] for b in p['boundarySegments']}==ring(n),'Boundary segments inconsistent with own space '+sid)
  require(p.get('coverStateMeaning')=='overall-space-character-not-zero-projection','Ambiguous overall cover meaning '+sid)
  require(p.get('geometryVersion')==version and p.get('unit')=='m' and p.get('coordinateFrame')=='V01-local-XYZ' and p.get('scenario')=='V01-T0','Incompatible boundary frame '+sid)
  for f in ['boundarySegments','analysisSliceZM','boundaryBasis','overallCoverType','coverStateMeaning']:
   support=[r for r in rs if r['source']==sid and r['type']=='HAS_SOURCE' and f in r['properties']['fields'] and r['target']=='EV01' and r['properties']['sourceVersion']==version and r['properties']['locator']==f'/nodes/{m["nodes"].index(n)}/properties']
   require(support,'Missing basic field provenance '+sid+'.'+f)
 for pair,rels in by_pair.items():
  require(len(rels)==1,'Duplicate boundary assertion '+str(pair))
  r=rels[0];p=r['properties'];require(p.get('rangeState')=='localized-by-existing-geometry' and p.get('geometryVersion')==version and p.get('analysisSliceZM')==1.,'Unqualified localized relationship '+r['id'])
  require(p.get('localBoundaryIds') and len(set(p['localBoundaryIds']))==len(p['localBoundaryIds']) and set(p['localBoundaryIds'])<=set(ring(N[r['source']])),'Missing/invalid local boundary ids')
  require(p['assertionLocator']==f'/relationships/{rs.index(r)}' and p['assertionSourceVersion']==version,'Local relationship provenance')
  loc=local_ranges(m,r);require(loc,'Empty localized boundary '+r['id'])
 roof=N['RF01'];require(roof['properties'].get('geometryVersion')==version,'Roof version mismatch')
 for id in ['RS01','RS02']:require(N[id]['properties'].get('geometryVersion')==version,'Roof-surface version mismatch')
 rg=roof['geometry'];rp=box(rg['x'][0],rg['y'][0],rg['x'][1],rg['y'][1]);surfaces=unary_union([Polygon([(p[0],p[1]) for p in N[id]['geometry']['vertices']]) for id in ['RS01','RS02']])
 require(rp.equals(surfaces),'Roof provider and surface projections disagree; refresh inputs')
 for row in roof_coverage(m):
  p=N[row['spaceUid'][4:]]['properties']
  require(not (p.get('coverStateMeaning')=='zero-projection' and row['coveredAreaM2']>0),'Zero-cover claim conflicts with roof projection')
 # Application obligations; do not manufacture unknown external spaces or hosts.
 for n in m['nodes']:
  id=n['id'];cls=n['class'];out=[r for r in rs if r['source']==id]
  if cls=='Element':
   members=[r for r in out if r['type']=='MEMBER_OF_ZONE']
   require(len(members)==1 and members[0]['target']==contract['memberTargets'].get(id) and N[members[0]['target']]['class'] in ['Zone','Building'],'Missing/ambiguous member organisation '+id)
  if cls=='Interface':
   sides=[r for r in out if r['type']=='INTERFACE_OF' and r['properties'].get('role') in ['side-a','side-b']];hosts=[r for r in out if r['type']=='INTERFACE_OF' and r['properties'].get('role')=='opening-host']
   require(len(sides)==(1 if id in ['I08','I09','I10'] else 2) and len(set(r['target'] for r in sides))==len(sides),'Interface sides obligation '+id)
   require(sorted(r['properties']['role'] for r in sides)==(['side-a'] if id in ['I08','I09','I10'] else ['side-a','side-b']) and all(N[r['target']]['class']=='Space' for r in sides),'Interface side roles/endpoints '+id)
   require(len(hosts)==(0 if id in ['I01','I04'] else 1),'Interface host obligation '+id)
   require(all('Wall' in N[r['target']]['labels'] and N[r['target']]['class']=='Element' for r in hosts),'Interface host endpoint '+id)
   require(len([r for r in out if r['type']=='INTERFACE_OF'])==len(sides)+len(hosts),'Unexpected interface participation role '+id)
 require(not any(r['type']=='BOT_HAS_BUILDING' and r['source']=='U01' and r['target']=='B03' for r in rs),'Independent neighbour falsely belongs to U01')
 require(not any('Element' in N[id]['labels'] for id in ['RS01','RS02']),'Geometry surface treated as Element')
 require('SpatialReference' in N['ST01']['labels'] and 'Space' in N['S06']['labels'] and 'Zone' not in N['CG01']['labels'],'Cross-module identity roles')
 return True

def object_coverage(m):
 rows=[]
 for n in sorted(m['nodes'],key=lambda n:n['id']):
  id=n['id'];cls=n['class'];rels=sorted([r['id'] for r in m['relationships'] if id in [r['source'],r['target']]])
  mandatory=['来源元数据（定位、版本或生成版本、非实证身份）'] if cls in ['Evidence','Source'] else ['声明属性的来源字段覆盖、定位与版本'];optional=[];unknown=[];na=[]
  if cls=='Element':mandatory+=['唯一组织归属'];optional+=['仅对已声明空间检查局部边界'];unknown+=['真实接触、受力与净空未验证']
  elif cls=='Space':mandatory+=['自身边界口径及局部参与','指定屋顶投影查询'];optional+=['有据的跨模块参照'];unknown+=['完整三维边界及未登记顶盖']
  elif cls=='Interface':mandatory+=['已知参与角色及局部几何'];unknown+=['真实净空与通行'];unknown+=['未实例化外侧空间'] if id in ['I08','I09','I10'] else [];na+=['墙宿主（开放分界）'] if id in ['I01','I04'] else []
  elif cls=='Building':mandatory+=['建筑身份、几何与比较参照'];na+=['归U01'] if id=='B03' else []
  elif cls=='GeometryRepresentation':mandatory+=['几何版本及所属屋顶' if id in ['RS01','RS02'] else '地面参照及几何版本'];na+=['实体成员/结构支承']
  else:na+=['统一强制建筑边数'];optional+=['按自身证据/分析/参照角色查询']
  rows.append({'uid':'V01:'+id,'name':n['name'],'class':cls,'mandatory':mandatory,'optional':optional,'notApplicable':na,'unknown':unknown,'relationshipIds':rels,'acceptance':'declared-application-obligations-passed-not-completeness-proof'})
 rows.append({'uid':'V01:SOURCE','name':'来源快照元数据','class':'DatasetSnapshot','mandatory':['原始模型SHA与逐属性读回一致'],'optional':[],'notApplicable':['建筑边界/归属/通行'],'unknown':[],'relationshipIds':[],'acceptance':'snapshot-metadata-not-building-object'})
 return rows

def analyze(m):
 validate(m)
 return json.loads(json.dumps({'ruleVersion':RULE,'modelVersion':m['modelVersion'],'scope':'synthetic-planar-and-application-rules-only','localizedBoundaries':boundary_summary(m),'roofCoverage':roof_coverage(m),'interfaceOccupation':interface_occupancy(m),'streetReference':street_reference(m),'objectCoverage':object_coverage(m),'semanticCompleteness':'not-proved','empiricalValidity':'not-validated'},ensure_ascii=False))
