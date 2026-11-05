"""Run the same published modules against preserved baseline and integration tests."""
from pathlib import Path
import importlib.util,json,os,subprocess,sys,unittest
W=Path(__file__).parent;sys.path.insert(0,str(W/'tools'));(W/'tests').mkdir(exist_ok=True)
summary=[]
for name,path in [('D04',W/'workers/d04/test_d04.py'),('D05',W/'workers/d05/test_d05.py'),('unified',W/'test_unified.py'),('extensions',W/'test_extensions.py'),('review-fixes',W/'test_review_fixes.py'),('basic-relations',W/'test_semantics.py')]:
 spec=importlib.util.spec_from_file_location('suite_'+name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 suite=unittest.defaultTestLoader.loadTestsFromModule(mod)
 with (W/'tests'/(name+'.log')).open('w') as stream:r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 row={'suite':name,'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'success':r.wasSuccessful()};summary.append(row);print(row,flush=True)
 (W/'tests/all-tests.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
 assert r.wasSuccessful(),str(W/'tests'/(name+'.log'))
r=subprocess.run([sys.executable,'-B',str(W/'test_legacy.py')],capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'));(W/'tests/legacy.log').write_text(r.stdout+r.stderr);assert r.returncode==0,str(W/'tests/legacy.log')
legacy=json.loads((W/'tests/legacy-regression-final.json').read_text());summary.append({'suite':'legacy','tests':len(legacy['checks']),'failures':0,'errors':0,'skipped':0,'success':True})
(W/'tests/all-tests.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps({'total':sum(x['tests'] for x in summary),'skipped':sum(x['skipped'] for x in summary),'failed':sum(x['failures']+x['errors'] for x in summary)},ensure_ascii=False))
