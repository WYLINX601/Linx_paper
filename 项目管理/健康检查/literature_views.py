"""Generate literature catalog views from note frontmatter; never write into Paper."""
from pathlib import Path
import argparse,json,posixpath,re,subprocess,yaml
from urllib.parse import quote
ROOT=Path('/Users/wangyuelin/Desktop/Obsidian/Paper')
BRIDGE=Path('/Users/wangyuelin/.hermes/profiles/academic/bin/mac-paper')
LINK_SOURCE='README.md'
SPECIAL={'README.md','畲族文献阅读索引.md','景宁畲族传统民居建筑风貌研究综述.md','核心文献网络补充与综述修订记录.md','文献提炼模板.md','文献总索引.md','文献库维护规则.md'}
KIND={'paper-reading':'单篇阅读','literature-reading-evidence':'单篇阅读','paper-data-collection-ledger':'专题拆解','chapter-citation-map':'专题拆解'}
ENTRY_OVERRIDES={'倾斜摄影模型利用':'证据与阅读记录.md'}

def read(path):
    r=subprocess.run([str(BRIDGE),'read',path],capture_output=True,text=True,check=True)
    d=json.loads(r.stdout)
    if not d.get('ok'):raise RuntimeError(d)
    return d['result']['text']

def meta(text):
    m=re.match(r'^---\n(.*?)\n---',text,re.S)
    if not m:return {}
    return yaml.safe_load(m.group(1)) or {}

def title_of(p,text,fm):
    if fm.get('title'):return str(fm['title'])
    m=re.search(r'^#\s+(.+)$',text,re.M)
    return m.group(1).strip() if m else p.stem

def authors_of(fm):
    a=fm.get('authors') or fm.get('author') or ''
    return '、'.join(map(str,a)) if isinstance(a,list) else str(a)

def zotero_of(fm):
    z=fm.get('zotero_item') or fm.get('zotero_key') or ''
    pid=str(fm.get('paper_id') or '')
    if not z and pid.startswith('zotero:'):z=pid.split(':',1)[1]
    att=fm.get('zotero_attachment') or ''
    return (str(z)+(' / PDF '+str(att) if att else '')) if z else '—'

def doi_of(fm):
    d=fm.get('doi') or ''
    if not d:
        pid=str(fm.get('paper_id') or '')
        if pid.startswith('doi:'):d=pid.split(':',1)[1]
    return str(d) if d else '—'

def cell(v):return str(v).replace('|','／').replace('\n',' ')
def cut(v,n=105):
    s=cell(v or '—');return s if len(s)<=n else s[:n-1]+'…'
def link(p,label=None):
    target=quote(posixpath.relpath(p,posixpath.dirname(LINK_SOURCE) or '.'))
    return '['+(label or Path(p).name)+']('+target+')'
def block(text,name,body):
    begin='<!-- '+name+':start -->';end='<!-- '+name+':end -->';new=begin+'\n'+body.rstrip()+'\n'+end
    assert text.count(begin)==1 and text.count(end)==1,(name,'missing/duplicate block markers')
    a,b=text.split(begin);_,c=b.split(end);return a+new+c

def collect(read_fn):
    items=[]
    for p in sorted((ROOT/'文献库').glob('*.md')):
        if p.name in SPECIAL:continue
        rel=p.relative_to(ROOT).as_posix();text=read_fn(rel);fm=meta(text)
        reading=fm.get('reading_status') or fm.get('read_status') or ''
        if not reading:
            st=str(fm.get('status') or '')
            if 'read' in st.lower() or '精读' in st or '初读' in st:reading=st
        items.append(dict(path=rel,title=title_of(p,text,fm),authors=authors_of(fm),year=fm.get('year') or '',
                          kind=KIND.get(str(fm.get('type')),'阅读记录'),reading=reading or '—',
                          scope=fm.get('read_scope') or '—',topics=fm.get('topics') or [],zotero=zotero_of(fm),doi=doi_of(fm),type=fm.get('type','')))
    items.sort(key=lambda x:(str(x['year']) if x['year'] else '9999',x['title']))
    return items

def single_table(items,base):
    global LINK_SOURCE;LINK_SOURCE=base
    b='| 文献 | 年 | 类型 | 阅读状态 | 阅读范围（摘要） | Zotero | DOI | 关键词 |\n|---|---|---|---|---|---|---|---|\n'
    for x in items:
        topics='、'.join(map(str,x['topics'])) if x['topics'] else '—'
        b+=f"| {link(x['path'],x['title'])} | {cell(x['year'] or '—')} | {x['kind']} | {cell(x['reading'])} | {cut(x['scope'])} | {cell(x['zotero'])} | {cell(x['doi'])} | {cell(topics)} |\n"
    return b

def topic_rows():
    rows=[]
    for d in sorted((ROOT/'文献库/专题精读').iterdir()):
        if not d.is_dir() or d.name.startswith('.'):continue
        files=[p for p in d.rglob('*.md') if not p.name.endswith('.smm.md')]+list(d.rglob('*.smm.md'))
        entry=(d/ENTRY_OVERRIDES[d.name]) if d.name in ENTRY_OVERRIDES else (d/'README.md')
        if not entry.is_file():
            cand=sorted(d.glob('*.smm.md'))
            entry=cand[0] if cand else d
        rows.append((d,entry,len(files)))
    return rows

def map_rows():
    rows=[]
    for d in sorted((ROOT/'文献库/文献导图').iterdir()):
        if not d.is_dir():continue
        maps=list(d.glob('*.smm.md'));entry=d/'README.md'
        if not entry.is_file():entry=(d/'00-阅读总览.smm.md') if (d/'00-阅读总览.smm.md').is_file() else d
        rows.append((d,entry,len(maps)))
    return rows

def generate(read_fn):
    global LINK_SOURCE
    items=collect(read_fn);out={}
    topics=topic_rows();maps=map_rows()
    # Full catalog
    p='文献库/文献总索引.md';base=p;LINK_SOURCE=base
    b='---\nwiki_id: literature-master-index\ntype: literature-index\nstatus: generated\nsummary: 从单篇笔记frontmatter与专题目录生成的文献总索引\nupdated: 2026-11-04\n---\n\n# 文献总索引\n\n> 本页由 `项目管理/健康检查/literature_views.py` 从笔记 frontmatter 与目录结构生成。阅读状态、页码与范围取自原笔记；本页不重新精读、不核验 Zotero 元数据，也不把专题包或导图重复计作独立论文。\n\n'
    b+=f'## 单篇与专题拆解（{len(items)}）\n\n'+single_table(items,base)
    b+=f'\n## 专题精读包（{len(topics)}）\n\n| 专题包 | 文件数（参考） |\n|---|---|\n'
    for d,entry,n in topics:b+=f"| {link(entry.relative_to(ROOT).as_posix(),d.name)} | {n} |\n"
    b+='\n文件数是页面／导图工作量提示，不是论文篇数或精读完成度；具体来源和阅读范围以包内说明为准。\n'
    b+=f'\n## 原生导图（{sum(n for _,_,n in maps)}）\n\n| 导图组 | 导图数 |\n|---|---|\n'
    for d,entry,n in maps:b+=f"| {link(entry.relative_to(ROOT).as_posix(),d.name)} | {n} |\n"
    b+='\n导图是阅读与比较视图，不单独构成一篇文献或一条新证据。\n'
    b+='\n## 专项记录\n\n- '+link('文献库/核读记录/README.md','核读记录')+'：独立复核与读回记录。\n- '+link('文献库/文献获取/README.md','文献获取记录')+'：下载、受阻与访问路径。\n- '+link('文献库/畲族文献阅读索引.md','畲族文献阅读索引')+'：既有来源清单入口。\n- '+link('文献库/景宁畲族传统民居建筑风貌研究综述.md','研究综述')+'：综述正文。\n'
    out[p]=b
    # README summary block
    p='文献库/README.md';base=p;LINK_SOURCE=base
    s=read_fn(p)
    b=f'## 文献总索引\n\n本区现有单篇与专题拆解 **{len(items)}** 篇、专题精读包 **{len(topics)}** 个、原生导图 **{sum(n for _,_,n in maps)}** 张。完整表见 {link("文献库/文献总索引.md","文献总索引")}。\n\n'
    b+=f'- 单篇与专题拆解：按年份列出阅读状态、阅读范围、Zotero／DOI 与关键词。\n- 专题精读包：{len(topics)} 个，入口与文件数见总索引。\n- 原生导图：{sum(n for _,_,n in maps)} 张，属于阅读与比较视图。\n- 维护规则：{link("文献库/文献库维护规则.md","文献库维护规则")}。\n'
    out[p]=block(s,'literature-catalog',b)
    # Topic package index
    p='文献库/专题精读/README.md';base=p;LINK_SOURCE=base
    b='---\nwiki_id: literature-topic-readings-index\ntype: literature-index\nstatus: generated\nsummary: 专题精读包入口；不重复宣称全文精读\nupdated: 2026-11-04\n---\n\n# 专题精读\n\n> 专题包围绕一个来源或一个问题组织多页阅读、比较与讨论。包内页面不等于多篇独立精读；具体来源、页码和阅读范围以各包说明为准。\n\n| 专题包 | 文件数（参考） |\n|---|---|\n'
    for d,entry,n in topics:b+=f"| {link(entry.relative_to(ROOT).as_posix(),d.name)} | {n} |\n"
    b+='\n专题之间的材料可以互相参照，但不在本页合并为“已读论文总数”。\n'
    out[p]=b
    # Map index
    p='文献库/文献导图/README.md';base=p;LINK_SOURCE=base
    b='---\nwiki_id: literature-maps-index\ntype: literature-index\nstatus: generated\nsummary: 原生阅读导图入口；导图是阅读视图，不是独立证据\nupdated: 2026-11-04\n---\n\n# 文献导图\n\n> 导图用于组织阅读、比较和提问，不单独构成论文、证据或研究结论。原论文与单篇笔记仍是引用和定位主源。\n\n| 导图组 | 导图数 |\n|---|---|\n'
    for d,entry,n in maps:b+=f"| {link(entry.relative_to(ROOT).as_posix(),d.name)} | {n} |\n"
    b+='\n导图节点中的判断若进入正式研究，应在主题页、论点页或成果包中另找依据，不以导图本身替代引文。\n'
    out[p]=b
    # Review records
    p='文献库/核读记录/README.md';base=p;LINK_SOURCE=base
    b='---\nwiki_id: literature-review-records\ntype: literature-index\nstatus: generated\nsummary: 独立复核与读回记录入口\nupdated: 2026-11-04\n---\n\n# 核读记录\n\n本目录保存独立复核、读回与验收记录，不是论文正文或新的研究结论。\n\n'
    for q in sorted((ROOT/'文献库/核读记录').glob('*.md')):
        if q.name!='README.md':b+=f"- {link(q.relative_to(ROOT).as_posix(),q.stem)}\n"
    b+='\n复核通过只表示该次检查的对象与范围，不自动提升原论文或原成果的实证状态。\n'
    out[p]=b
    # Acquisition records
    p='文献库/文献获取/README.md';base=p;LINK_SOURCE=base
    b='---\nwiki_id: literature-acquisition-records\ntype: literature-index\nstatus: generated\nsummary: 文献下载与获取状态记录入口\nupdated: 2026-11-04\n---\n\n# 文献获取记录\n\n本目录保存下载清单、受阻截图与访问路径，不替代 Zotero 中的原始 PDF，也不表示全文已读。\n\n'
    for q in sorted((ROOT/'文献库/文献获取').glob('*.md')):
        if q.name!='README.md':b+=f"- {link(q.relative_to(ROOT).as_posix(),q.stem)}\n"
    b+='\n原始 PDF 仍以 Zotero 为准；获取成功不等于阅读或证据核验完成。\n'
    out[p]=b
    stats={'single_records':len(items),'topic_packages':len(topics),'maps':sum(n for _,_,n in maps),'view_files':len(out)}
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
