"""Generate relationship views from artifact README frontmatter; never write into Paper."""
from pathlib import Path
import argparse,json,posixpath,subprocess,yaml
from urllib.parse import quote
ROOT=Path('/Users/wangyuelin/Desktop/Obsidian/Paper')
BRIDGE=Path('/Users/wangyuelin/.hermes/profiles/academic/bin/mac-paper')
def read(path):
    r=subprocess.run([str(BRIDGE),'read',path],capture_output=True,text=True,check=True)
    d=json.loads(r.stdout)
    if not d.get('ok'):raise RuntimeError(d)
    return d['result']['text']
def meta(text):
    if not text.startswith('---\n'):raise ValueError('README lacks relationship metadata')
    return yaml.safe_load(text.split('---',2)[1])
LINK_SOURCE='README.md'
TOPIC_ROLES={}
GROUPS={'current':'现行主源','candidate':'现行候选','prototype':'过程原型','redirect':'统一原型入口','display':'展示与讨论','record':'文献核查记录'}
GROUP_ORDER=['current','candidate','prototype','redirect','display','record']
GROUP_DESC={
 'current':'现行工作直接依赖、仍在维护的主源与成果。',
 'candidate':'仍在讨论或试采、尚未成为正式字段或规则的候选成果。',
 'prototype':'早期框架、模型原型或演示，保留用于追溯，不作为现行主源。',
 'redirect':'统一原型建立后保留的分析入口，详见对应主源。',
 'display':'展示、汇报或讨论视图，不独立计作研究验证。',
 'record':'文献综述或审阅过程的冻结记录，不是当前分析结论。',
}
REL_TYPES={'merges','supersedes','builds_on'}
REL_LABEL={'merges':'合并','supersedes':'替代','builds_on':'建立于'}
REL_OUT={'merges':'合并前置','supersedes':'替代前置','builds_on':'建立于'}
REL_IN={'merges':'被合并入','supersedes':'被替代','builds_on':'被后续成果引用'}
def link(p,label=None):
    target=quote(posixpath.relpath(p,posixpath.dirname(LINK_SOURCE) or '.'))
    if p in TOPIC_ROLES and label and not label.startswith('〔'):
        label='〔'+TOPIC_ROLES[p]+'〕'+label
    return '['+(label or Path(p).name)+']('+target+')'
def block(text,name,body,anchor=None):
    begin='<!-- '+name+':start -->';end='<!-- '+name+':end -->';new=begin+'\n'+body.rstrip()+'\n'+end
    if begin in text:
        assert text.count(begin)==1 and text.count(end)==1
        a,b=text.split(begin);_,c=b.split(end);return a+new+c
    if anchor and anchor in text:return text.replace(anchor,new+'\n\n'+anchor,1)
    return text.rstrip()+'\n\n'+new+'\n'
def cell(value):return str(value).replace('|','／').replace('\n',' ')
def discover_topics(read_fn,root=ROOT):
    result={};ids=set()
    for q in sorted(root.glob('主题研究/*/*.md')):
        p=q.relative_to(root).as_posix();s=read_fn(p)
        if not s.startswith('---\n'):continue
        m=meta(s)
        if m.get('type')!='research-topic':continue
        title=m['topic_title'];uid=m['wiki_id'];role=m['research_role']
        assert title and title not in result and uid not in ids,'duplicate/empty topic identity'
        expected='〔'+role+'〕'+title
        assert q.parent.name==expected and q.stem==expected,'topic role/title changed: migrate paths explicitly'
        ids.add(uid);result[title]={'path':p,'meta':m}
    assert result,'no research topics discovered'
    return result
def generate(read_fn,root=ROOT):
    global LINK_SOURCE,TOPIC_ROLES
    packages=sorted(p for p in (root/'研究成果').iterdir() if p.is_dir() and not p.name.startswith('.'))
    discovered=discover_topics(read_fn,root);topics=sorted(discovered);topic_paths={t:v['path'] for t,v in discovered.items()}
    TOPIC_ROLES={v['path']:v['meta']['research_role'] for v in discovered.values()}
    items=[];out={}
    for directory in packages:
        p=str((directory/'README.md').relative_to(root));LINK_SOURCE=p;s=read_fn(p);m=meta(s)
        primary=m['artifact_primary_topic'];roles=m['artifact_topic_roles'];sources=m['artifact_main_sources']
        assert primary in roles and set(roles)<=set(topics),(p,'unknown topic')
        assert sources and all((root/x).is_file() or bool(read_fn(x)) for x in sources),(p,'missing main source')
        assert m['artifact_boundary'] and m['artifact_state'] and m['artifact_kind']
        group=m.get('artifact_group');assert group in GROUPS,(p,'missing/unknown artifact_group')
        display='〔'+m['artifact_label']+'〕'+m['artifact_title']
        assert directory.name==display,'artifact label/title changed: migrate directory explicitly'
        items.append(dict(path=p,name=display,meta=m,text=s))
    by_path={x['path']:x for x in items}
    incoming={}
    for x in items:
        for r in x['meta'].get('artifact_relations') or []:
            assert r.get('to') in by_path,(x['path'],'artifact relation target must be an existing package README')
            assert r.get('type') in REL_TYPES,(x['path'],'unknown artifact relation type')
            assert r['to']!=x['path'],(x['path'],'self artifact relation')
            incoming.setdefault(r['to'],[]).append((x,r))
    edges=[(x,r) for x in items for r in (x['meta'].get('artifact_relations') or [])]
    for x in items:
        p=x['path'];m=x['meta'];s=x['text']
        primary=m['artifact_primary_topic'];roles=m['artifact_topic_roles'];sources=m['artifact_main_sources'];group=m['artifact_group']
        b='## 主题归属与使用边界\n\n> 本节由本文件 frontmatter 的 artifact_* 字段生成。主要主题是维护归口；分类与状态不构成新增研究结论或验收。\n\n'
        b+=f"- **产物类型**：〔{m['artifact_label']}〕{m['artifact_kind']}\n- **成果层级**：{GROUPS[group]}\n- **当前状态**：{m['artifact_state']}\n- **主要主题**：{link(topic_paths[primary],primary)}\n"
        b+='- **复用主题**：'+('、'.join(link(topic_paths[t],t) for t in roles if t!=primary) or '暂无另行列出的复用主题')+'\n\n'
        b+='| 主题 | 关系 | 在该主题中的用途 |\n|---|---|---|\n'
        for t,role in roles.items():b+=f"| {link(topic_paths[t],t)} | {'主要归口' if t==primary else '复用'} | {cell(role)} |\n"
        rels=m.get('artifact_relations') or []
        rev=incoming.get(p,[])
        if rels or rev:
            b+='\n### 成果递进关系\n\n> 仅记录有明确依据的前后关系；方向为后继→前置，无记录不代表没有关系。\n\n'
            for r in rels:
                b+=f"- **{REL_OUT[r['type']]}**：{link(r['to'],by_path[r['to']]['name'])}"+(f"（{r['note']}）" if r.get('note') else '')+'\n'
            for x2,r in rev:
                b+=f"- **{REL_IN[r['type']]}**：{link(x2['path'],x2['name'])}"+(f"（{r['note']}）" if r.get('note') else '')+'\n'
            b+='\n'
        b+='### 维护主源与派生边界\n\n'+'\n'.join('- '+link(x) for x in sources)+'\n\n'+m['artifact_boundary']+'\n\n原件与历史记录仍按本包原说明维护；不把展示导出、快照或链接存在当作研究验证。\n'
        out[p]=block(s,'artifact-relations',b,'## ')
    for t in topics:
        p=topic_paths[t];LINK_SOURCE=p;s=read_fn(p)
        b='## 关联成果、用途与状态\n\n> 本表从各成果包 README 的关系字段派生；研究判断仍在本主题维护。修改定义、模型或数据请进入相应包的维护主源，不在这里复制一份。\n\n'
        b+='| 成果包 | 层级 | 本主题中的关系 | 用途 | 当前状态 |\n|---|---|---|---|---|\n'
        for x in items:
            m=x['meta']
            if t in m['artifact_topic_roles']:
                b+=f"| {link(x['path'],x['name'])} | {GROUPS[m['artifact_group']]} | {'主要归口' if t==m['artifact_primary_topic'] else '复用'} | {cell(m['artifact_topic_roles'][t])} | {cell(m['artifact_state'])} |\n"
        b+='\n完整状态与限制见对应成果入口；跨主题使用不等于重复维护，也不等于已进入论文或通过实证验证。\n'
        topic_edges=[(x,r) for x,r in edges if x['meta']['artifact_primary_topic']==t or by_path[r['to']]['meta']['artifact_primary_topic']==t]
        if topic_edges:
            b+='\n### 本主题中的成果递进\n\n> 仅列有明确依据的关系；跨主题关系在两端主题都可出现。方向为后继→前置。\n\n| 后继成果 | 关系 | 前置成果 | 说明 |\n|---|---|---|---|\n'
            for x,r in topic_edges:
                b+=f"| {link(x['path'],x['name'])} | {REL_LABEL[r['type']]} | {link(r['to'],by_path[r['to']]['name'])} | {cell(r.get('note',''))} |\n"
            b+='\n'
        out[p]=block(s,'topic-artifacts',b,'## 验证反例与待解决问题')
    p='研究成果/README.md';LINK_SOURCE=p;s=read_fn(p)
    b='## 成果包层级与主要主题\n\n本目录保存广义研究产物，包括依据整理、候选稿、过程原型和展示包，不都是原创或已验证成果。表内只列本目录实际存在的一级成果包；层级说明维护状态，主要主题是维护归口，复用主题及主源见包内入口。\n\n'
    for key in GROUP_ORDER:
        subset=[x for x in items if x['meta']['artifact_group']==key]
        if not subset:continue
        b+=f"### {GROUPS[key]}（{len(subset)}）\n\n{GROUP_DESC[key]}\n\n| 成果包 | 主要主题 | 产物类型 | 状态 |\n|---|---|---|---|\n"
        for x in subset:
            m=x['meta'];t=m['artifact_primary_topic'];b+=f"| {link(x['path'],x['name'])} | {link(topic_paths[t],t)} | {cell(m['artifact_kind'])} | {cell(m['artifact_state'])} |\n"
        b+='\n'
    b+='## 成果演进\n\n> 仅列各包 README 明确记录的前后关系；方向为后继→前置。无记录不代表没有关系，也不能据版本号推断。\n\n'
    if edges:
        b+='| 后继成果 | 关系 | 前置成果 | 说明 |\n|---|---|---|---|\n'
        for x,r in edges:
            b+=f"| {link(x['path'],x['name'])} | {REL_LABEL[r['type']]} | {link(r['to'],by_path[r['to']]['name'])} | {cell(r.get('note',''))} |\n"
        b+='\n'
    else:
        b+='当前尚无已记录的关系。\n\n'
    out[p]=block(s,'artifact-catalog',b)
    p='主题研究/README.md';LINK_SOURCE=p;s=read_fn(p)
    b='## 主题与成果的对应入口\n\n主题页维护问题、分析与判断；成果包维护具体产物；章节再选择主题认识及其证据。点击主题查看用途，点击成果入口查看主源和边界。\n\n'
    b+='| 主题 | 主要归口包数 | 复用包数 |\n|---|---:|---:|\n'
    for t in topics:
        own=sum(x['meta']['artifact_primary_topic']==t for x in items)
        reuse=sum(t in x['meta']['artifact_topic_roles'] and x['meta']['artifact_primary_topic']!=t for x in items)
        b+=f"| {link(topic_paths[t],t)} | {own} | {reuse} |\n"
    b+='\n数量只表示导航关系，不是研究工作量、成果质量或完成度。'+link('项目管理/主题成果关系维护.md','关系维护说明')+'。\n'
    out[p]=block(s,'topic-catalog',b)
    stats={'packages':len(items),'topics':len(topics),'relations':sum(len(x['meta']['artifact_topic_roles']) for x in items),'primary_relations':len(items),'reused_relations':sum(len(x['meta']['artifact_topic_roles'])-1 for x in items),'progression_edges':len(edges),'view_files':len(out)}
    return out,stats
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check',action='store_true');ap.add_argument('--output-dir',type=Path);args=ap.parse_args()
    if not args.check and not args.output_dir:ap.error('choose --check or --output-dir')
    if args.output_dir and args.output_dir.resolve().is_relative_to(ROOT.resolve()):ap.error('output-dir must be outside Paper; use guarded mac-paper upload after review')
    cache={}
    def cached(p):
        if p not in cache:cache[p]=read(p)
        return cache[p]
    out,stats=generate(cached);changed=[p for p,s in out.items() if s!=cached(p)]
    if args.output_dir:
        for p,s in out.items():
            f=args.output_dir/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
    print(json.dumps({**stats,'out_of_sync':changed},ensure_ascii=False,indent=2))
    if args.check and changed:raise SystemExit(1)
