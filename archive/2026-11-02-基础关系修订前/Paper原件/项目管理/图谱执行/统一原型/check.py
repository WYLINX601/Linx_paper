"""Reconstruct a scratch run from Paper; local checks by default, DB reads only on request."""
import argparse,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path('/Users/wangyuelin/Desktop/Obsidian/Paper');PROFILE=Path('/Users/wangyuelin/.hermes/profiles/academic');P='研究成果/〔合成试例〕虚拟民居单体试验V01';T='项目管理/图谱执行/统一原型';A='archive/2026-10-30-统一原型合并前';F='研究成果/〔分析框架〕风貌分析拆解';BRIDGE=PROFILE/'bin/mac-paper'
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--database',action='store_true',help='Run read-only exact DB verification and build a review in scratch. Never import.');ap.add_argument('--candidate-root',type=Path,help='Optional unpublished overlay outside Paper for testing this tool.');args=ap.parse_args()
 if args.candidate_root:assert not args.candidate_root.resolve().is_relative_to(ROOT.resolve())
 w=Path(tempfile.mkdtemp(prefix='unified-check-',dir=PROFILE/'cache/scratch'));transfers=[]
 def get(rel,dest):
  out=w/dest;out.parent.mkdir(parents=True,exist_ok=True)
  if args.candidate_root and (args.candidate_root/rel).is_file():out.write_bytes((args.candidate_root/rel).read_bytes());return
  r=subprocess.run([str(BRIDGE),'download',rel,str(out)],check=True,capture_output=True,text=True);j=json.loads(r.stdout);assert j['ok'];transfers.append(j['result'])
 for f in ['compile_model.py','analyze.py','queries.py','run_graph.py','mcp_client.py','build_review.py','viewer.template.html']:get(T+'/tools/'+f,'tools/'+f)
 for f in ['test_unified.py','test_legacy.py']:get(T+'/'+f,f)
 get(P+'/案例模型.json','candidate/model.json');get(P+'/Neo4j/统一迁移映射.json','candidate/migration.json')
 for f in ['v01.json','d03.json']:get(A+'/原件/'+f,'originals/'+f)
 for f in ['compile_model.py','legacy_compile.py','analyze.py']:get(A+'/d03-tools/'+f,'d03-tools/'+f)
 for f in ['graph.json','schema.json']:get(A+'/db/before/'+f,'db/before/'+f)
 get(P+'/Neo4j/回归夹具.json','tests/legacy-fixtures.json');get(P+'/Neo4j/执行回执/V01-readback.json','db/V01-readback.json')
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');results=[]
 for f in ['test_unified.py','test_legacy.py']:
  r=subprocess.run([sys.executable,str(w/f)],env=env,capture_output=True,text=True);(w/(f+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,f+' failed: '+str(w/(f+'.log'));results.append(f)
 if args.database:
  import hashlib
  for f in ['preflight.json','execution-stage.json','verification-upgrade.json']:get(P+'/Neo4j/执行回执/'+f,'db/'+f)
  for f in ['风貌分析拆解类型表.md','D03院落与空间组织拆解表.md']:get(F+'/'+f,'candidates/'+F+'/'+f)
  cmd=[sys.executable,str(w/'tools/run_graph.py'),'--workspace',str(w),'--model',str(w/'candidate/model.json'),'--model-sha',hashlib.sha256((w/'candidate/model.json').read_bytes()).hexdigest(),'--mode','verify','--verification-upgrade',str(w/'db/verification-upgrade.json')]
  r=subprocess.run(cmd,env=env,capture_output=True,text=True);(w/'verify.log').write_text(r.stdout+r.stderr);assert r.returncode==0,'Read-only verify failed: '+str(w/'verify.log')
  subprocess.run([sys.executable,str(w/'tools/build_review.py'),'--workspace',str(w)],check=True,env=env)
 (w/'transfer-receipts.json').write_text(json.dumps(transfers,ensure_ascii=False,indent=2))
 print(json.dumps({'status':'passed','localSuites':results,'database':'read-only-exact-verification' if args.database else 'not-contacted','workspace':str(w),'publication':'none; review and guarded publication required'},ensure_ascii=False))
if __name__=='__main__':main()
