"""Parameter-only adversarial tests. No bad data is persisted to Neo4j."""
import copy,json,math,tempfile
from pathlib import Path
from compile_model import compile_model,valid_polygon,PREFIX
from analyze import analyze
from workspace import W,CASE
from mcp_client import save
m,p,_=compile_model(W/'candidates'/CASE/'案例模型.json')
G={'nodes':[{'key':n['properties']['uid'],'labels':n['labels'],'properties':n['properties']} for n in p['nodes']],'relationships':[{'key':r['properties']['uid'],'source':r['source'],'target':r['target'],'type':r['type'],'properties':r['properties']} for r in p['relationships']]}
REQ=m['externalExtension']['pathRequests'];RULE=m['externalExtension']['rules'];results=[]
def analyze_g(g):return analyze(g,REQ,RULE)
def prop(g,id):return next(n['properties'] for n in g['nodes'] if n['key']==PREFIX+id)
def edge(g,id):return next(r for r in g['relationships'] if r['key']==PREFIX+id)
def row(r,item,id):return next(x for x in r['items'][item] if x.get('uid')==PREFIX+id)
def area(r):return next(x for x in r['items']['T05'] if x.get('kind')=='area-configuration')
def test(name,mutation,check):
    g=copy.deepcopy(G);mutation(g);r=analyze_g(g);assert check(r),name;results.append({'id':name,'passed':True,'kind':'local-parameter-only'})
def boundary(g,fn):
    p=prop(g,'E-C01');bs=json.loads(p['boundaryRecordsJson']);fn(bs);p['boundaryRecordsJson']=json.dumps(bs)
def polygon(g,id,xy):prop(g,id)['polygonJson']=json.dumps(xy)
b=analyze_g(G)
assert len(b['items'])==6 and len(b['items']['T01'])==8
assert math.isclose(row(b,'T02','E-C01')['ratio'],12/28) and row(b,'T02','E-C02')['ratio']==0.5
assert b['items']['T04'][0]['crossings']==3 and b['items']['T04'][1]['crossings'] is None
assert area(b)['courtyardRatio']==0.3125 and b['useSummary']['knownSpaces']==2 and b['useSummary']['useAssignments']==4
assert all(x['relativePosition'] is not None for x in b['items']['T03'])
results.append({'id':'positive-six-items-and-known-results','passed':True,'kind':'local-projection-only'})
# T01/T05 invalid geometry, units, coordinate frames, denominator and uncertainty.
for field,val in [('geometryComplete',False),('unit','cm'),('level','E-upper'),('coordinateFrame','different'),('geometryBasis','roof-projection'),('geometryVersion','changed')]:
    test('area-'+field,lambda g,f=field,v=val:prop(g,'E-C01').update({f:v}),lambda r:area(r)['status']=='not-computed')
for name,xy in [('zero-area',[[0.,0.],[0.,0.],[0.,0.],[0.,0.]]),('self-intersection',[[2.,2.],[10.,8.],[2.,8.],[10.,2.],[2.,2.]]),('not-closed',[[2.,2.],[10.,2.],[10.,8.],[2.,8.]])]:
    test(name,lambda g,x=xy:polygon(g,'E-C01',x),lambda r:area(r)['status']=='not-computed')
test('outside-denominator',lambda g:polygon(g,'E-U01',[[0.,0.],[5.,0.],[5.,5.],[0.,5.],[0.,0.]]),lambda r:area(r)['status']=='not-computed')
test('area-overlap-union-not-sum',lambda g:polygon(g,'E-G01',[[2.,7.],[10.,7.],[10.,10.],[2.,10.],[2.,7.]]),lambda r:area(r)['status']=='computed' and area(r)['overlapDeductedM2']==8.0 and area(r)['spaceUnionM2']==112.0)
test('geometry-source-field-missing',lambda g:edge(g,'SRC-E-C01')['properties']['fields'].remove('polygonJson'),lambda r:area(r)['status']=='not-computed')
test('source-version-changed',lambda g:prop(g,'EV02').update(sourceVersion='E-2.0'),lambda r:area(r)['status']=='not-computed')
test('source-locator-changed',lambda g:edge(g,'SRC-E-C01')['properties'].update(locator='/wrong'),lambda r:area(r)['status']=='not-computed')
# T02 explicit open is zero, unknown stops full ratio, opening deduction is mandatory.
test('unknown-side-stops',lambda g:boundary(g,lambda bs:bs[3].update(state='unknown',kind='unknown',solidState='unknown')),lambda r:row(r,'T02','E-C01')['status']=='unknown-stopped' and row(r,'T02','E-C01')['ratio'] is None)
test('covered-not-solid',lambda g:boundary(g,lambda bs:bs[0].update(solidIntervalsM=[[0.,8.]])),lambda r:row(r,'T02','E-C01')['status']=='invalid-input')
test('opening-not-deducted',lambda g:boundary(g,lambda bs:bs[2].update(solidIntervalsM=[[0.,8.]])),lambda r:row(r,'T02','E-C01')['status']=='invalid-input')
test('overlap-solid-intervals',lambda g:boundary(g,lambda bs:bs[1].update(solidIntervalsM=[[0.,4.],[3.,6.]])),lambda r:row(r,'T02','E-C01')['status']=='invalid-input')
test('participant-mismatch',lambda g:edge(g,'E-BOUNDARY-E-C01-E').update(target=PREFIX+'E-B02'),lambda r:row(r,'T02','E-C01')['status']=='invalid-input')
test('duplicate-boundary',lambda g:boundary(g,lambda bs:bs[3].update(id='N')),lambda r:row(r,'T02','E-C01')['status']=='invalid-input')
# T03 reference guards; arbitrary bent reference test uses the actual arc, not chord.
for field,val in [('startChainageM',-1.),('endChainageM',99.),('correspondence','ambiguous'),('referenceGeometryVersion','wrong'),('unit','cm')]:
    test('entry-'+field,lambda g,f=field,v=val:prop(g,'E-I01').update({f:v}),lambda r:row(r,'T03','E-I01')['status']=='invalid-input')
test('entry-missing-role',lambda g:g['relationships'].remove(edge(g,'E-I01-side-b')),lambda r:row(r,'T03','E-I01')['status']=='invalid-input')
from shapely.geometry import LineString
line=LineString([[0.,0.],[2.,0.],[2.,4.]])
pt=line.interpolate((1.+5.)/2);assert [pt.x,pt.y]==[2.,1.] and [pt.x,pt.y]!=[1.5,1.5]
results.append({'id':'bent-line-chainage-not-chord-midpoint','passed':True,'kind':'local-geometry-primitive'})
def bent_chain(g):
    p=prop(g,'E-C02');bs=json.loads(p['boundaryRecordsJson']);bs[3]['polyline']=[[2.,10.],[2.,11.],[1.,11.],[1.,13.],[2.,13.],[2.,14.]];p['boundaryRecordsJson']=json.dumps(bs)
    p['polygonJson']=json.dumps([[2.,10.],[10.,10.],[10.,14.],[2.,14.],[2.,13.],[1.,13.],[1.,11.],[2.,11.],[2.,10.]])
    prop(g,'E-I04').update(referencePolylineJson=json.dumps(bs[3]['polyline']),referenceLengthM=float(LineString(bs[3]['polyline']).length),startChainageM=1.,endChainageM=5.)
test('bent-entry-full-analysis-chain',bent_chain,lambda r:row(r,'T03','E-I04')['status']=='computed' and row(r,'T03','E-I04')['centerXY']==[1.,12.])
def wrong_other_side(g):
    prop(g,'E-I02')['toSpaceUid']=PREFIX+'E-C02';edge(g,'E-I02-side-b')['target']=PREFIX+'E-C02'
test('entry-other-side-not-touching',wrong_other_side,lambda r:row(r,'T03','E-I02')['status']=='invalid-input')
def missing_participant(g):
    boundary(g,lambda bs:bs[1].update(participantId=None));g['relationships'].remove(edge(g,'E-BOUNDARY-E-C01-E'))
test('known-building-participant-required',missing_participant,lambda r:row(r,'T02','E-C01')['status']=='invalid-input')
# T04 direction and context are mandatory; missing route never implies unreachable.
for field,val in [('contextId','other'),('actor',''),('actor','another-actor'),('doorState',''),('obstacleState',''),('observationTime',''),('observationTime','different-snapshot'),('state','unknown'),('viaUid',PREFIX+'E-I04'),('sourceVersion','wrong'),('analysisRuleVersion','wrong'),('analysisRuleUid','wrong'),('sourceModelSha256','wrong')]:
    test('passage-'+field+'-'+(val or 'empty'),lambda g,f=field,v=val:edge(g,'ACCESS-E-G01-E-C02')['properties'].update({f:v}),lambda r:r['items']['T04'][0]['status']=='no-confirmed-path-not-unreachable')
test('wrong-access-endpoint',lambda g:edge(g,'ACCESS-E-G01-E-C02').update(target=PREFIX+'E-P01'),lambda r:r['items']['T04'][0]['crossings'] is None)
# T06 no geometry-to-use inference, no type-level claim applied to an instance.
for field,val in [('useScope','type-only'),('useEvidenceRole','inferred-from-geometry'),('useState','unknown'),('useValues',['晾晒','晾晒'])]:
    test('use-'+field,lambda g,f=field,v=val:prop(g,'E-C01').update({f:v}),lambda r:row(r,'T06','E-C01')['state']=='invalid-input')
test('use-missing-source-field',lambda g:edge(g,'SRC-E-C01')['properties']['fields'].remove('useValues'),lambda r:row(r,'T06','E-C01')['state']=='invalid-input')
test('use-explicit-none',lambda g:prop(g,'E-C02').update(useState='none'),lambda r:row(r,'T06','E-C02')['state']=='none')
test('use-not-applicable',lambda g:prop(g,'E-C02').update(useState='not-applicable'),lambda r:row(r,'T06','E-C02')['state']=='not-applicable')
for name,mutation in [('wrong-rule-definition',lambda g:prop(g,'R02').update(definitionJson='{}')),('wrong-rule-version',lambda g:prop(g,'R02').update(ruleVersion='wrong'))]:
    g=copy.deepcopy(G);mutation(g)
    try:analyze_g(g);raise AssertionError(name)
    except ValueError:results.append({'id':name,'passed':True,'kind':'local-parameter-only'})
# The source compiler rejects semantic corruption before any executable payload.
for name,mutation in [('entry-host',lambda x:x['externalExtension']['entrances'][0].update(hostId='E-B01')),('duplicate-use',lambda x:x['externalExtension']['objects'][1].update(useValues=['晾晒','晾晒'])),('wrong-pass-via',lambda x:x['externalExtension']['access'][0].update(via='E-I04')),('wrong-geometry-xy',lambda x:x['externalExtension']['objects'][1]['polygon'][0].append(2.))]:
    bad=copy.deepcopy(m);mutation(bad)
    with tempfile.NamedTemporaryFile(mode='w',suffix='.json',dir=W,delete=False) as f:json.dump(bad,f);path=Path(f.name)
    try:
        try:compile_model(path);raise AssertionError(name)
        except (ValueError,KeyError):results.append({'id':'compiler-'+name,'passed':True,'kind':'local-source-rejection'})
    finally:path.unlink()
assert m['examples']==json.loads((W/'originals'/CASE/'案例模型.json').read_text())['examples']
results.append({'id':'A-D-original-inputs-preserved','passed':True,'kind':'source-equality'})
zr=analyze(G,[{'from':'E-C01','to':'E-C01','contextId':'undeclared'}],RULE)
assert zr['items']['T04'][0]['status']=='invalid-request-context'
results.append({'id':'zero-hop-undeclared-context-rejected','passed':True,'kind':'analysis-request'})
assert len(results)==len({x['id'] for x in results})
save(W/'tests/results.json',{'status':'passed','count':len(results),'tests':results,'scope':'local synthetic/projection and parameter-only; database guards are separately executed'})
print(json.dumps({'status':'passed','count':len(results)}))
