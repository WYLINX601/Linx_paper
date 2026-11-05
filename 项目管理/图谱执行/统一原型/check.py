"""Clean-workspace maintenance entry; never writes Paper or imports graph data."""
import argparse,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path('/Users/wangyuelin/Desktop/Obsidian/Paper');PROFILE=Path('/Users/wangyuelin/.hermes/profiles/academic');P='研究成果/〔合成试例〕虚拟民居单体试验V01';T='项目管理/图谱执行/统一原型';OLD='archive/2026-10-30-统一原型合并前';BASE='archive/2026-10-31-统一原型D04-D06扩展前';F='研究成果/〔分析框架〕风貌分析拆解';BRIDGE=PROFILE/'bin/mac-paper'
FIXBASE='archive/2026-11-02-基础关系修订前';RECEIPTS=P+'/Neo4j/基础关系修订回执'
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--database',action='store_true');ap.add_argument('--candidate-root',type=Path);args=ap.parse_args()
 if args.candidate_root:assert not args.candidate_root.resolve().is_relative_to(ROOT.resolve())
 w=Path(tempfile.mkdtemp(prefix='unified-next-check-',dir=PROFILE/'cache/scratch'));transfers=[]
 def get(rel,dest):
  out=w/dest;out.parent.mkdir(parents=True,exist_ok=True)
  if args.candidate_root and (args.candidate_root/rel).is_file():out.write_bytes((args.candidate_root/rel).read_bytes());return
  p=subprocess.run([str(BRIDGE),'download',rel,str(out)],check=True,capture_output=True,text=True);j=json.loads(p.stdout);assert j['ok'];transfers.append(j['result'])
 for f in ['compile_model.py','analyze.py','queries.py','run_graph.py','mcp_client.py','build_review.py','viewer.template.html','extension-ui.js','basic-ui.js','d04.py','d05.py','d06.py','projection.py','semantics.py']:get(T+'/tools/'+f,'tools/'+f)
 for f in ['test_unified.py','test_legacy.py','test_extensions.py','test_review_fixes.py','test_semantics.py','run_tests.py']:get(T+'/'+f,f)
 for mod in ['d04','d05']:get(T+'/workers/'+mod+'/test_'+mod+'.py','workers/'+mod+'/test_'+mod+'.py')
 get(P+'/案例模型.json','candidate/model.json');get(P+'/Neo4j/后续扩展映射.json','candidate/extension-map.json')
 get(P+'/Neo4j/基础关系修订回执/analysis-results.json','candidate/analysis.json')
 get(P+'/Neo4j/基础关系修订映射.json','candidate/fix-map.json');get(FIXBASE+'/model-2.1.json','baseline/model-2.1.json')
 get(BASE+'/originals/model.json','originals/model.json');get(BASE+'/tests/baseline-analysis.json','tests/baseline-analysis.json')
 for f in ['v01.json','d03.json']:get(OLD+'/原件/'+f,'originals/'+f)
 for f in ['compile_model.py','legacy_compile.py','analyze.py']:get(OLD+'/d03-tools/'+f,'d03-tools/'+f)
 for f in ['graph.json','schema.json']:get(FIXBASE+'/database/'+f,'db/before/'+f)
 get(P+'/Neo4j/回归夹具.json','tests/legacy-fixtures.json')
 if args.candidate_root and not (args.candidate_root/(RECEIPTS+'/V01-readback.json')).exists():pass
 else:get(RECEIPTS+'/V01-readback.json','db/V01-readback.json')
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');r=subprocess.run([sys.executable,'-B',str(w/'run_tests.py')],env=env,capture_output=True,text=True);(w/'run_tests.log').write_text(r.stdout+r.stderr);assert r.returncode==0,str(w/'run_tests.log')
 if args.database:
  for f in ['preflight.json','execution-stage.json']:get(RECEIPTS+'/'+f,'db/'+f)
  for f in ['风貌分析拆解类型表.md','D03院落与空间组织拆解表.md','D04立面材料与装饰拆解表.md','D05民居组合街巷与地形拆解表.md','D06类型比较与关联解释拆解表.md']:get(F+'/'+f,'candidates/'+F+'/'+f)
  cmd=[sys.executable,'-B',str(w/'tools/run_graph.py'),'--workspace',str(w),'--model',str(w/'candidate/model.json'),'--model-sha',hashlib.sha256((w/'candidate/model.json').read_bytes()).hexdigest(),'--mode','verify']
  r=subprocess.run(cmd,env=env,capture_output=True,text=True);(w/'verify.log').write_text(r.stdout+r.stderr);assert r.returncode==0,str(w/'verify.log')
  # Build-review consumes the unified-suite receipt, not a fabricated summary.
  r=subprocess.run([sys.executable,'-B',str(w/'test_unified.py')],env=env,capture_output=True,text=True);assert r.returncode==0;r=subprocess.run([sys.executable,'-B',str(w/'tools/build_review.py'),'--workspace',str(w)],env=env,capture_output=True,text=True);(w/'viewer.log').write_text(r.stdout+r.stderr);assert r.returncode==0,str(w/'viewer.log')
 (w/'transfer-receipts.json').write_text(json.dumps(transfers,ensure_ascii=False,indent=2))
 print(json.dumps({'status':'passed','tests':json.loads((w/'tests/all-tests.json').read_text()),'database':'read-only-exact-verification' if args.database else 'not-contacted','workspace':str(w),'publication':'none'},ensure_ascii=False))
if __name__=='__main__':main()
