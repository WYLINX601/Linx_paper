"""Canonical V01 -> LPG, with deterministic local geometry qualification.
No database access. No direct credentials. All values remain synthetic.
"""
from pathlib import Path
import copy,hashlib,json,math
from shapely.geometry import LineString,Polygon,Point,box
from shapely.ops import unary_union
VERSION='V01-unified-2.2'
DS='V01';PREFIX='V01:'
MODEL_PATH='研究成果/〔合成试例〕虚拟民居单体试验V01/案例模型.json'
LABELS={'KGItem','V01','Demo','Entity','Zone','DwellingUnit','Building','Space','Courtyard','ExternalTransition','Element','Wall','Column','Roof','RoofSurface','GeometryRepresentation','Interface','EntranceInterface','Evidence','Source','SyntheticSource','ReferenceDatum','AnalysisRule','ComparisonResult','DatasetSnapshot','材质_木','材质_砖','材质_灰泥','材质_陶瓦','AnalysisCollection','SpatialReference','StreetSegment','GroundProfile'}
RELS={'PART_OF','MEMBER_OF_ZONE','ASSOCIATED_WITH','BOT_HAS_BUILDING','BOT_HAS_SPACE','BOT_CONTAINS_ELEMENT','BOUNDARY_PARTICIPANT','INTERFACE_OF','DIRECT_ACCESS_TO','SPATIAL_RELATION','SUPPORTS_SYSTEM','DOCUMENTS','AXIS_JOINS','ENVELOPE_INTERSECTS','SHARES_BOUNDARY','HAS_SOURCE','USES_DATUM','DECLARES_RULE','USES_ANALYSIS_RULE','HAS_COMPARISON','COMPARES_SUBJECT','COMPARES_REFERENCE','APPLIES_RULE','PLAN_POSITION','FACADE_PARTICIPANT','HAS_ANALYSIS_MEMBER','STREET_BOUNDARY_PARTICIPANT','REFERENCES_GROUND'}
def require(v,msg):
 if not v:raise ValueError(msg)
def dumps(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(v):return hashlib.sha256(dumps(v).encode()).hexdigest()
def flat(v):return [float(x) for p in v for x in p]
def pair(v):return [v[i:i+2] for i in range(0,len(v),2)]
def polygon(n):
 g=n['geometry'];a=g['min'];b=g['max'];return box(a[0],a[1],b[0],b[1])
def normalize_props(p):
 out={}
 for k,v in p.items():
  if v is None:continue
  if isinstance(v,dict) or isinstance(v,list) and any(isinstance(x,(list,dict)) for x in v):out[k+'Json']=dumps(v)
  elif isinstance(v,list) and v and all(type(x) in (int,float) for x in v) and any(type(x)==float for x in v):out[k]=[float(x) for x in v]
  else:out[k]=copy.deepcopy(v)
 return out

def merge_intervals(xs,length):
 out=[]
 for a,b in sorted(xs):
  a=max(0.,float(a));b=min(float(length),float(b))
  if b-a<=1e-10:continue
  if out and a<=out[-1][1]+1e-9:out[-1][1]=max(out[-1][1],b)
  else:out.append([a,b])
 return out

def subtract(xs,cuts,length):
 out=merge_intervals(xs,length)
 for a,b in merge_intervals(cuts,length):
  nxt=[]
  for s,e in out:
   if b<=s or a>=e:nxt.append([s,e])
   else:
    if a>s:nxt.append([s,a])
    if b<e:nxt.append([b,e])
  out=nxt
 return out

def geometry_intervals(line,geom):
 hit=line.intersection(geom)
 parts=list(hit.geoms) if hasattr(hit,'geoms') else [hit];out=[]
 for part in parts:
  if isinstance(part,LineString) and part.length>1e-10:
   ts=[line.project(Point(c)) for c in part.coords];out.append([min(ts),max(ts)])
 return merge_intervals(out,line.length)

def column_intervals(line,n,z):
 g=n['geometry'];cx,cy,cz=g['center'];r=g['radius']
 if not cz<=z<cz+g['height']:return []
 a,b=line.coords;dx=b[0]-a[0];dy=b[1]-a[1];L=line.length
 t=((cx-a[0])*dx+(cy-a[1])*dy)/L
 d=abs((cx-a[0])*dy-(cy-a[1])*dx)/L
 if d>=r:return []
 half=math.sqrt(r*r-d*d)
 return merge_intervals([[t-half,t+half]],L)

def wall_intervals(line,n,z,model,N):
 g=n['geometry'];a=g['a'];b=g['b'];h=g['height'];t=g['thickness']/2
 # Current perimeter walls are constant height; roof-profile walls are not silently flattened.
 require(g.get('heightMode')=='constant','Localized wall slice requires declared constant height')
 if not 0<=z<h:return []
 solid=box(round(min(a[0],b[0])-(t if a[0]==b[0] else 0),10),round(min(a[1],b[1])-(t if a[1]==b[1] else 0),10),round(max(a[0],b[0])+(t if a[0]==b[0] else 0),10),round(max(a[1],b[1])+(t if a[1]==b[1] else 0),10))
 intervals=geometry_intervals(line,solid);cuts=[]
 for rel in model['relationships']:
  if rel['type']=='INTERFACE_OF' and rel['target']==n['id'] and rel['properties'].get('role')=='opening-host':
   opening=N[rel['source']];og=opening['geometry']
   if og['z'][0]<=z<og['z'][1]:
    # Projection is explicitly a host-axis -> inside analysis-boundary correspondence.
    ds=sorted(line.project(Point(og[k])) for k in ('a','b'))
    cuts.append(ds)
 return subtract(intervals,cuts,line.length)

def boundary_qualification(model):
 N={n['id']:n for n in model['nodes']};c=N['S05'];bs=c['properties']['boundarySegments'];z=c['properties']['analysisSliceZM'];by={b['id']:b for b in bs};out={}
 require(z==1.0,'Current slice rule fixed at z=1m; re-version before changing')
 require(len(by)==len(bs)==4,'Boundary identities')
 lines=[]
 for i,b in enumerate(bs):
  line=LineString(b['polyline']);lines.append(line)
  require(line.length>0 and polygon(c).boundary.covers(line),'Boundary off existing space geometry')
  require(b['polyline'][-1]==bs[(i+1)%len(bs)]['polyline'][0],'Boundary ring gap')
  require(b['state']=='known','Incomplete perimeter state')
 require(math.isclose(sum(x.length for x in lines),polygon(c).length,abs_tol=1e-9) and math.isclose(unary_union(lines).length,polygon(c).length,abs_tol=1e-9),'Boundary not exhaustive or duplicated')
 for r in model['relationships']:
  if r['source']!='S05' or r['type']!='BOUNDARY_PARTICIPANT':continue
  p=r['properties'];b=by[p['boundaryId']];line=LineString(b['polyline']);n=N[r['target']];role=p['participantRole']
  require(p.get('geometryVersion')==model['modelVersion'],'Boundary participant version')
  if role=='covered-open-transition':intervals=[]
  elif role=='wall-boundary':intervals=wall_intervals(line,n,z,model,N)
  elif role=='column-section':intervals=column_intervals(line,n,z)
  else:raise ValueError('Unknown boundary contribution role')
  out[r['id']]={'referencePolylineXY':flat(b['polyline']),'referenceLengthM':float(line.length),'analysisSliceZM':z,'solidIntervalBoundsM':flat(intervals),'netContributionM':sum(v-u for u,v in intervals),'derivationRule':'V01-boundary-slice-union-v1','derivationStatus':'synthetic_geometry_derived','coverState':b['coverState']}
 return out

def interface_qualification(model):
 N={n['id']:n for n in model['nodes']};out={}
 for id in model['analysisContract']['D03']['entrances']:
  n=N[id];p=n['properties'];g=n['geometry'];a=g['a'];b=g['b'];refs=[r for r in model['relationships'] if r['source']==id and r['type']=='INTERFACE_OF'];sides=[r for r in refs if r['properties'].get('role') in ('side-a','side-b')]
  require(len(sides)==2 and {r['properties']['role'] for r in sides}=={'side-a','side-b'},'Entrance must keep two distinct roles')
  require(len({r['target'] for r in sides})==2,'Repeated entrance endpoint')
  projections=[]
  for r in sides:
   s=N[r['target']];sg=s['geometry'];candidates=[]
   ring=list(polygon(s).exterior.coords)
   for q1,q2 in zip(ring,ring[1:]):
    if abs(a[1]-b[1])<1e-9 and abs(q1[1]-q2[1])<1e-9 and min(q1[0],q2[0])-1e-9<=min(a[0],b[0]) and max(a[0],b[0])<=max(q1[0],q2[0])+1e-9:
     candidates.append((abs(q1[1]-a[1]),[[float(a[0]),float(q1[1])],[float(b[0]),float(q1[1])]],q1[1]-a[1]))
   require(candidates,'No complete parallel correspondence for entrance')
   candidates.sort(key=lambda x:x[0]);require(len(candidates)==1 or candidates[1][0]-candidates[0][0]>1e-9,'Ambiguous projection')
   dist,segment,offset=candidates[0]
   require(dist<=0.120000001,'Unexpected offset outside declared wall/space correspondence')
   projections.append({'spaceUid':PREFIX+s['id'],'role':r['properties']['role'],'segmentXY':segment,'offsetYM':float(offset),'absoluteOffsetM':float(dist),'basis':'同线局部' if dist<1e-9 else '宿主轴向该空间分析边界的明确平行映射；非原几何重合'})
  if p['referenceMode']=='host-axis-to-space-boundary-projection':
   host=N[p['referenceHostId']];hg=host['geometry'];ref=LineString([hg['a'],hg['b']]);require(ref.covers(LineString([a,b])),'Opening not on host axis')
   hosts=[r for r in refs if r['properties'].get('role')=='opening-host'];require(len(hosts)==1 and hosts[0]['target']==host['id'],'Wrong opening host')
  else:
   ref=LineString(next(x['polyline'] for x in N[p['referenceSpaceId']]['properties']['boundarySegments'] if x['id']==p['referenceBoundaryId']))
   require(ref.covers(LineString([a,b])),'Open boundary not on reference line')
  sa,sb=sorted([ref.project(Point(a)),ref.project(Point(b))])
  require(all(math.isclose(p[k],v,abs_tol=1e-9) for k,v in [('startChainageM',sa),('endChainageM',sb),('referenceLengthM',ref.length)]),'Entrance cached chainage mismatch')
  mid=ref.interpolate((sa+sb)/2)
  out[id]={'sideBoundaryMappingsJson':dumps(projections),'referencePolylineXY':flat(list(ref.coords)),'relativePosition':(sa+sb)/2/ref.length,'referenceCenterXY':[float(mid.x),float(mid.y)],'correspondenceRule':'V01-host-and-side-boundaries-v1','correspondenceVersion':VERSION}
 return out

def validate_model(m):
 def finite_tree(v):
  if isinstance(v,float):require(math.isfinite(v),'Non-finite input')
  elif isinstance(v,dict):
   for x in v.values():finite_tree(x)
  elif isinstance(v,list):
   for x in v:finite_tree(x)
 finite_tree(m)
 require(m['meta']['caseId']==DS and m['modelVersion']==VERSION,'Unexpected canonical model/version')
 ns=m['nodes'];rs=m['relationships'];N={n['id']:n for n in ns};ids=set(N)
 require(len(ids)==len(ns) and len({r['id'] for r in rs})==len(rs),'Duplicate identity')
 require(all(r['source'] in ids and r['target'] in ids for r in rs),'Missing relationship endpoint')
 require(all(r['type'] in RELS for r in rs),'Unknown relationship type')
 require(all(set(n['labels'])<=LABELS for n in ns),'Unknown label')
 require(not any(r['type'] in ('REALIZED_IN','BOUNDED_BY') for r in rs),'Competing legacy relationship facts')
 require(all('Element' not in n['labels'] for n in ns if n['id'] in ['RS01','RS02']),'Analysis surface still typed as physical element')
 require(N['S01']['name']=='堂屋' and 'Courtyard' in N['S05']['labels'],'Same-name source collision')
 for n in ns:
  p=n['properties'];g=n['geometry']
  if n['class']=='Building':
   for field,dirfield in [('widthM','widthDirection'),('depthM','depthDirection')]:
    require(p[dirfield] in ('+X','+Y'),'Unknown building measurement direction')
    axis=0 if p[dirfield]=='+X' else 1
    require(math.isclose(p[field],g['max'][axis]-g['min'][axis],abs_tol=1e-9),'Stale building dimensions '+n['id'])
   require(Polygon(pair(p['footprintXY'])).equals(polygon(n)),'Stale building footprint '+n['id'])
   require(p['groundZM']==g['min'][2] and p['groundPointXYZ'][2]==p['groundZM'] and p['eavePointXYZ'][2]==p['eaveZM'] and p['ridgePointXYZ'][2]==p['ridgeZM'],'Inconsistent building elevation '+n['id'])
  if n['class']=='Space':
   require(math.isclose(p['widthM'],g['max'][0]-g['min'][0],abs_tol=1e-9) and math.isclose(p['depthM'],g['max'][1]-g['min'][1],abs_tol=1e-9),'Stale dimensions '+n['id'])
   require(math.isclose(p['areaM2'],polygon(n).area,abs_tol=1e-9),'Stale space area '+n['id'])
   require(Polygon(pair(p['footprintXY'])).equals(polygon(n)),'Stale space footprint '+n['id'])
   require(p['useState']=='known' and p['useValues']==[p['use']],'Changed/duplicated legacy use '+n['id'])
 for r in rs:
  p=r['properties'];require(p.get('assertionSourceUid')=='V01:EV01' and p.get('assertionSourceVersion')==N['EV01']['properties']['sourceVersion'] and p.get('assertionLocator','').startswith('/relationships/'),'Relationship assertion provenance')
  if r['type']!='HAS_SOURCE':require(p['sourceUid']=='V01:EV01' and p['sourceVersion']==VERSION,'Relation source version')
  if r['type']=='BOT_CONTAINS_ELEMENT':require(N[r['source']]['class'] in ['Zone','Building'] and N[r['target']]['class']=='Element','Containment endpoints')
  if r['type']=='INTERFACE_OF':require(N[r['source']]['class']=='Interface' and r['properties'].get('role') in ['side-a','side-b','opening-host'],'Interface role missing')
  if r['type']=='HAS_SOURCE':
   p=r['properties'];require(p['sourceVersion']==N[r['target']]['properties']['sourceVersion'],'Source version mismatch')
   require(p['sourceUid']=='V01:'+r['target'],'Property source identity mismatch')
   require(set(p['fields'])<=set(N[r['source']]['properties']),'Source covers nonexistent property')
   require(p['locator'].startswith('/nodes/'),'Source locator absent')
 require(math.isclose(N['B01']['properties']['eaveZM'],N['RF01']['geometry']['eaveZ'],abs_tol=1e-12),'Wrong eave basis')
 require(N['B02']['properties']['groundZM']==3.0 and N['U01']['properties']['areaScopeLevelZM']==0.0,'Annex silently flattened to ground')
 require(math.isclose(N['CMP01']['properties']['valueM'],N['B02']['properties']['eaveZM']-N['B01']['properties']['eaveZM'],abs_tol=1e-9),'Stale comparison cache')
 boundary_qualification(m);interface_qualification(m)
 require({'D04','D05','D06'}<=set(m['analysisContract']),'Missing unified extension contract')
 import d04,d05,d06
 from projection import validate_extension_sources
 d04.validate(m);d05.validate(m);d06.validate(m)
 validate_extension_sources(m)
 import semantics
 semantics.validate(m)
 return True

def compile_model(path):
 path=Path(path);raw=path.read_bytes();m=json.loads(raw);validate_model(m);sha=hashlib.sha256(raw).hexdigest();nodes=[];rels=[];N={n['id']:n for n in m['nodes']};bq=boundary_qualification(m);iq=interface_qualification(m)
 from semantics import qualified_boundaries
 local=qualified_boundaries(m)
 for n in m['nodes']:
  p=normalize_props(n['properties']);p.update(uid=PREFIX+n['id'],id=n['id'],name=n['name'],**{'class':n['class']},datasetId=DS,caseId=DS,dataMode='synthetic_demo',graphStatus='active',sourceModelSha256=sha,evidenceIds=n['evidence'],sourceRecordJson=dumps(n))
  labels=set(n['labels'])|{'KGItem','V01','Demo'}
  if n['class'] not in ['Evidence','Source','ReferenceDatum','AnalysisRule','ComparisonResult']:labels.add('Entity')
  for k in ['geometry','labelEvidence','propertyOrigins']:
   if n.get(k) is not None:p[k+'Json']=dumps(n[k])
  if n['class'] in ['Space','Building','Zone']:p['botClassIri']='https://w3id.org/bot#'+n['class']
  elif n['class'] in ['Element','Interface']:p['botClassIri']='https://w3id.org/bot#'+n['class']
  g=n['geometry']
  if g and g['kind']=='rect':p.update(centerX=(g['min'][0]+g['max'][0])/2,centerY=(g['min'][1]+g['max'][1])/2,centerZ=g['z'])
  if g and g['kind']=='column':p.update(centerX=g['center'][0],centerY=g['center'][1],centerZ=g['center'][2])
  if n['id'] in iq:p.update(iq[n['id']])
  nodes.append({'id':n['id'],'labels':sorted(labels),'properties':p})
 for r in m['relationships']:
  p=normalize_props(r['properties']);p.update(uid=PREFIX+r['id'],id=r['id'],datasetId=DS,caseId=DS,dataMode='synthetic_demo',graphStatus='active',sourceModelSha256=sha,evidenceIds=r['evidence'],recordStatus=r['status'],sourceRecordJson=dumps(r))
  if r['id'] in bq:p.update(bq[r['id']])
  if r['id'] in local:p.update(local[r['id']])
  if r['type']=='INTERFACE_OF':p['botPropertyIri']='https://w3id.org/bot#interfaceOf'
  if r['type']=='HAS_SOURCE':
   source=N[r['source']]['properties'];p['fields']=[f+'Json' if isinstance(source[f],dict) or isinstance(source[f],list) and any(isinstance(x,(list,dict)) for x in source[f]) else f for f in p['fields']]
  if r['type']=='DIRECT_ACCESS_TO':p['viaUid']=PREFIX+p['via']
  if r['type']=='PLAN_POSITION':
   a=polygon(N[r['source']]).centroid;b=polygon(N[r['target']]).centroid;p.update(deltaXM=round(a.x-b.x,12),deltaYM=round(a.y-b.y,12),alongAxisM=round(a.y-b.y,12),crossAxisM=round(a.x-b.x,12))
  rels.append({'id':r['id'],'source':PREFIX+r['source'],'target':PREFIX+r['target'],'type':r['type'],'properties':p})
 nodes.append({'id':'SOURCE','labels':['DatasetSnapshot','Demo','KGItem','V01'],'properties':{'uid':'V01:SOURCE','id':'V01:SOURCE','name':'V01统一原型与来源快照','datasetId':DS,'caseId':DS,'dataMode':'synthetic_demo','graphStatus':'active','sourceModelSha256':sha,'sourcePath':MODEL_PATH,'method':'唯一V01主源投影；同对象复用，异例保留归档测试；无自动跨系统事务','rawModelJson':dumps(m),'inferenceResultsJson':dumps(m['analysisResults'])}})
 payload={'nodes':nodes,'relationships':rels,'sourceModelSha256':sha}
 validate_payload(payload,m)
 return m,payload

def validate_payload(p,m):
 N={n['properties']['uid']:n for n in p['nodes']};R={r['properties']['uid']:r for r in p['relationships']}
 require(len(N)==len(p['nodes']) and len(R)==len(p['relationships']),'Payload duplicate identities')
 require(all(k.startswith(PREFIX) for k in [*N,*R]),'Payload namespace')
 for n in N.values():require(set(n['labels'])<=LABELS and {'KGItem','V01'}<=set(n['labels']),'Payload labels')
 for r in R.values():require(r['source'] in N and r['target'] in N and r['type'] in RELS,'Payload endpoint/type')
 for row in list(N.values())+list(R.values()):
  pr=row['properties'];require(pr['caseId']==DS and pr['datasetId']==DS and pr['sourceModelSha256']==p['sourceModelSha256'],'Payload source binding')
  for k,v in pr.items():require(type(v) in (str,int,float,bool,list) and (not isinstance(v,list) or all(type(x) in (str,int,float,bool) for x in v)),'Unsupported property '+k)
 require(not any(k.startswith(('D01V01:','D03V01:')) for k in N),'Parallel active example remains')
 return True

if __name__=='__main__':
 import sys
 m,p=compile_model(sys.argv[1]);out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'nodes':len(p['nodes']),'relationships':len(p['relationships']),'modelSHA256':p['sourceModelSha256']}))
