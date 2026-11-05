from pathlib import Path
import hashlib, json, subprocess
W=Path(__file__).resolve().parent
ROOT=Path('/Users/wangyuelin/Desktop/Obsidian/Paper')
PROFILE=Path('/Users/wangyuelin/.hermes/profiles/academic')
BRIDGE=PROFILE/'bin/mac-paper'
CASE='研究成果/〔合成试例〕D03院落围合图谱试例'
TOOLS='项目管理/图谱执行/D03院落围合'
TABLE='研究成果/〔分析框架〕风貌分析拆解/D03院落与空间组织拆解表.md'
MAP=TABLE.replace('拆解表.md','拆解图.smm.md')
def digest(data): return hashlib.sha256(data).hexdigest()
def get(rel):
    d=json.loads(subprocess.check_output([str(BRIDGE),'read',rel]))
    if not d.get('ok'): raise RuntimeError(d)
    return d['result']
def pull(rel):
    r=get(rel); p=W/'originals'/rel; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(r['text']); assert digest(p.read_bytes())==r['sha256']
    mpath=W/'sources.json'; m=json.loads(mpath.read_text()) if mpath.exists() else {}
    m[rel]={'sha256':r['sha256'],'path':str(p)}
    mpath.write_text(json.dumps(m,ensure_ascii=False,indent=2))
    return p
def candidate(rel,text):
    p=W/'candidates'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
if __name__=='__main__':
    paths=['AGENTS.md','README.md','context/PROJECT_CONTEXT.md','研究成果/〔建模依据〕知识图谱建模基准/BOT基准.md','研究成果/〔建模依据〕知识图谱建模基准/本研究优化基准.md',TABLE,MAP,CASE+'/README.md',CASE+'/案例模型.json',CASE+'/审核视图.html',TOOLS+'/README.md',TOOLS+'/compile_model.py',TOOLS+'/mcp_client.py',TOOLS+'/run_graph.py',TOOLS+'/verify_current.py',TOOLS+'/preflight.py','研究成果/〔分析框架〕风貌分析拆解/README.md','研究成果/〔分析框架〕风貌分析拆解/D06类型比较与关联解释拆解表.md']
    for rel in paths:
        p=pull(rel);print(rel,digest(p.read_bytes()))
