"""Build the offline review solely from verified database readback."""
import argparse,hashlib,json,re
from pathlib import Path
from markdown_it import MarkdownIt
from compile_model import MODEL,compile_model
from run_graph import verify_exact
from analyze import analyze
MD=MarkdownIt('commonmark',{'html':True}).enable('table')
def build(w,template=None):
    pkg=Path(MODEL).parent;v=json.loads((w/'db/verification.json').read_text());g=json.loads((w/'db/D03-readback.json').read_text())
    p=w/'candidates'/MODEL;m,payload,_=compile_model(p);assert hashlib.sha256(p.read_bytes()).hexdigest()==v['modelSHA256']
    assert v['status']=='verified-external-synthetic-six-items-new-details-awaiting-review';verify_exact(g,payload)
    a=analyze(g,m['externalExtension']['pathRequests'],m['externalExtension']['rules']);assert a==json.loads((w/'db/analysis-results.json').read_text())
    table=w/'candidates/研究成果/〔分析框架〕风貌分析拆解/D03院落与空间组织拆解表.md';s=table.read_text();docs={}
    for i in range(1,7):
        key=f'T{i:02}';match=re.search(r'^## D03-'+key+r' .*?(?=^## |\Z)',s,re.M|re.S);assert match;docs[key]=MD.render(match.group())
    sources=MD.render(s[s.index('## 来源、阅读履历与查证任务'):])
    d={'graph':g,'analysis':a,'verification':v,'documents':docs,'sourcesHTML':sources,'queries':json.loads((w/'generated/queries.json').read_text()),'results':json.loads((w/'db/query-results.json').read_text()),'tests':json.loads((w/'tests/results.json').read_text()),'preflight':json.loads((w/'db/preflight.json').read_text())}
    source=Path(template) if template else Path(__file__).with_name('viewer.template.html');out=w/'candidates'/pkg/'审核视图.html';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(source.read_text().replace('__SNAPSHOT__',json.dumps(d,ensure_ascii=False).replace('</','<\\/')))
    report={'path':str(out),'modelSHA256':v['modelSHA256'],'tableSHA256':hashlib.sha256(table.read_bytes()).hexdigest(),'snapshotSHA256':hashlib.sha256((w/'db/D03-readback.json').read_bytes()).hexdigest(),'templateSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'htmlSHA256':hashlib.sha256(out.read_bytes()).hexdigest(),'tasks':list(docs),'source':'genuine verified Neo4j readback'}
    (w/'viewer-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);a=p.parse_args();build(Path(a.workspace))
