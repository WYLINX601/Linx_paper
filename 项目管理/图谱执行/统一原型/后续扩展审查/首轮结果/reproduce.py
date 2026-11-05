"""Read-only frozen review. Run with python -B; no DB imports or IO writes."""
import sys, json, pathlib, copy, hashlib, math, ast
ROOT = pathlib.Path('/Users/wangyuelin/.hermes/profiles/academic/cache/scratch/prototype-next-ozht7hck/review-fixed')
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
import d04, d05, d06, projection, compile_model, analyze
for module in (d04,d05,d06,projection,compile_model,analyze):
    assert pathlib.Path(module.__file__).parent == ROOT/'tools'
m = json.loads((ROOT/'candidate/model.json').read_text())
p = json.loads((ROOT/'candidate/payload.json').read_text())
a = json.loads((ROOT/'candidate/analysis.json').read_text())
o = json.loads((ROOT/'originals/model.json').read_text())
def node(m,id): return next(n for n in m['nodes'] if n['id']==id)
def pn(g,id): return next(n for n in g['nodes'] if n['properties']['uid']=='V01:'+id)
def edge(m,id): return next(r for r in m['relationships'] if r['id']==id)
def run(name,fn):
    try: print(json.dumps({'test':name,'result':fn()},ensure_ascii=False,default=str))
    except Exception as e: print(json.dumps({'test':name,'exception':type(e).__name__,'message':str(e)},ensure_ascii=False))
def baseline():
    mm,pp=compile_model.compile_model(ROOT/'candidate/model.json')
    aa=analyze.analyze(p)
    return {'valid':compile_model.validate_model(m),'payloadEqual':pp==p,'analysisEqual':aa==a,'D06Items':list(aa['D06']), 'counts':[len(mm['nodes']),len(pp['nodes']),len(pp['relationships'])], 'D04':[{'region':x['regionId'],'net':x['netDomainAreaM2'],'known':x['knownAreaM2'],'unknown':x['unknownAreaM2']} for x in aa['D04']['T03']]}
run('baseline',baseline)
def old_changes():
    changes=[]
    for n in o['nodes']:
        now=node(m,n['id'])
        if n['geometry']!=now['geometry'] or any(n[k]!=now[k] for k in ['id','name','class','labels','evidence']): raise AssertionError(n['id'])
        for k,v in n['properties'].items():
            if now['properties'].get(k)!=v: changes.append([n['id'],k,v,now['properties'].get(k)])
    ro={r['id']:r for r in m['relationships']}
    structural=[r['id'] for r in o['relationships'] if r['id'] not in ro or any(r[k]!=ro[r['id']][k] for k in ['source','target','type','status','evidence'])]
    return {'oldGeometryAndIdentityUnchanged':True,'oldRelationshipSemanticChanges':structural,'changedPropertyKeys':sorted(set(x[1] for x in changes)), 'nonVersionChanges':[x for x in changes if x[1] not in ['geometryVersion','analysisItems','areaScopeVersion','sourceVersion','frameVersion','inputGeometryVersion','correspondenceVersion','boundaryVersion','version']]}
run('old_identity_semantics',old_changes)
def zero_material():
    q=copy.deepcopy(m);r=node(q,'W03')['properties']['facadeRecords'][0];t=r['surfaceRegions'][0]
    specs=[([0,0,9.6,1],'灰泥'),([0,1,1,2],'灰泥'),([2.2,1,9.6,2],'灰泥'),([0,2,9.6,3.6],'灰泥'),([1,1,2.2,2],'砖')]
    r['surfaceRegions']=[dict(copy.deepcopy(t),id=t['id']+'-'+str(i),rectUZ=b,material=mat) for i,(b,mat) in enumerate(specs)]
    valid=compile_model.validate_model(q);s=d04.analyze(q)['T03'][0];res=d06.analyze(q)
    return {'compilerAccepted':valid,'materialAreasM2':s['materialAreasM2'],'materialState':s['state'],'completeMaterialCount':res['T01']['localFacadeMatrix'][0]['fields']['completeMaterialCount'],'classification':[v for v in res['T03']['allocations'] if v['unitId']=='D04-W03-N' and v['schemeId']=='complete-surface-material']}
run('zero_net_material_changes_classification',zero_material)
def geom_provenance():
    q=copy.deepcopy(m);prop=node(q,'B03')['properties'];old={k:v for k,v in prop.items() if k.startswith('geometrySource')};prop['geometrySourceLocator']='/nodes/9/geometry';prop['geometrySourceVersion']='stale-version'
    return {'before':old,'compilerAccepted':compile_model.validate_model(q)}
run('new_geometry_wrong_locator_version',geom_provenance)
def missing(id,key):
    g=copy.deepcopy(p);del pn(g,id)['properties'][key]
    return analyze.analyze(g)['D06']['T01']['buildingElevationMatrix']
run('missing_actual_facade_rejected',lambda:missing('W03','facadeRecordsJson'))
run('missing_actual_B03_eave_rejected',lambda:missing('B03','eaveZM'))
def extra_pair():
    g=copy.deepcopy(p);r=copy.deepcopy(next(r for r in g['relationships'] if r['source']=='V01:I05' and r['target']=='V01:S05' and r['type']=='INTERFACE_OF'));r['id']='EXTRA';r['properties']['uid']='V01:EXTRA';r['properties']['id']='EXTRA';g['relationships'].append(r)
    out=analyze.analyze(g)
    return {'extraActualPairIgnored':True,'localPairs':out['D06']['T02']['localPairs'],'rehydratedRelationshipCount':len(projection.rehydrate(g)['relationships']),'actualRelationshipCount':len(g['relationships'])}
run('extra_actual_pair_relationship',extra_pair)
def changed_geom():
    g=copy.deepcopy(p);n=pn(g,'C01');gg=json.loads(n['properties']['geometryJson']);gg['radius']=1.0;n['properties']['geometryJson']=json.dumps(gg)
    out=analyze.analyze(g)
    return {'geometry':gg,'enclosureUnchanged':out['D03']['T02']==a['D03']['T02'],'enclosureRatio':out['D03']['T02']['netSolidRatio']}
run('actual_C01_geometry_vs_rawModel',changed_geom)
def missing_legacy_geom():
    g=copy.deepcopy(p);del pn(g,'C01')['properties']['geometryJson'];out=analyze.analyze(g)
    return {'enclosureUnchanged':out['D03']['T02']==a['D03']['T02']}
run('missing_actual_C01_geometry',missing_legacy_geom)
def valid_source_mutation():
    q=copy.deepcopy(m);edge(q,'X-SRC-W03')['properties']['locator']='/nodes/0/properties';return compile_model.validate_model(q)
run('wrong_facade_source_pointer_rejected',valid_source_mutation)
def actual_material():
    g=copy.deepcopy(p);pp=pn(g,'W10')['properties'];rr=json.loads(pp['facadeRecordsJson']);rr[0]['surfaceRegions'][1]['state']='known';rr[0]['surfaceRegions'][1]['material']='灰泥';pp['facadeRecordsJson']=json.dumps(rr)
    out=analyze.analyze(g)
    return {'wholeShares':out['D04']['T03'][1]['wholeDomainShares'],'jointValidIds':out['D06']['T02']['jointValidUnitIds'],'rawSnapshotUnchanged':pn(g,'SOURCE')['properties']['rawModelJson']==pn(p,'SOURCE')['properties']['rawModelJson']}
run('actual_material_recomputed',actual_material)
def joint_unknown():
    q=copy.deepcopy(m);r=node(q,'W03')['properties']['facadeRecords'][0]['surfaceRegions'][0];r.update(state='unknown',material=None);z=d06.analyze(q)
    return {'joint':z['T02']['jointValidUnitIds'],'wholeFrequency':z['T02']['wholeBuildingCombinationFrequency'],'localPairs':len(z['T02']['localPairs'])}
run('both_material_unknown_joint_empty',joint_unknown)
def source_missing():
    q=copy.deepcopy(m);edge(q,'X-SRC-W03')['properties']['fields'].remove('facadeRecords');return compile_model.validate_model(q)
run('missing_facade_source_rejected',source_missing)
def version_mutation():
    q=copy.deepcopy(m);node(q,'W10')['properties']['facadeRecords'][0]['geometryVersion']='stale';return compile_model.validate_model(q)
run('stale_facade_version_rejected',version_mutation)
def pairing_mutation():
    q=copy.deepcopy(m);q['analysisContract']['D06']['localPairs'][0]['facadeHostId']='W03';return compile_model.validate_model(q)
run('wrong_explicit_pair_rejected',pairing_mutation)
def scheme_cases():
    s=d06.schemes()[0];conf=copy.deepcopy(s);conf['rules'].append({'code':'overlap','when':{'openingCount':{'ge':1}}})
    return {str(v):d06.classify({'openingCount':v},s)['state'] for v in [None,0,1,3]}|{'conflict':d06.classify({'openingCount':1},conf)['state']}
run('classification_unknown_unmatched_conflict',scheme_cases)
# Extract pure verification functions only; do not import mcp_client or run_graph.
tree=ast.parse((ROOT/'tools/run_graph.py').read_text());selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['native_type','verify_exact','preserve_original_geometry']];ns={'json':json,'require':compile_model.require};exec(compile(ast.Module(body=selected,type_ignores=[]),'frozen-run_graph-pure-functions','exec'),ns)
def readback(g):
    out=copy.deepcopy(g)
    for k in ['nodes','relationships']:
        for row in out[k]:
            row['key']=row['properties']['uid'];row['types']=[{'key':key,'type':ns['native_type'](v)} for key,v in row['properties'].items() if ns['native_type'](v)]
    return out
run('postwrite_exact_positive',lambda:ns['verify_exact'](readback(p),p))
def verify_bad(kind):
    g=readback(p)
    if kind=='property':pn(g,'B03')['properties']['eaveZM']=4
    elif kind=='type':next(x for x in pn(g,'B03')['types'] if x['key']=='eaveZM')['type']='FLOAT NOT NULL'
    elif kind=='extra-edge':g['relationships'].append(copy.deepcopy(g['relationships'][0]))
    return ns['verify_exact'](g,p)
for kind in ['property','type','extra-edge']:run('postwrite_exact_reject_'+kind,lambda kind=kind:verify_bad(kind))
print(json.dumps({'test':'hashes_after','result':{k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in json.loads((ROOT/'manifest.json').read_text()).items()}}))
