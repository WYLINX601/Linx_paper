"""Run the preserved D03 algorithms locally. Never connect to Neo4j."""
import hashlib,json,math,sys
from pathlib import Path
W=Path(__file__).resolve().parent
sys.path.insert(0,str(W/'d03-tools'))
sys.path.append(str(W/'tools'))  # legacy compiler imports only the shared save helper
from compile_model import compile_model
from analyze import analyze
m,p,c=compile_model(W/'originals/d03.json')
g={k:[dict(r,key=r['properties']['uid']) for r in p[k]] for k in ['nodes','relationships']}
a=analyze(g,m['externalExtension']['pathRequests'],m['externalExtension']['rules'])
old=json.loads((W/'tests/legacy-fixtures.json').read_text())
checks=[]
def check(name,condition):
 assert condition,name;checks.append(name)
check('classification-exact',c==old['classificationAssignments'])
check('analysis-exact-six-items',a==old['analysis'])
check('A-B-same-type',c[0]['candidateType']==c[1]['candidateType']=='ENC-3B-1W')
check('C-explicit-open',c[2]['candidateType']=='ENC-2B-1W-1O')
check('D-unknown-not-open',c[3]['status']=='unknown' and c[3]['candidateType']=='')
check('six-items',set(a['items'])=={'T01','T02','T03','T04','T05','T06'})
check('both-courtyards',{'D03V01:E-C01','D03V01:E-C02'}<=set(x['uid'] for x in a['items']['T01']))
check('forward-three-reverse-unconfirmed',[x['crossings'] for x in a['items']['T04'] if 'from' in x]==[3,None])
check('courtyard-ratio',math.isclose(next(x for x in a['items']['T05'] if x['kind']=='area-configuration')['courtyardRatio'],.3125))
check('multi-use-deduplicated',a['useSummary']['knownSpaces']==2 and a['useSummary']['useAssignments']==4)
r={'status':'passed-local-regression-not-active-db','checks':checks,'hashes':{str(f.relative_to(W)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [W/'originals/d03.json',W/'d03-tools/compile_model.py',W/'d03-tools/legacy_compile.py',W/'d03-tools/analyze.py']},'classificationAssignments':c,'analysis':a}
(W/'tests/legacy-regression-final.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'legacyRegression':'passed','checks':checks},ensure_ascii=False))
