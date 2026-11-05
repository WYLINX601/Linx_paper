"""Focused remaining F03 gap; all mutations confined to memory/output."""
import copy,json,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
FIX=OUT.parent/'review2-fixed'
sys.dont_write_bytecode=True
sys.path.insert(0,str(FIX/'tools'))
from compile_model import compile_model,validate_model
from analyze import analyze
import semantics
m,p=compile_model(FIX/'candidate/model.json')
a=analyze(p)
def r(x):return next(t for t in x['relationships'] if t['id']=='BOUND-S04-C01')
def src(x):return next(t for t in x['nodes'] if t['id']=='SOURCE')['properties']['rawModelJson']
results=[]
original_validate=semantics.validate
for field,bad in [('sourceUid','V01:EV09'),('sourceVersion','1.1'),('locator','/relationships/0')]:
    q=copy.deepcopy(p);r(q)['properties'][field]=bad
    seen=[]
    def recording_validate(model):
        seen.append(copy.deepcopy(r(model)['properties']))
        return original_validate(model)
    semantics.validate=recording_validate
    try:out=analyze(q)
    finally:semantics.validate=original_validate
    assert len(seen)==1 and seen[0][field]==bad
    assert src(q)==src(p)
    results.append({'mode':'actualLPG','relation':'BOUND-S04-C01','field':field,'badValue':bad,'analyzeAccepted':True,'fullAnalysisUnchanged':out==a,'rawModelJsonUnchanged':src(q)==src(p),'actualRehydratedValueSeenByValidator':seen[0][field],'assertionFieldsStillCorrect':{k:seen[0][k] for k in ['assertionSourceUid','assertionSourceVersion','assertionLocator']}})
# Demonstrate that a freshly compiled canonical locator conflict also survives.
bad=copy.deepcopy(m);r(bad)['properties']['locator']='/relationships/0'
assert validate_model(bad)
path=OUT/'counterexample-wrong-boundary-locator.json'
path.write_text(json.dumps(bad,ensure_ascii=False,indent=2)+'\n')
mm,pp=compile_model(path)
aa=analyze(pp)
results.append({'mode':'canonical-new-compile','field':'locator','value':r(mm)['properties']['locator'],'assertionLocator':r(mm)['properties']['assertionLocator'],'validateAccepted':True,'compileAccepted':True,'analyzeAccepted':True,'basicRelationsUnchanged':aa['basicRelations']==a['basicRelations'],'sourceModelSha256':pp['sourceModelSha256']})
(OUT/'focused-provenance-repro.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
assert not any(k in sys.modules for k in ['run_graph','mcp_client','build_review'])
print(json.dumps(results,ensure_ascii=False,indent=2))
