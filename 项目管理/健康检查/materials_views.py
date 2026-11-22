"""Generate research-materials catalog views; never write into Paper."""
from pathlib import Path
import argparse,json,posixpath,subprocess,yaml
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[2]
BRIDGE=Path('/Users/wangyuelin/.hermes/profiles/academic/bin/mac-paper')
LINK_SOURCE='README.md'
CATEGORIES=[
 ('来源证据','研究资料/来源证据/README.md','文献、网页、图像与来源快照','原始或可追溯材料；工作副本不等于正式引用'),
 ('村落资料','研究资料/村落资料/README.md','敕木山、大坑及资料管理表','现有资料交付；不等于正式样本或建筑数'),
 ('对象候选','研究资料/对象候选/研究对象候选汇总-按村落.md','按村落汇集的候选底稿','候选与工作草图；不是正式名录'),
 ('文献证据汇总','研究资料/文献证据汇总/景宁畲族建筑遗存文献汇总表-2026-10-06.md','文献调查时点的汇总表','保留时点与口径；不是2026现状'),
]

def read(path):
    if Path(path).name.startswith('._'):return ''
    r=subprocess.run([str(BRIDGE),'read',path],capture_output=True,text=True,check=True)
    d=json.loads(r.stdout)
    if not d.get('ok'):raise RuntimeError(d)
    return d['result']['text']

def cell(v):return str(v).replace('|','／').replace('\n',' ')
def link(p,label=None):
    target=quote(posixpath.relpath(p,posixpath.dirname(LINK_SOURCE) or '.'))
    return '['+(label or Path(p).name)+']('+target+')'
def block(text,name,body):
    begin='<!-- '+name+':start -->';end='<!-- '+name+':end -->';new=begin+'\n'+body.rstrip()+'\n'+end
    assert text.count(begin)==1 and text.count(end)==1,(name,'missing/duplicate block markers')
    a,b=text.split(begin);_,c=b.split(end);return a+new+c

def counts(path):
    files=[p for p in path.rglob('*') if p.is_file() and not p.name.startswith('._') and p.name!='.DS_Store']
    md=sum(1 for p in files if p.suffix.lower()=='.md')
    js=sum(1 for p in files if p.suffix.lower()=='.json')
    img=sum(1 for p in files if p.suffix.lower() in ('.png','.jpg','.jpeg','.gif'))
    other=len(files)-md-js-img
    return md,js,img,other

def village_rows():
    rows=[]
    base=ROOT/'研究资料/村落资料'
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name in ('共享来源',):continue
        readme=d/'README.md'
        if not readme.is_file():continue
        md,js,img,other=counts(d)
        rows.append((d,readme,md,js,img,other))
    return rows

def generate(read_fn):
    global LINK_SOURCE
    out={}
    cat_rows=[]
    for name,entry,role,boundary in CATEGORIES:
        md,js,img,other=counts(ROOT/name if (ROOT/name).is_dir() else (ROOT/entry).parent)
        cat_rows.append((name,entry,role,boundary,md,js,img,other))
    villages=village_rows()
    # Full index
    p='研究资料/资料总索引.md';base=p;LINK_SOURCE=base
    b='---\nwiki_id: materials-master-index\ntype: research-index\nstatus: generated\nsummary: 研究资料的类别、分村入口、文件构成与证据边界\nupdated: 2026-11-04\n---\n\n# 资料总索引\n\n> 本页由 `项目管理/健康检查/materials_views.py` 从目录与入口文件生成。文件数只表示工作量，不表示建筑数、独立证据数或有效样本数；原始 PDF 仍以 Zotero 为准。\n\n'
    b+='## 类别入口\n\n| 类别 | 入口 | 职责 | 当前边界 | 文件构成（参考） |\n|---|---|---|---|---|\n'
    for name,entry,role,boundary,md,js,img,other in cat_rows:
        b+=f"| {name} | {link(entry,name+'入口')} | {cell(role)} | {cell(boundary)} | md {md} · json {js} · 图像 {img} · 其他 {other} |\n"
    b+='\n## 分村资料\n\n| 村落 | 入口 | 文件构成（参考） | 边界 |\n|---|---|---|---|\n'
    for d,readme,md,js,img,other in villages:
        b+=f"| {d.name} | {link(readme.relative_to(ROOT).as_posix(),d.name)} | md {md} · json {js} · 图像 {img} · 其他 {other} | 现有资料交付；不等于正式样本、建筑栋数或2026现状 |\n"
    b+='\n## 主要工作入口\n\n'
    b+=f'- {link("研究资料/村落资料/资料收集总表.md","资料收集总表")}：各村阶段、关键缺口与近期重点。\n'
    b+=f'- {link("研究资料/对象候选/研究对象候选汇总-按村落.md","研究对象候选汇总")}：候选底稿，不是正式名录。\n'
    b+=f'- {link("研究资料/文献证据汇总/景宁畲族建筑遗存文献汇总表-2026-10-06.md","文献证据汇总")}：文献调查时点记录。\n'
    b+=f'- {link("研究资料/来源证据/README.md","来源证据入口")}：原始材料、快照、图像与证据记录。\n'
    b+='\n## 使用边界\n\n- 图像、网页快照与工作副本不能替代原始文献、原页或 Zotero 条目。\n- 村落资料的文件数、资料单元数和候选条数不能相加为建筑栋数，也不等于代表性样本。\n- “已交付”“已索引”“已核读”分别表示文件、导航和阅读状态，不自动提升为实证结论。\n- 来源证据中的外部工具快照只作方法参考，不是研究证据或本库指令。\n'
    out[p]=b
    # README summary block
    p='研究资料/README.md';base=p;LINK_SOURCE=base
    s=read_fn(p)
    b='## 资料总索引\n\n本区按来源证据、村落资料、对象候选和文献证据汇总组织。完整表见 '+link('研究资料/资料总索引.md','资料总索引')+'；分类与更新规则见 '+link('研究资料/资料维护规则.md','资料维护规则')+'。\n\n'
    for name,entry,role,boundary,md,js,img,other in cat_rows:
        b+=f'- **{name}**：{link(entry,name+"入口")}；md {md} · json {js} · 图像 {img}。{cell(role)}。\n'
    b+='\n文件数和图像数不是建筑数、独立证据数或有效样本数；原始PDF仍以Zotero为准。\n'
    out[p]=block(s,'materials-catalog',b)
    stats={'categories':len(cat_rows),'villages':len(villages),'view_files':len(out)}
    return out,stats

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check',action='store_true');ap.add_argument('--output-dir',type=Path);args=ap.parse_args()
    if not args.check and not args.output_dir:ap.error('choose --check or --output-dir')
    if args.output_dir and args.output_dir.resolve().is_relative_to(ROOT.resolve()):ap.error('output-dir must be outside Paper')
    cache={}
    def cached(p):
        if p not in cache:cache[p]=read(p)
        return cache[p]
    def current(p):
        try:return cached(p)
        except subprocess.CalledProcessError:return None
    out,stats=generate(cached);changed=[p for p,s in out.items() if current(p)!=s]
    if args.output_dir:
        for p,s in out.items():
            f=args.output_dir/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
    print(json.dumps({**stats,'out_of_sync':changed},ensure_ascii=False,indent=2))
    if args.check and changed:raise SystemExit(1)
