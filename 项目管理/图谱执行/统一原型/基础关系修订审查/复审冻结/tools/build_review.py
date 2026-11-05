"""Build an offline review from exact verified readback, or labelled local preview."""
import argparse,hashlib,json,re
from pathlib import Path
from markdown_it import MarkdownIt
from compile_model import compile_model,MODEL_PATH
from run_graph import verify_exact,code_hash
from analyze import analyze
from queries import queries
MD=MarkdownIt('commonmark',{'html':True}).enable('table')
def build(w,preview=False):
 model=w/'candidate/model.json';m,p=compile_model(model);sha=hashlib.sha256(model.read_bytes()).hexdigest()
 if preview:
  g={k:[{**r,'key':r['properties']['uid']} for r in p[k]] for k in ['nodes','relationships']};v={'status':'candidate-local-preview-not-database-readback','modelSHA256':sha};answers={}
 else:
  v=json.loads((w/'db/verification.json').read_text());g=json.loads((w/'db/V01-readback.json').read_text())
  assert v['status']=='verified-unified-synthetic-prototype-new-details-await-user-review' and v['modelSHA256']==sha and v['compilerSHA256']==code_hash()
  verify_exact(g,p);answers=json.loads((w/'db/query-results.json').read_text())
 a=analyze(g)
 if not preview:assert a==json.loads((w/'db/analysis-results.json').read_text())
 base=w/'candidates/研究成果/〔分析框架〕风貌分析拆解';tables={}
 for key,filename,alias in [('D01','风貌分析拆解类型表.md','d01-table.md'),('D03','D03院落与空间组织拆解表.md','d03-table.md'),('D04','D04立面材料与装饰拆解表.md','d04.md'),('D05','D05民居组合街巷与地形拆解表.md','d05.md'),('D06','D06类型比较与关联解释拆解表.md','d06.md')]:
  path=base/filename
  if preview and not path.exists():path=w/'originals'/alias
  tables[key]=path.read_text()
 docs={'D01':MD.render(re.sub(r'^---\n.*?\n---\n','',tables['D01'],count=1,flags=re.S))}
 for i in range(1,7):
  k=f'T{i:02}';match=re.search(r'^## D03-'+k+r' .*?(?=^## |\Z)',tables['D03'],re.M|re.S);assert match;docs[k]=MD.render(match.group())
 docs['来源与阅读履历']=MD.render(tables['D03'][tables['D03'].index('## 来源、阅读履历与查证任务'):])
 for module in ['D04','D05','D06']:docs[module]=MD.render(re.sub(r'^---\n.*?\n---\n','',tables[module],count=1,flags=re.S))
 d={'graph':g,'analysis':a,'verification':v,'documents':docs,'queries':queries(),'results':answers,'tests':json.loads((w/'tests/results.json').read_text()),'preflight':json.loads((w/'db/preflight.json').read_text())}
 template=Path(__file__).with_name('viewer.template.html');out=w/'candidates'/Path(MODEL_PATH).parent/'审核视图.html';out.parent.mkdir(parents=True,exist_ok=True)
 text=template.read_text();assert text.count('__SNAPSHOT__')==1 and '__ROUTING__' not in text
 text=text.replace('__EXTENSION_UI__',Path(__file__).with_name('extension-ui.js').read_text())
 text=text.replace('__BASIC_UI__',Path(__file__).with_name('basic-ui.js').read_text())
 out.write_text(text.replace('__SNAPSHOT__',json.dumps(d,ensure_ascii=False).replace('</','<\\/')))
 report={'source':'candidate-local-preview' if preview else 'genuine-verified-Neo4j-readback','modelSHA256':sha,'htmlSHA256':hashlib.sha256(out.read_bytes()).hexdigest(),'templateSHA256':hashlib.sha256(template.read_bytes()).hexdigest(),'documentsSHA256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in tables.items()},'tasks':list(docs),'output':str(out)}
 (w/('viewer-preview.json' if preview else 'viewer-build.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);p.add_argument('--preview',action='store_true');args=p.parse_args();build(Path(args.workspace),args.preview)
