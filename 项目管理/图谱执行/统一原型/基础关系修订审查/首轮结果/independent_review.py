"""Read-only frozen-input audit. Run with python -B; output only review-output."""
import ast, copy, hashlib, json, math, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
F=ROOT/'review-fixed'; O=ROOT/'review-output'
sys.dont_write_bytecode=True
sys.path.insert(0,str(F/'tools'))
from compile_model import compile_model, validate_model
from analyze import analyze
from projection import rehydrate
import semantics
from shapely.geometry import LineString, Point, box, Polygon
from shapely.ops import unary_union

def load(p): return json.loads((F/p).read_text())
def save(p,v): (O/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def manifest_check():
    mf=load('manifest.json')
    return {'files':len(mf),'mismatches':[p for p,h in mf.items() if hashlib.sha256((F/p).read_bytes()).hexdigest()!=h], 'manifestSHA256':hashlib.sha256((F/'manifest.json').read_bytes()).hexdigest()}
start=manifest_check(); assert not start['mismatches']
M,P=compile_model(F/'candidate/model.json'); A=analyze(P); B=load('baseline/model-2.1.json')
N={n['id']:n for n in M['nodes']}; BN={n['id']:n for n in B['nodes']}
R={r['id']:r for r in M['relationships']}; BR={r['id']:r for r in B['relationships']}
assert set(N)==set(BN) and all(N[i]['geometry']==BN[i]['geometry'] for i in N)
assert set(BR)<=set(R) and len(set(R)-set(BR))==5
assert all(all(R[i][k]==BR[i][k] for k in ['source','target','type','status','evidence']) for i in BR)
assert N['EV09']==BN['EV09']
assert P==load('candidate/payload.json')
analysis_matches_frozen=json.loads(json.dumps(A))==load('candidate/analysis.json')
# Record all changed existing fields, excluding only the exact model-version lift.
def diff(a,b,path=''):
    if a==b: return []
    if isinstance(a,dict) and isinstance(b,dict):
        out=[]
        for k in sorted(set(a)|set(b)):
            if k not in a or k not in b: out.append({'path':path+'/'+k,'before':a.get(k),'after':b.get(k)})
            else: out+=diff(a[k],b[k],path+'/'+k)
        return out
    if isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        return [v for i,(x,y) in enumerate(zip(a,b)) for v in diff(x,y,path+'/'+str(i))]
    if isinstance(a,str) and isinstance(b,str) and a.replace('V01-unified-2.1','V01-unified-2.2')==b: return []
    return [{'path':path,'before':a,'after':b}]
changes={'nodes':{i:diff(BN[i],N[i]) for i in N if diff(BN[i],N[i])},'relationships':{i:diff(BR[i],R[i]) for i in BR if diff(BR[i],R[i])},'additions':[R[i] for i in sorted(set(R)-set(BR))]}
save('authorized-diff.json',changes)

# Independent 1D clipping. Decimal-rounded rectangular walls, analytic circles;
# unlike production, subtract opening rectangles as polygons before intersecting.
def space_lines(n):
    x0,y0=n['geometry']['min'][:2];x1,y1=n['geometry']['max'][:2]
    return {k:LineString(v) for k,v in {'N':[(x0,y1),(x1,y1)],'E':[(x1,y1),(x1,y0)],'S':[(x1,y0),(x0,y0)],'W':[(x0,y0),(x0,y1)]}.items()}
def wallsolid(n,z):
    g=n['geometry'];a,b=g['a'],g['b'];t=g['thickness']/2
    h=g['height'] if g['heightMode']=='constant' else min(q[2] for q in g['topProfile'])
    if z>=h:return Polygon()
    x0,x1=sorted([a[0],b[0]]);y0,y1=sorted([a[1],b[1]])
    if x0==x1:x0-=t;x1+=t
    else:y0-=t;y1+=t
    geom=box(*[round(v,9) for v in [x0,y0,x1,y1]])
    for r in M['relationships']:
        if r['type']=='INTERFACE_OF' and r['target']==n['id'] and r['properties'].get('role')=='opening-host':
            o=N[r['source']]['geometry']
            if o['z'][0]<=z<o['z'][1]:
                x0,x1=sorted([o['a'][0],o['b'][0]]);y0,y1=sorted([o['a'][1],o['b'][1]])
                if x0==x1:x0-=t*2;x1+=t*2
                else:y0-=t*2;y1+=t*2
                geom=geom.difference(box(x0,y0,x1,y1))
    return geom

def independent_intervals(n,line,z):
    if 'Column' in n['labels']:
        g=n['geometry'];cx,cy,cz=g['center'];radius=g['radius']
        if not cz<=z<cz+g['height']:return []
        ax,ay=line.coords[0];bx,by=line.coords[-1]
        ux,uy=(bx-ax)/line.length,(by-ay)/line.length
        projection=(cx-ax)*ux+(cy-ay)*uy
        d2=(cx-ax)**2+(cy-ay)**2-projection**2
        if d2>=radius**2-1e-12:return []
        half=math.sqrt(max(0,radius**2-d2));lo=max(0,projection-half);hi=min(line.length,projection+half)
        return [[lo,hi]] if hi-lo>1e-9 else []
    hit=line.intersection(wallsolid(n,z))
    parts=list(hit.geoms) if hasattr(hit,'geoms') else [hit]
    return sorted([sorted([line.project(Point(p.coords[0])),line.project(Point(p.coords[-1]))]) for p in parts if isinstance(p,LineString) and p.length>1e-9])
rows=[]; discrepancies=[]; undeclared_side_hits=[]
for r in M['relationships']:
    if r['type']!='BOUNDARY_PARTICIPANT':continue
    if r['properties']['participantRole']=='covered-open-transition':continue
    expected={}
    for bid,line in space_lines(N[r['source']]).items():
        ints=independent_intervals(N[r['target']],line,1.)
        if ints:expected[bid]=ints
    actual={v['boundaryId']:v['intervalsM'] for v in semantics.local_ranges(M,r)}
    scoped={k:v for k,v in expected.items() if k in r['properties']['localBoundaryIds']}
    if set(scoped)!=set(actual) or any(len(actual.get(k,[]))!=len(v) or any(abs(a-b)>1e-7 for pair1,pair2 in zip(actual.get(k,[]),v) for a,b in zip(pair1,pair2)) for k,v in scoped.items()):
        discrepancies.append({'relationship':r['id'],'independentDeclaredSides':scoped,'production':actual})
    if set(expected)-set(scoped):undeclared_side_hits.append({'relationship':r['id'],'extraGeometricSides':{k:v for k,v in expected.items() if k not in scoped},'interpretation':'geometric-only intersections outside explicitly scoped side; not an automatic missing assertion'})
    rows.append({'relationship':r['id'],'space':r['source'],'participant':r['target'],'independentAllSides':expected,'declaredSides':r['properties']['localBoundaryIds']})
# Union on each registered boundary, independent of implementation interval merger.
unions=[]
for sid in semantics.SPACE_IDS:
    summary=next(x for x in A['basicRelations']['localizedBoundaries'] if x['spaceUid']=='V01:'+sid)
    for bid,line in space_lines(N[sid]).items():
        pieces=[]
        for row in rows:
            if row['space']!=sid:continue
            for a,b in row['independentAllSides'].get(bid,[]):pieces.append(LineString([line.interpolate(a),line.interpolate(b)]))
        union=unary_union(pieces).length;total=sum(p.length for p in pieces)
        prod=next(x for x in summary['segments'] if x['id']==bid)
        unions.append({'space':sid,'side':bid,'independentUnionM':union,'independentOverlapM':total-union,'reportedUnionM':prod['registeredSolidLengthM']})
        if not math.isclose(union,prod['registeredSolidLengthM'],abs_tol=1e-7):discrepancies.append(unions[-1])
g=N['RF01']['geometry'];roof=box(g['x'][0],g['y'][0],g['x'][1],g['y'][1])
roofs=[]
for sid in semantics.SPACE_IDS:
    g=N[sid]['geometry'];rect=box(*g['min'][:2],*g['max'][:2]);area=rect.intersection(roof).area
    prod=next(x for x in A['basicRelations']['roofCoverage'] if x['spaceUid']=='V01:'+sid)
    assert math.isclose(area,prod['coveredAreaM2'],abs_tol=1e-9)
    roofs.append({'space':sid,'areaM2':area,'ratio':area/rect.area})
gi=N['I04']['geometry'];line=LineString([gi['a'],gi['b']]);occupied=[]
for cid in ['C01','C02','C03','C04']:
    occupied += [LineString([line.interpolate(a),line.interpolate(b)]) for a,b in independent_intervals(N[cid],line,1.)]
free=line.difference(unary_union(occupied));gaps=[x.length for x in free.geoms]
assert all(math.isclose(x,2.92,abs_tol=1e-8) for x in gaps) and len(gaps)==3
s=N['S06']['geometry'];t=N['ST01']['geometry'];street=Polygon(list(zip(t['surfaceXY'][::2],t['surfaceXY'][1::2])))
streetArea=street.intersection(box(*s['min'][:2],*s['max'][:2])).area
assert math.isclose(streetArea,2.76,abs_tol=1e-9)
save('independent-geometry.json',{'boundaryRows':rows,'unionChecks':unions,'discrepancies':discrepancies,'undeclaredSideGeometricHits':undeclared_side_hits,'roof':roofs,'I04gapLengthsM':gaps,'streetAreaM2':streetArea})

# Readback mutations: never edit frozen objects/files; never call run_graph.
probes=[]
def probe(name,mutate,runner=analyze,base=P):
    q=copy.deepcopy(base)
    try:
        mutate(q);result=runner(q)
        probes.append({'name':name,'outcome':'accepted','result':result if isinstance(result,bool) else result.get('basicRelations',result)})
    except Exception as e:probes.append({'name':name,'outcome':'rejected','error':type(e).__name__+': '+str(e)})
def node(q,i):return next(n for n in q['nodes'] if n['id']==i)
def rel(q,i):return next(r for r in q['relationships'] if r['id']==i)
probe('reverse_actual_LPG',lambda q:(q['nodes'].reverse(),q['relationships'].reverse()))
probe('missing_actual_boundaryBasis',lambda q:node(q,'S04')['properties'].pop('boundaryBasis'))
probe('changed_actual_local_cache',lambda q:rel(q,'BOUND-S04-C01')['properties'].update(localNetLengthM=99))
probe('missing_actual_column_geometry',lambda q:node(q,'C01')['properties'].pop('geometryJson'))
probe('changed_actual_column_radius',lambda q:node(q,'C01')['properties'].update(geometryJson=json.dumps({**json.loads(node(q,'C01')['properties']['geometryJson']),'radius':.2})))
probe('missing_actual_member_type',lambda q:rel(q,next(r['id'] for r in P['relationships'] if r['source']=='V01:C01' and r['type']=='MEMBER_OF_ZONE')).update(type='ASSOCIATED_WITH'))
probe('missing_actual_C01_source_fields',lambda q:rel(q,'SRC-C01')['properties'].update(fields=[]))
probe('missing_actual_EV01_source_version',lambda q:node(q,'EV01')['properties'].pop('sourceVersion'))
probe('changed_actual_EV01_source_version',lambda q:node(q,'EV01')['properties'].update(sourceVersion='stale'))
probe('missing_actual_boundary_assertionSourceUid',lambda q:rel(q,'BOUND-S04-C01')['properties'].pop('assertionSourceUid'))
probe('changed_actual_boundary_assertionSourceUid',lambda q:rel(q,'BOUND-S04-C01')['properties'].update(assertionSourceUid='V01:EV09'))
probe('missing_actual_boundary_participantRole',lambda q:rel(q,'BOUND-S04-C01')['properties'].pop('participantRole'))
probe('wrong_actual_old_member_target',lambda q:next(r for r in q['relationships'] if r['source']=='V01:C01' and r['type']=='MEMBER_OF_ZONE').update(target='V01:EV09'))
probe('wrong_actual_interface_roles',lambda q:next(r for r in q['relationships'] if r['source']=='V01:I01' and r['properties'].get('role')=='side-b')['properties'].update(role='side-a'))
probe('missing_actual_I04_clearance_warning',lambda q:node(q,'I04')['properties'].pop('clearWidthState'))
probe('canonical_duplicate_I01_side_a_passes_validate_model',lambda q:next(r for r in q['relationships'] if r['source']=='I01' and r['properties'].get('role')=='side-b')['properties'].update(role='side-a'),runner=validate_model,base=M)
probe('canonical_member_target_source_passes_validate_model',lambda q:next(r for r in q['relationships'] if r['source']=='C01' and r['type']=='MEMBER_OF_ZONE').update(target='EV09'),runner=validate_model,base=M)
# Frozen expected output is exact; do not store full successful analysis repeatedly.
for p in probes:
    if isinstance(p.get('result'),dict):
        result=p.pop('result');p['objectCoverageCount']=len(result.get('objectCoverage',[]));p['semanticCompleteness']=result.get('semanticCompleteness');p['agreesWithCandidateBasicRelations']=result==A['basicRelations']
save('mutation-probes.json',probes)

# AST only, no import or execution of run_graph.py.
tree=ast.parse((F/'tools/run_graph.py').read_text()); literals={}
for stmt in tree.body:
    if isinstance(stmt,ast.Assign):
        for target in stmt.targets:
            if isinstance(target,ast.Name) and target.id=='REPLACE':
                expr=stmt.value
                while isinstance(expr,ast.Call) and isinstance(expr.func,ast.Attribute):expr=expr.func.value
                literals['REPLACE']=ast.literal_eval(expr)
q=literals['REPLACE']
assert 'DELETE' not in q and 'DROP' not in q and 'MERGE' not in q
assert q.count('CREATE ')==1 and 'size(additions)=5' in q
save('write-static-check.json',{'notExecuted':True,'singleCreateSite':True,'noDeleteDropMerge':True,'strictFiveAdditions':True,'nativeValueTypeGuards':q.count('valueType('),'note':'AST/string static checks only; no Cypher server execution or planner validation'})
# Execute the actual JSON round-trip equality used by build_review.py:19,
# without importing the prohibited run_graph dependency or running the builder.
serialized=json.loads(json.dumps(A,ensure_ascii=False))
assert A!=serialized
assert json.loads(json.dumps(A))==serialized
leaf=A['basicRelations']['roofCoverage'][0]['intersectionGeoJSON']['coordinates']
leaf2=serialized['basicRelations']['roofCoverage'][0]['intersectionGeoJSON']['coordinates']
save('json-roundtrip-repro.json',{'fullAnalysisRoundtripEqual':A==serialized,'normalizedEqual':json.loads(json.dumps(A))==serialized,'firstMismatchPath':'/basicRelations/roofCoverage/0/intersectionGeoJSON/coordinates','beforeType':type(leaf).__name__,'afterType':type(leaf2).__name__,'leafEqual':leaf==leaf2,'buildReviewFailure':'build_review.py:19 assertion false even for its own freshly serialized analysis; builder not executed'})
drifts=[{'id':i,'before':BR[i]['properties']['evidenceRole'],'after':R[i]['properties']['evidenceRole']} for i in BR if 'evidenceRole' in BR[i]['properties'] and BR[i]['properties']['evidenceRole']!=R[i]['properties'].get('evidenceRole')]
save('evidence-role-drift.json',{'count':len(drifts),'changes':drifts})
# Existing tests are supplemental, after independent computations.
p=subprocess.run([sys.executable,'-B',str(F/'test_semantics.py')],cwd=ROOT,capture_output=True,text=True)
(O/'supplied-tests.txt').write_text(p.stdout+p.stderr)
end=manifest_check();assert end==start
save('verification.json',{'initialManifest':start,'finalManifest':end,'modelNodes':len(M['nodes']),'payloadNodes':len(P['nodes']),'baselineEdges':len(B['relationships']),'candidateEdges':len(M['relationships']),'newEdges':sorted(set(R)-set(BR)),'allGeometryPreserved':True,'EV09Unchanged':True,'compiledPayloadMatchesFrozen':True,'analysisMatchesFrozen':analysis_matches_frozen,'geometryDiscrepancyCount':len(discrepancies),'suppliedTestsExitCode':p.returncode,'mutationProbes':len(probes)})
print(json.dumps({'verification':load_output if False else {'hashes':end,'geometryDiscrepancies':discrepancies,'suppliedTestsExitCode':p.returncode},'probes':probes},ensure_ascii=False,indent=2))
