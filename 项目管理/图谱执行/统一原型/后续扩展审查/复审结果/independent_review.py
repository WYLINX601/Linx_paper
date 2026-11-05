"""Independent second review. All test mutations are in memory/output only."""
import ast
import copy
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path

ROOT = Path('/Users/wangyuelin/.hermes/profiles/academic/cache/scratch/prototype-next-ozht7hck/review2-fixed')
OUT = ROOT.parent / 'review2-output'
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
import compile_model as cm
import analyze as az
import projection as pr
import d04
import d05
import d06

M, P = cm.compile_model(ROOT / 'candidate/model.json')
A = az.analyze(P)
RESULTS = []

def n(m, id):
    return next(x for x in m['nodes'] if x['id'] == id)

def pn(p, id):
    return next(x for x in p['nodes'] if x['properties']['uid'] == 'V01:' + id)

def check(ok, message):
    if not ok:
        raise AssertionError(message)

def close(a, b):
    check(math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10), f'{a} != {b}')

def run(id, fn):
    try:
        detail = fn()
        RESULTS.append({'id': id, 'passed': True, 'detail': detail})
    except Exception as e:
        RESULTS.append({'id': id, 'passed': False, 'error': str(e), 'traceback': traceback.format_exc()})

def reject(fn, contains=None):
    try:
        fn()
    except ValueError as e:
        if contains:
            check(contains in str(e), 'Unexpected rejection: ' + str(e))
        return {'rejected': True, 'exception': type(e).__name__, 'message': str(e)}
    raise AssertionError('Invalid input accepted')

def compiled_case(q):
    path = OUT / 'mutated-model.json'
    path.write_text(json.dumps(q, ensure_ascii=False))
    return cm.compile_model(path)[1]

def baseline():
    check(P == json.loads((ROOT/'candidate/payload.json').read_text()), 'payload mismatch')
    check(A == json.loads((ROOT/'candidate/analysis.json').read_text()), 'analysis mismatch')
    check(P['sourceModelSha256'] == '34d8c27da739f94eac856b7c975959de17558c1acbd00c6415e49261baa1387a', 'SHA mismatch')
    check(len(P['nodes']) == 56 and len(P['relationships']) == 285, 'count mismatch')
    check(set(A['D06']) == {'T01','T02','T03','T04','T05'}, 'D06 not five tasks')
    new = {'B03','CG01','ST01','TP01'}
    check(new <= {x['id'] for x in M['nodes']}, 'new ids')
    check(len([x for x in P['nodes'] if x['id'] not in new]) == 52, 'old projection count')
    check(sum(x['class']=='Building' for x in M['nodes']) == 3, 'building count')
    return {'payloadEqualsFrozen': True, 'analysisEqualsFrozen': True, 'modelObjects':len(M['nodes']), 'projectedNodesIncludingSOURCE':len(P['nodes']), 'projectedNonNewNodesIncludingSOURCE':52, 'relationships':len(P['relationships']), 'BuildingObjects':3, 'D06Tasks':list(A['D06'])}
run('baseline_recompile_analyze_counts_sha', baseline)

# Reconstruct the exact former F01 partition, not import its test helper.
def material_model(last_state='known', positive=False):
    q = copy.deepcopy(M)
    rec = n(q,'W03')['properties']['facadeRecords'][0]
    template = rec['surfaceRegions'][0]
    specs = [([0,0,9.6,1],'灰泥'),([0,1,1,2],'灰泥'),([2.2,1,9.6,2],'灰泥'),([0,2,9.6,3.6],'灰泥'),([1,1,2.2,2],'砖')]
    rec['surfaceRegions'] = [dict(copy.deepcopy(template),id='independent-region-'+str(i),rectUZ=rect,material=mat) for i,(rect,mat) in enumerate(specs)]
    if last_state != 'known':
        rec['surfaceRegions'][-1].update(state=last_state,material=None)
    if positive:
        rec['surfaceRegions'][0]['material'] = '砖'
    return q

def material_test(state, positive=False, lpg=False):
    q = material_model(state, positive)
    check(cm.validate_model(q), 'invalid constructed input')
    if lpg:
        p = copy.deepcopy(P)
        pn(p,'W03')['properties']['facadeRecordsJson'] = cm.dumps(n(q,'W03')['properties']['facadeRecords'])
        a = az.analyze(p)
        check(pn(p,'SOURCE')['properties']['rawModelJson'] == pn(P,'SOURCE')['properties']['rawModelJson'], 'snapshot changed')
        f, g = a['D04'], a['D06']
    else:
        p = compiled_case(q)
        a = az.analyze(p)
        f, g = a['D04'], a['D06']
    s = next(x for x in f['T03'] if x['hostId']=='W03')
    combination = next(x for x in f['T06'] if x['hostId']=='W03')['combination']
    row = next(x for x in g['T01']['localFacadeMatrix'] if x['hostId']=='W03')
    allocation = next(x for x in g['T03']['allocations'] if x['unitId']=='D04-W03-N' and x['schemeId']=='complete-surface-material')
    close(s['netDomainAreaM2'], 9.6*3.6 - 3*1.2)
    close(s['unknownAreaM2'], 0)
    check(s['state']=='known' and len(s['zeroNetSurfaceRegions'])==1, 'state/diagnostics')
    check(s['unresolvedParts']==[], 'zero net unresolved leaked')
    check(row['fields']['completeMaterialCount']==(2 if positive else 1), 'material count')
    check(all(v>0 for v in s['materialAreasM2'].values()), 'zero area in table')
    check(set(combination['materials'])==({'灰泥','砖'} if positive else {'灰泥'}), 'zero area in combination')
    check(allocation['matches']==['multiple-materials-complete-domain' if positive else 'single-material-complete-domain'], 'classification')
    if positive:
        close(s['materialAreasM2']['砖'],9.6)
        close(s['materialAreasM2']['灰泥'],21.36)
    else:
        close(s['materialAreasM2']['灰泥'],30.96)
    return {'path':'actual-LPG-unchanged-rawModel' if lpg else 'compile-then-analyze','lastRegionState':state,'materialAreasM2':s['materialAreasM2'],'unknownAreaM2':s['unknownAreaM2'],'combinationMaterials':combination['materials'],'diagnostics':s['zeroNetSurfaceRegions'],'completeMaterialCount':row['fields']['completeMaterialCount'],'classification':allocation['matches']}
for state, positive, label in [('known',False,'old_counterexample'),('known',True,'true_two_positive_materials'),('unknown',False,'zero_unknown'),('mixed',False,'zero_mixed')]:
    for lpg in [False,True]:
        run('F01_'+label+('_LPG' if lpg else '_compiled'), lambda s=state,p=positive,l=lpg:material_test(s,p,l))

def positive_unknown():
    p=copy.deepcopy(P)
    records=json.loads(pn(p,'W03')['properties']['facadeRecordsJson'])
    records[0]['surfaceRegions'][0].update(state='unknown',material=None)
    pn(p,'W03')['properties']['facadeRecordsJson']=cm.dumps(records)
    a=az.analyze(p)
    s=a['D04']['T03'][0]
    check(s['state']=='unknown' and s['materialAreasM2']=={},'unknown allocated')
    close(s['unknownAreaM2'],30.96)
    check(a['D06']['T01']['localFacadeMatrix'][0]['fields']['completeMaterialCount'] is None,'unknown count imputed')
    check(a['D06']['T02']['jointValidCount']==0,'joint unknown imputed')
    return {'unknownAreaM2':s['unknownAreaM2'],'completeMaterialCount':None,'jointValidCount':0}
run('F01_positive_unknown_remains_unknown',positive_unknown)

# F02: actual geometry must dominate the unchanged raw snapshot.
def c01_missing():
    p=copy.deepcopy(P);del pn(p,'C01')['properties']['geometryJson']
    return reject(lambda:az.analyze(p),'Missing actual geometry C01')
run('F02_missing_actual_C01',c01_missing)

def changed_c01(update_cache):
    p=copy.deepcopy(P);g=json.loads(pn(p,'C01')['properties']['geometryJson']);g['radius']=1.0
    pn(p,'C01')['properties']['geometryJson']=cm.dumps(g)
    if not update_cache:
        return reject(lambda:az.analyze(p),'Boundary cache differs')
    expected=cm.boundary_qualification(pr.rehydrate(p))
    for r in p['relationships']:
        if r['id'] in expected:r['properties'].update(expected[r['id']])
    a=az.analyze(p)
    participant=next(x for b in a['D03']['T02']['segments'] for x in b['participants'] if x['uid']=='V01:C01')
    close(participant['contributionM'],0.88)
    close(a['D03']['T02']['netSolidBoundaryM'],18.58)
    close(a['D03']['T02']['netSolidRatio'],18.58/28.08)
    check(pn(p,'SOURCE')['properties']['rawModelJson']==pn(P,'SOURCE')['properties']['rawModelJson'],'snapshot changed')
    return {'actualRadius':1.0,'contributionM':participant['contributionM'],'netSolidBoundaryM':a['D03']['T02']['netSolidBoundaryM'],'netSolidRatio':a['D03']['T02']['netSolidRatio'],'rawModelUnchanged':True}
run('F02_changed_actual_C01_stale_cache_stops',lambda:changed_c01(False))
run('F02_changed_actual_C01_current_cache_recomputes',lambda:changed_c01(True))

# Complete identity-set rejection; projection and end-to-end analysis separately.
def identity_case(kind, direct):
    p=copy.deepcopy(P)
    if kind=='extra-pair':
        r=copy.deepcopy(next(x for x in p['relationships'] if x['source']=='V01:I05' and x['target']=='V01:S05' and x['type']=='INTERFACE_OF' and x['properties'].get('role')=='side-a'))
        r['id']='EXTRA';r['properties'].update(id='EXTRA',uid='V01:EXTRA');p['relationships'].append(r)
    elif kind=='duplicate-edge':p['relationships'].append(copy.deepcopy(p['relationships'][0]))
    elif kind=='missing-edge':p['relationships'].pop()
    elif kind=='extra-node':
        x=copy.deepcopy(p['nodes'][0]);x['id']='EXTRA';x['properties'].update(id='EXTRA',uid='V01:EXTRA');p['nodes'].append(x)
    elif kind=='duplicate-node':p['nodes'].append(copy.deepcopy(p['nodes'][0]))
    elif kind=='missing-node':p['nodes'].remove(pn(p,'B03'))
    elif kind=='edge-caseId':p['relationships'][0]['properties']['caseId']='OTHER'
    elif kind=='node-datasetId':p['nodes'][0]['properties']['datasetId']='OTHER'
    return reject(lambda:(pr.rehydrate if direct else az.analyze)(p))
for kind in ['extra-pair','duplicate-edge','missing-edge','extra-node','duplicate-node','missing-node','edge-caseId','node-datasetId']:
    for direct in [True,False]:
        run('F03_'+kind+('_projection' if direct else '_analysis'),lambda k=kind,d=direct:identity_case(k,d))

def actual_metadata():
    p=copy.deepcopy(P)
    p['relationships'][0]['properties'].update(recordStatus='changed-status',evidenceIds=['EV08'])
    pn(p,'B01')['properties']['evidenceIds']=['EV08']
    q=pr.rehydrate(p)
    r=next(x for x in q['relationships'] if x['id']==p['relationships'][0]['id'])
    check(r['status']=='changed-status' and r['evidence']==['EV08'],'relationship actual metadata ignored')
    check(n(q,'B01')['evidence']==['EV08'],'node actual evidence ignored')
    del p['relationships'][0]['properties']['recordStatus'];del p['relationships'][0]['properties']['evidenceIds']
    r=next(x for x in pr.rehydrate(p)['relationships'] if x['id']==p['relationships'][0]['id'])
    check(r['status'] is None and r['evidence']==[],'missing actual metadata fell back')
    return {'relationshipStatusEvidenceFromActual':True,'nodeEvidenceFromActual':True,'missingRelationshipMetadataNoFallback':True}
run('F03_actual_status_evidence_and_no_fallback',actual_metadata)

def source_positive(id):
    idx=next(i for i,x in enumerate(M['nodes']) if x['id']==id)
    loc=n(M,id)['properties']['geometrySourceLocator']
    target=M
    for token in loc.split('/')[1:]:target=target[int(token)] if isinstance(target,list) else target[token]
    check(target==n(M,id)['geometry'] and loc==f'/nodes/{idx}/geometry','pointer does not resolve self geometry')
    check(n(M,id)['properties']['geometrySourceVersion']==M['modelVersion'],'source version')
    return {'id':id,'locator':loc,'version':M['modelVersion'],'resolvedSelfGeometry':True}

def source_negative(id, mutation, lpg):
    field='geometrySourceLocator' if 'locator' in mutation else 'geometrySourceVersion'
    q=copy.deepcopy(P if lpg else M)
    props=(pn(q,id) if lpg else n(q,id))['properties']
    if mutation.startswith('missing'):del props[field]
    else:props[field]='/nodes/9/geometry' if field=='geometrySourceLocator' else 'stale-version'
    return reject(lambda:az.analyze(q) if lpg else compiled_case(q))
for id in ['B03','CG01','ST01','TP01']:
    run('F04_'+id+'_positive_self_pointer_version',lambda i=id:source_positive(i))
    for mutation in ['wrong-locator','stale-version','missing-locator','missing-version']:
        for lpg in [False,True]:
            run('F04_'+id+'_'+mutation+('_LPG' if lpg else '_compiler'),lambda i=id,m=mutation,l=lpg:source_negative(i,m,l))

def actual_w10_material():
    p=copy.deepcopy(P);props=pn(p,'W10')['properties'];rec=json.loads(props['facadeRecordsJson'])
    rec[0]['surfaceRegions'][1].update(state='known',material='砖');props['facadeRecordsJson']=cm.dumps(rec)
    a=az.analyze(p);s=a['D04']['T03'][1];row=a['D06']['T01']['localFacadeMatrix'][1]
    check(s['state']=='known' and row['fields']['completeMaterialCount']==2,'actual material not recomputed')
    close(s['materialAreasM2']['灰泥'],6.4);close(s['materialAreasM2']['砖'],6.4)
    check(pn(p,'SOURCE')['properties']['rawModelJson']==pn(P,'SOURCE')['properties']['rawModelJson'],'raw snapshot changed')
    return {'materialAreasM2':s['materialAreasM2'],'completeMaterialCount':2,'rawModelUnchanged':True}
run('actual_W10_two_materials_from_LPG',actual_w10_material)

# Source/facade regression: deleting actual properties cannot revive rawModel values.
def missing_actual_facade():
    p=copy.deepcopy(P);del pn(p,'W03')['properties']['facadeRecordsJson']
    return reject(lambda:az.analyze(p))
run('missing_actual_facade_stops',missing_actual_facade)

def stale_actual_facade_source():
    p=copy.deepcopy(P);r=next(x for x in p['relationships'] if x['id']=='X-SRC-W03');r['properties']['sourceVersion']='stale'
    return reject(lambda:az.analyze(p),'Unsupported extension field W03.facadeRecords')
run('stale_actual_facade_source_stops',stale_actual_facade_source)

def actual_extension_edge_metadata(field):
    p=copy.deepcopy(P);r=next(x for x in p['relationships'] if x['id']=='D04-FACADE-W03');r['properties'][field]='bad' if field=='recordStatus' else ['EV08']
    return reject(lambda:az.analyze(p),'participant source boundary')
for field in ['recordStatus','evidenceIds']:
    run('actual_facade_edge_'+field+'_not_snapshot',lambda f=field:actual_extension_edge_metadata(f))

# Extract only pure verifier functions. Do NOT import run_graph/mcp_client.
source=(ROOT/'tools/run_graph.py').read_text();tree=ast.parse(source)
wanted={'native_type','binding','verify_exact','preserve_original_geometry'}
selected=ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in wanted],type_ignores=[])
ns={'copy':copy,'json':json,'require':cm.require}
exec(compile(selected,str(ROOT/'tools/run_graph.py'),'exec'),ns)

def readback(p):
    g=copy.deepcopy(p)
    for category in ['nodes','relationships']:
        for row in g[category]:
            row['key']=row['properties']['uid']
            row['types']=[{'key':k,'type':ns['native_type'](v)} for k,v in row['properties'].items() if ns['native_type'](v)]
    return g
G=readback(P)
run('postwrite_exact_positive',lambda:{'verified':ns['verify_exact'](G,P)})

def verifier_negative(kind):
    g=copy.deepcopy(G)
    if kind=='property':g['nodes'][0]['properties']['name']='changed'
    elif kind=='native-equal-value':
        row=next(x for x in g['nodes'] if x['key']=='V01:B02');row['properties']['eaveZM']=7
        next(x for x in row['types'] if x['key']=='eaveZM')['type']='INTEGER NOT NULL'
    elif kind=='extra-edge':
        row=copy.deepcopy(g['relationships'][0]);row['key']='V01:EXTRA';row['properties']['uid']='V01:EXTRA';g['relationships'].append(row)
    elif kind=='duplicate-edge':g['relationships'].append(copy.deepcopy(g['relationships'][0]))
    elif kind=='extra-node':
        row=copy.deepcopy(g['nodes'][0]);row['key']='V01:EXTRA';row['properties']['uid']='V01:EXTRA';g['nodes'].append(row)
    elif kind=='endpoint':g['relationships'][0]['target']='V01:B03'
    elif kind=='type':g['relationships'][0]['type']='HAS_SOURCE'
    elif kind=='label':g['nodes'][0]['labels'].append('Unauthorized')
    elif kind=='missing-edge':g['relationships'].pop()
    return reject(lambda:ns['verify_exact'](g,P))
for kind in ['property','native-equal-value','extra-edge','duplicate-edge','extra-node','endpoint','type','label','missing-edge']:
    run('postwrite_exact_reject_'+kind,lambda k=kind:verifier_negative(k))

def binding_copy():
    b=ns['binding'](P);b['frozenNodes'][0]['properties']['name']='changed'
    check(P['nodes'][0]['properties']['name']!='changed','binding alias')
    check(len(b['frozenNodes'])==56 and len(b['frozenRelationships'])==285,'binding incomplete')
    return {'isolatedFrozenPayload':True,'nodes':56,'relationships':285}
run('prewrite_binding_isolated_full_payload',binding_copy)
run('geometry_preservation_positive',lambda:{'verified':ns['preserve_original_geometry'](M,G)})

def preserve_negative():
    q=copy.deepcopy(M);n(q,'C01')['geometry']['radius']=1.0
    return reject(lambda:ns['preserve_original_geometry'](q,G),'Original geometry changed C01')
run('geometry_preservation_reject_changed_C01',preserve_negative)

# Independent numeric controls within the fixed prototype.
def numeric_controls():
    f=A['D04'];g=A['D05']
    close(f['T01'][0]['grossAreaM2'],9.6*3.6)
    close(f['T02'][0]['openingUnionAreaM2'],3*1.2)
    close(g['T03']['pavementWidthM'],(-4.8-0.24/2)-(-8.8))
    close(g['T03']['sides']['left']['knownEntityProportion'],(9.6-1.6)/9.6)
    close(g['T04']['slopeRatio'],3/math.hypot(0.4,3.8))
    check(g['T04']['thresholdToSamePointPavement']['status']=='unknown','unsupported same-point inferred')
    return {'independentRectangleAndOpeningArea':True,'streetWidthAndEntityRatio':True,'groundSlope':True,'unsupportedSamePointRemainsUnknown':True}
run('fixed_prototype_independent_numeric_controls',numeric_controls)

loaded={name:str(Path(mod.__file__).resolve()) for name,mod in sys.modules.items() if getattr(mod,'__file__',None) and name in ['compile_model','analyze','projection','d04','d05','d06','mcp_client','run_graph']}
check('mcp_client' not in loaded and 'run_graph' not in loaded,'prohibited module imported')
check(all(Path(path).is_relative_to(ROOT) for path in loaded.values()),'project module imported outside frozen root')
report={'countMeaning':'Each result is one named independent scenario (may contain multiple assertions). Expected rejection is a pass. Not a count of assertions, database executions, or real samples. Bundled suite is counted separately.','scenarioCount':len(RESULTS),'passed':sum(x['passed'] for x in RESULTS),'failed':sum(not x['passed'] for x in RESULTS),'loadedProjectModules':loaded,'pureVerifierExtraction':sorted(wanted),'results':RESULTS}
(OUT/'independent-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False,indent=2))
for x in RESULTS:
    if not x['passed']:print(json.dumps(x,ensure_ascii=False,indent=2))
sys.exit(1 if report['failed'] else 0)
