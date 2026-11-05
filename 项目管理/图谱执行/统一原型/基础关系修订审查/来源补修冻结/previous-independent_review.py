"""Independent bounded review. Run with -B; never imports graph runner/client.
Reads only review2-fixed and its own review2-output receipts. All writes here.
"""
import ast, copy, hashlib, json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / 'review2-fixed'
OUT = ROOT / 'review2-output'
sys.dont_write_bytecode = True
sys.path.insert(0, str(FIX / 'tools'))
from compile_model import compile_model, validate_model
from analyze import analyze
import semantics

def load(p):
    return json.loads((FIX / p).read_text())
def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
def node(m, uid):
    return next(n for n in m['nodes'] if n['id'] == uid)
def rel(m, uid):
    return next(r for r in m['relationships'] if r['id'] == uid)
def upgrade(v):
    if isinstance(v, dict): return {k: upgrade(x) for k, x in v.items()}
    if isinstance(v, list): return [upgrade(x) for x in v]
    return 'V01-unified-2.2' if v == 'V01-unified-2.1' else v

def diff(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        result=[]
        for k in sorted(a.keys() | b.keys()):
            p=path+'/'+k
            if k not in a: result.append({'path':p,'kind':'added','new':b[k]})
            elif k not in b: result.append({'path':p,'kind':'removed','old':a[k]})
            else: result.extend(diff(a[k],b[k],p))
        return result
    if a != b: return [{'path':path,'kind':'changed','old':a,'new':b}]
    return []

BASE=load('baseline/model-2.1.json')
M,P=compile_model(FIX/'candidate/model.json')
A=analyze(P)
checks={}
checks['compiled_payload_equals_frozen']=P == load('candidate/payload.json')
(OUT/'analysis-roundtrip.json').write_text(json.dumps(A,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
checks['full_analysis_disk_json_roundtrip_equal']=A==json.loads((OUT/'analysis-roundtrip.json').read_text())
checks['current_analysis_equals_recomputed']=A==load('candidate/analysis.json')
checks['roof_geojson_native_roundtrip']=semantics.roof_coverage(M)==json.loads(json.dumps(semantics.roof_coverage(M),allow_nan=False))

def native(v):
    if isinstance(v,dict): return all(type(k) is str and native(x) for k,x in v.items())
    if isinstance(v,list): return all(native(x) for x in v)
    return v is None or type(v) in (str,bool,int) or type(v) is float and math.isfinite(v)
checks['analysis_strict_json_native']=native(A)
checks['model_node_order_identity_unchanged']=[n['id'] for n in BASE['nodes']]==[n['id'] for n in M['nodes']]
BN={n['id']:n for n in BASE['nodes']}; MN={n['id']:n for n in M['nodes']}
BR={r['id']:r for r in BASE['relationships']}; MR={r['id']:r for r in M['relationships']}
checks['all_original_geometry_unchanged']=all(n['geometry']==MN[i]['geometry'] for i,n in BN.items())
checks['all_old_relation_ids_retained']=BR.keys()<=MR.keys()
checks['old_relation_endpoints_types_and_metadata_unchanged']=all({k:v for k,v in r.items() if k!='properties'}=={k:v for k,v in MR[i].items() if k!='properties'} for i,r in BR.items())
checks['old_evidence_roles_exactly_preserved']=all(r['properties'].get('evidenceRole')==MR[i]['properties'].get('evidenceRole') for i,r in BR.items())
newids=sorted(MR.keys()-BR.keys())
expected=['BOUND-S04-C01','BOUND-S04-C02','BOUND-S04-C03','BOUND-S04-C04','BOUND-S06-W10']
checks['only_five_authorized_boundary_edges']=newids==expected and all(MR[i]['type']=='BOUNDARY_PARTICIPANT' for i in newids)
local={'localBoundaryIds','rangeState','analysisSliceZM','geometryVersion','localRuleVersion','localRangeBasis'}
spaceprops={'boundaryBasis','analysisSliceZM','boundarySegments','overallCoverType','coverStateMeaning','boundaryCoverStateMeaning','coverState'}
origins={'boundaryBasis','analysisSliceZM','boundarySegments','overallCoverType','coverStateMeaning'}
unapproved=[]; deltas=[]
for i,n in BN.items():
    changes=diff(upgrade(n),MN[i],'/nodes/'+i)
    deltas.extend(changes)
    for d in changes:
        tail=d['path'].split('/')[3:]
        allowed=i in semantics.SPACE_IDS and len(tail)>=2 and ((tail[0]=='properties' and tail[1] in spaceprops) or (tail[0]=='propertyOrigins' and tail[1] in origins))
        if not allowed: unapproved.append(d)
for i,r in BR.items():
    allowed=local if r['type']=='BOUNDARY_PARTICIPANT' else {'fields'} if i in {'SRC-'+s for s in semantics.SPACE_IDS} else set()
    changes=diff(upgrade(r),MR[i],'/relationships/'+i);deltas.extend(changes)
    for d in changes:
        tail=d['path'].split('/')[3:]
        if not (len(tail)>=2 and tail[0]=='properties' and tail[1] in allowed):unapproved.append(d)
checks['no_unauthorized_old_record_deltas']=not unapproved
checks['EV09_entire_node_unchanged']=BN['EV09']==MN['EV09'] and MN['EV09']['properties']['sourceVersion']=='1.1'
save('preservation.json',{'counts':{'baselineNodes':len(BN),'candidateNodes':len(MN),'payloadNodes':len(P['nodes']),'oldRelationships':len(BR),'newRelationships':len(MR)},'newIds':newids,'oldRecordDeltasAfterExactVersionUpgrade':deltas,'unapproved':unapproved,'topLevelDeltas':diff({k:upgrade(v) for k,v in BASE.items() if k not in ['nodes','relationships']},{k:v for k,v in M.items() if k not in ['nodes','relationships']})})

# Independent mutation generation: frozen rawModelJson is deliberately unchanged.
member=next(r['id'] for r in M['relationships'] if r['source']=='C01' and r['type']=='MEMBER_OF_ZONE')
side=next(r['id'] for r in M['relationships'] if r['source']=='I01' and r['type']=='INTERFACE_OF' and r['properties']['role']=='side-b')
host=next(r['id'] for r in M['relationships'] if r['source']=='I02' and r['properties'].get('role')=='opening-host')
cases=[]
def edge_case(name,uid,field,value=None,delete=False,endpoint=False):
    cases.append(dict(name=name,kind='edge',id=uid,field=field,value=value,delete=delete,endpoint=endpoint))
def node_case(name,uid,field,value=None,delete=False):
    cases.append(dict(name=name,kind='node',id=uid,field=field,value=value,delete=delete,endpoint=False))
edge_case('C01_member_to_source_EV09',member,'target','EV09',endpoint=True)
edge_case('C01_member_to_wrong_building_B02',member,'target','B02',endpoint=True)
edge_case('I01_duplicate_side_a',side,'role','side-a')
edge_case('I01_nonspace_wall_side',side,'target','W01',endpoint=True)
edge_case('I01_nonspace_source_side',side,'target','EV09',endpoint=True)
edge_case('I02_nonwall_column_host',host,'target','C01',endpoint=True)
edge_case('I02_nonwall_space_host',host,'target','S02',endpoint=True)
edge_case('SRC_C01_empty_fields','SRC-C01','fields',[])
edge_case('SRC_C01_missing_fields','SRC-C01','fields',delete=True)
edge_case('SRC_C01_wrong_source_version','SRC-C01','sourceVersion','1.1')
edge_case('SRC_C01_wrong_source_uid','SRC-C01','sourceUid','V01:EV09')
edge_case('SRC_C01_wrong_locator','SRC-C01','locator','/nodes/0/properties')
edge_case('SRC_C01_wrong_locator_kind','SRC-C01','locatorKind','text')
edge_case('SRC_C01_missing_diameter_support','SRC-C01','fields',[x for x in rel(M,'SRC-C01')['properties']['fields'] if x!='diameterM'])
for uid in ['BOUND-S04-C01','R059']:
    for field,val in [('assertionSourceUid','V01:EV09'),('assertionSourceVersion','1.1'),('assertionLocator','/relationships/0'),('sourceUid','V01:EV09'),('sourceVersion','1.1'),('locator','/relationships/0')]:
        edge_case(uid+'_wrong_'+field,uid,field,val)
    for field in ['assertionSourceUid','assertionSourceVersion','assertionLocator','sourceUid','sourceVersion','locator']:
        edge_case(uid+'_missing_'+field,uid,field,delete=True)
node_case('EV01_wrong_source_version','EV01','sourceVersion','1.1')
node_case('C01_missing_diameter','C01','diameterM',delete=True)
node_case('S04_missing_boundaryBasis','S04','boundaryBasis',delete=True)
node_case('C01_missing_geometry','C01','geometryJson',delete=True)
edge_case('BOUND_S04_C01_changed_cache','BOUND-S04-C01','localNetLengthM',42.)

mutations=[]
for case in cases:
    for mode,source in [('canonical',M),('actualLPG',P)]:
        # GeometryJson and cache live only in LPG; do not misrepresent a canonical equivalent.
        if mode=='canonical' and case['field'] in ['geometryJson','localNetLengthM']:continue
        x=copy.deepcopy(source)
        q=rel(x,case['id']) if case['kind']=='edge' else node(x,case['id'])
        target=q if case['endpoint'] else q['properties']
        val=case['value']
        if case['endpoint'] and mode=='actualLPG':val='V01:'+val
        if case['delete']:target.pop(case['field'],None)
        else:target[case['field']]=copy.deepcopy(val)
        raw_unchanged=mode!='actualLPG' or node(x,'SOURCE')['properties']['rawModelJson']==node(P,'SOURCE')['properties']['rawModelJson']
        try:
            ret=validate_model(x) if mode=='canonical' else analyze(x)
            record={'name':case['name'],'mode':mode,'rejected':False,'rawModelUnchanged':raw_unchanged,'returned':'valid' if mode=='canonical' else 'full analysis with passed application labels'}
        except Exception as e:
            record={'name':case['name'],'mode':mode,'rejected':True,'rawModelUnchanged':raw_unchanged,'exceptionType':type(e).__name__,'message':str(e)}
        mutations.append(record)
save('mutation-probes.json',mutations)
checks['all_actual_mutations_keep_rawModel_unchanged']=all(x['rawModelUnchanged'] for x in mutations)
checks['required_named_F03_counterexamples_rejected']=all(x['rejected'] for x in mutations if x['name'] in [c['name'] for c in cases[:14]] or 'assertion' in x['name'])
checks['all_provenance_and_endpoint_counterexamples_rejected']=all(x['rejected'] for x in mutations)

# Independent analytic section clipping, no production interval/geometry helpers.
def union(xs):
    out=[]
    for a,b in sorted(xs):
        if b-a<1e-10:continue
        if out and a<=out[-1][1]+1e-9:out[-1][1]=max(out[-1][1],b)
        else:out.append([a,b])
    return out

def minus(xs,cuts):
    out=union(xs)
    for a,b in union(cuts):
        new=[]
        for c,d in out:
            if b<=c or a>=d:new.append([c,d]);continue
            if c<a:new.append([c,a])
            if b<d:new.append([b,d])
        out=new
    return out

def ring(g):
    x,y=g['min'][:2];X,Y=g['max'][:2]
    return {'N':[[x,Y],[X,Y]],'E':[[X,Y],[X,y]],'S':[[X,y],[x,y]],'W':[[x,y],[x,Y]]}

def section(uid,xy,z=1.):
    g=MN[uid]['geometry'];a,b=xy;L=math.dist(a,b);u=[(b[k]-a[k])/L for k in (0,1)]
    if g['kind']=='column':
        cx,cy,cz=g['center'];r=g['radius']
        if not cz<=z<cz+g['height']:return []
        along=(cx-a[0])*u[0]+(cy-a[1])*u[1];perp=abs((cx-a[0])*u[1]-(cy-a[1])*u[0])
        if perp>=r:return []
        d=math.sqrt(r*r-perp*perp);return union([[max(0,along-d),min(L,along+d)]])
    if g['kind']!='wall':return []
    h=g['height'] if g['heightMode']=='constant' else min(p[2] for p in g['topProfile'])
    if not 0<=z<h:return []
    lo=[min(g['a'][k],g['b'][k]) for k in (0,1)];hi=[max(g['a'][k],g['b'][k]) for k in (0,1)]
    normal=0 if g['a'][0]==g['b'][0] else 1
    lo[normal]=round(lo[normal]-g['thickness']/2,10);hi[normal]=round(hi[normal]+g['thickness']/2,10)
    def clip(low,high):
        c,d=0.,L
        for k in (0,1):
            if abs(u[k])<1e-12:
                if a[k]<low[k]-1e-10 or a[k]>high[k]+1e-10:return []
            else:
                p,q=sorted([(low[k]-a[k])/u[k],(high[k]-a[k])/u[k]])
                c=max(c,p);d=min(d,q)
        return union([[c,d]])
    solid=clip(lo,hi);cuts=[]
    for r in M['relationships']:
        if r['type']!='INTERFACE_OF' or r['target']!=uid or r['properties'].get('role')!='opening-host':continue
        op=MN[r['source']]['geometry']
        if not op['z'][0]<=z<op['z'][1]:continue
        low=[min(op['a'][k],op['b'][k]) for k in (0,1)];high=[max(op['a'][k],op['b'][k]) for k in (0,1)]
        low[normal]=lo[normal];high[normal]=hi[normal];cuts+=clip(low,high)
    return minus(solid,cuts)

def close(a,b):
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    return math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-8)
geom=[]
for row in A['basicRelations']['localizedBoundaries']:
    sid=row['spaceUid'].split(':')[1]
    for seg in row['segments']:
        xy=ring(MN[sid]['geometry'])[seg['id']];allxs=[]
        for p in seg['participants']:
            uid=p['uid'].split(':')[1]
            r=MR[p['relationshipUid'].split(':')[1]]
            xs=[] if r['properties']['participantRole']=='covered-open-transition' else section(uid,xy)
            geom.append({'space':sid,'segment':seg['id'],'participant':uid,'independent':xs,'reported':p['intervalsM'],'equal':close(xs,p['intervalsM'])})
            allxs+=xs
        geom.append({'space':sid,'segment':seg['id'],'independentUnion':union(allxs),'reported':seg['registeredSolidIntervalsM'],'equal':close(union(allxs),seg['registeredSolidIntervalsM'])})
checks['all_24_sides_and_local_participants_independent_geometry_match']=all(x['equal'] for x in geom)
# Explicit requested dimensions derived directly from original geometry.
length=lambda xs:sum(b-a for a,b in xs)
col_lengths=[length(section('C0'+str(i),ring(MN['S04']['geometry'])['S'])) for i in range(1,5)]
gate=section('W10',ring(MN['S06']['geometry'])['N'])
ig=MN['I04']['geometry'];xy=[ig['a'],ig['b']];gaps=minus([[0,math.dist(*xy)]],sum([section('C0'+str(i),xy) for i in range(1,5)],[]))
gaplengths=[b-a for a,b in gaps]
roof=MN['RF01']['geometry'];roofareas={}
for sid in semantics.SPACE_IDS:
    g=MN[sid]['geometry'];area=max(0,min(g['max'][0],roof['x'][1])-max(g['min'][0],roof['x'][0]))*max(0,min(g['max'][1],roof['y'][1])-max(g['min'][1],roof['y'][0]));roofareas[sid]=area
    report=next(x for x in A['basicRelations']['roofCoverage'] if x['spaceUid']=='V01:'+sid)
    checks['independent_roof_area_'+sid]=close(area,report['coveredAreaM2'])
s=MN['S06']['geometry'];st=MN['ST01']['geometry'];xx=st['surfaceXY'][::2];yy=st['surfaceXY'][1::2]
streetarea=max(0,min(s['max'][0],max(xx))-max(s['min'][0],min(xx)))*max(0,min(s['max'][1],max(yy))-max(s['min'][1],min(yy)))
checks['requested_numeric_values']=close(col_lengths,[.14,.28,.28,.14]) and close(length(gate),.4) and len(gate)==2 and close(roofareas['S05'],5.616) and close(gaplengths,[2.92,2.92,2.92]) and close(streetarea,2.76)
checks['I04_independent_gaps_equal_report']=close(gaps,A['basicRelations']['interfaceOccupation']['planOpenIntervalsM'])
checks['street_independent_equals_report']=close(streetarea,A['basicRelations']['streetReference']['intersectionAreaM2'])
save('geometry-recomputation.json',{'comparisons':geom,'columnLengths':col_lengths,'gateIntervals':gate,'gateNet':length(gate),'roofAreas':roofareas,'I04GapIntervals':gaps,'I04GapLengths':gaplengths,'streetArea':streetarea})

# Preserve the positive exceptions without asking for nonexistent exterior spaces.
exceptions={}
for uid in ['I01','I04','I08','I09','I10']:
    rs=[r for r in M['relationships'] if r['source']==uid and r['type']=='INTERFACE_OF']
    exceptions[uid]=[{'role':r['properties']['role'],'target':r['target']} for r in rs]
checks['I01_I04_no_hosts']=all(not any(x['role']=='opening-host' for x in exceptions[uid]) for uid in ['I01','I04'])
checks['I08_to_I10_single_known_side']=all([x['role'] for x in exceptions[uid] if x['role'] in ['side-a','side-b']]==['side-a'] for uid in ['I08','I09','I10'])
checks['56_object_acceptance_not_completeness']=len(A['basicRelations']['objectCoverage'])==56 and all(r['acceptance'] in ['declared-application-obligations-passed-not-completeness-proof','snapshot-metadata-not-building-object'] for r in A['basicRelations']['objectCoverage']) and A['basicRelations']['semanticCompleteness']=='not-proved'
rev=copy.deepcopy(P);rev['nodes'].reverse();rev['relationships'].reverse()
checks['full_analysis_order_independent']=analyze(rev)==A
save('positive-exceptions.json',exceptions)
# Static only: parse strings/AST, never execute/import run_graph or build_review.
text=(FIX/'tools/run_graph.py').read_text();tree=ast.parse(text)
replace_expr=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='REPLACE' for t in n.targets))
while isinstance(replace_expr,ast.Call) and isinstance(replace_expr.func,ast.Attribute):
    replace_expr=replace_expr.func.value
replace=ast.literal_eval(replace_expr)
import re
static={
    'no_delete_merge_drop_or_ddl_in_write_cypher':not re.search(r'\b(DELETE|DETACH|MERGE|DROP|CONSTRAINT|INDEX|REMOVE)\b',replace,re.I),
    'only_one_create_fixed_boundary_type':len(re.findall(r'\bCREATE\b',replace))==1 and 'CREATE (a)-[r:BOUNDARY_PARTICIPANT]->(b)' in replace,
    'only_existing_nodes_matched_for_update':'MATCH (n:KGItem {uid:row.properties.uid}) SET n=row.properties' in replace,
    'old_endpoints_types_required':'r.source=o.source AND r.target=o.target AND r.type=o.type' in replace,
    'exactly_five_additions':'WHERE size(additions)=5' in replace and all("['V01:"+a+"','V01:"+b+"']" in replace for a,b in semantics.REQUIRED_NEW),
    'frozen_payload_and_native_types':'ns=$frozenNodes AND rs=$frozenRelationships' in replace and 'valueType(n.properties[t.key])=t.type' in replace and 'valueType(r.properties[t.key])=t.type' in replace,
    'old_graph_properties_labels_types':'properties(n)=o.properties' in replace and 'size(labels(n))=size(o.labels)' in replace and 'properties(e.r)=o.properties' in replace and 'valueType(e.r[t.key])=t.type' in replace,
    'source_sha_bound':"sourceModelSha256=$sourceModelSha256" in replace and 'model_sha==args.model_sha' in text,
    'authorization_preflight_and_no_retry':all(s in text for s in ['user-authorized-V01-basic-relations-update','Source/code/database changed since preflight','write-started-no-retry','Stage exists; read back instead of resending']),
    'unrelated_graph_schema_exact_readback':all(s in text for s in ['remaining==untouched','==oldschema','verify_exact(active,p)','analysis==analyze(p)']),
    'source_recompiled_immediately_before_commit':"require(compile_model(model_path)[1]==p,'Source changed before commit')" in text,
    'no_21_replay_command':not re.search(r'\b(subprocess|os\.system|exec|eval)\s*\(',text),
}
checks['static_run_graph_protection_predicates']=all(static.values())
save('static-checks.json',{'checks':static,'writeCypherLiteral':replace,'scope':'AST/text only; no Neo4j compilation, invocation, or live guard tests'})
checks['no_prohibited_module_imported']=not any(k in sys.modules for k in ['run_graph','mcp_client','build_review'])
save('verification.json',{'checks':checks,'failedChecks':[k for k,v in checks.items() if not v],'mutations':{'count':len(mutations),'rejected':sum(x['rejected'] for x in mutations),'accepted':[{'name':x['name'],'mode':x['mode']} for x in mutations if not x['rejected']]},'provided_tests_executed':False})
print(json.dumps({'checks':checks,'acceptedMutations':[x for x in mutations if not x['rejected']]},ensure_ascii=False,indent=2))
