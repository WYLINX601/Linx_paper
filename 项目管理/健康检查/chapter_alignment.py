"""Generate the v0.6-to-current chapter migration map; never write into Paper."""
from pathlib import Path
import argparse,json,posixpath,subprocess,yaml
from urllib.parse import quote
ROOT=Path('/Users/wangyuelin/Desktop/Obsidian/Paper')
BRIDGE=Path('/Users/wangyuelin/.hermes/profiles/academic/bin/mac-paper')
LINK_SOURCE='论文章节/维护/章节迁移映射.md'
ACTIONS={'rewrite':'改写','split':'拆分','merge':'合并','move':'移入','keep':'保留','new':'新写','retire':'停用'}
SHORT={'第一章 绪论':'第一章','第二章 景宁畲族传统民居研究对象与多尺度资料基础':'第二章','第三章 传统民居多尺度风貌特征提取与知识图谱组织体系设计':'第三章','第四章 景宁畲族典型村落风貌特征提取与知识图谱构建':'第四章','第五章 基于知识图谱的景宁畲族传统民居建筑风貌综合认知':'第五章','第六章 结论与展望':'第六章'}

def read(path):
    r=subprocess.run([str(BRIDGE),'read',path],capture_output=True,text=True,check=True)
    d=json.loads(r.stdout)
    if not d.get('ok'):raise RuntimeError(d)
    return d['result']['text']

def link(p,label=None):
    path,_,anchor=p.partition('#')
    target=quote(posixpath.relpath(path,posixpath.dirname(LINK_SOURCE) or '.'))
    if anchor:target+='#'+anchor
    return '['+(label or Path(p).name)+']('+target+')'
def cell(v):return str(v).replace('|','／').replace('\n',' ')

def generate(read_fn):
    global LINK_SOURCE
    outline=yaml.safe_load(read_fn('论文章节/大纲结构.yaml'))
    m=yaml.safe_load(read_fn('论文章节/维护/章节迁移映射.yaml'))
    chapters={c['id']:c for c in outline['chapters'] if c.get('included')}
    current={}
    section_ids=set()
    subsection_ids=set()
    for c in chapters.values():
        for s in c.get('sections',[]):
            if not s.get('included'):continue
            current[s['id']]=(c['id'],s)
            section_ids.add(s['id'])
            for sub in s.get('subsections',[]):
                if sub.get('included'):
                    current[sub['id']]=(c['id'],sub)
                    subsection_ids.add(sub['id'])
    rows=[]
    for r in m['mappings']:
        assert r.get('action') in ACTIONS,(r,'bad action')
        cur=r.get('current') or []
        assert cur,(r,'no current section')
        for sid in cur:assert sid in current,(r,'unknown current section',sid)
        if r.get('old') is None:assert r['action']=='new',(r,'old null must be new')
        rows.append(r)
    covered={sid for r in rows for sid in r['current']}
    missing=[sid for sid in section_ids if sid not in covered]
    assert not missing,('unmapped current sections',missing)
    # group by current chapter in outline order
    groups={cid:[] for cid in chapters}
    for r in rows:
        cid,sec=current[r['current'][0]]
        groups[cid].append((r,sec))
    p='论文章节/维护/章节迁移映射.md';LINK_SOURCE=p
    b='---\nwiki_id: chapter-migration-map\ntype: derived-index\nstatus: generated\nsummary: v0.6正文节点与现行大纲活动节的迁移映射\nupdated: 2026-11-04\n---\n\n# 章节迁移映射\n\n> 本页由 `项目管理/健康检查/chapter_alignment.py` 从大纲结构与迁移映射生成。它只表示施工关系，不表示正文已完成、引文已核或结论已成立；“新写”不等于没有旧稿素材，只表示没有可直接对应的旧节。\n\n'
    old_count=len({r['old'] for r in rows if r['old']})
    new_count=sum(1 for r in rows if r['action']=='new')
    b+=f'- 旧稿节：**{old_count}**；新写节：**{new_count}**；现行二级节：**{len(section_ids)}**；现行三级节：**{len(subsection_ids)}**；已覆盖二级节：**{len(covered & section_ids)}**；已覆盖三级节：**{len(covered & subsection_ids)}**。\n- 三级节只在旧稿有直接对应时单列；第二章三级节沿用父节映射，不表示未覆盖。\n- 动作词：改写／拆分／合并／移入／保留／新写。\n\n'
    for n,(cid,c) in enumerate(chapters.items(),1):
        b+=f"## 第{n}章 {c['title']}\n\n| 旧稿来源 | 现行节 | 动作 | 说明 |\n|---|---|---|---|\n"
        for r,sec in groups[cid]:
            if r['old']:
                old=SHORT.get(r['old_chapter'],r['old_chapter'] or '旧稿')+' · '+r['old']
            else:old='—'
            links='、'.join(link(chapters[cid]['path']+'#'+sid, current[sid][1]['title']) for sid in r['current'])
            b+=f"| {cell(old)} | {links} | {ACTIONS[r['action']]} | {cell(r.get('note',''))} |\n"
        b+='\n'
    b+='## 使用边界\n\n- 本映射是正文改写的施工图，不是正文替代；具体段落的保留、删改和引文核对仍需逐段处理。\n- “移入”表示旧稿内容应进入另一章，不表示已经移动或改写。\n- “新写”表示现行节没有可直接对应的旧节；可引用旧稿素材，但不能把旧稿结论直接搬过来。\n- 章节职责和稳定 ID 以[[论文章节/大纲结构.yaml|大纲结构]]为准；本页不新增、不删除、不重排节。\n'
    stats={'old_sections':old_count,'new_sections':new_count,'current_sections':len(section_ids),'current_subsections':len(subsection_ids),'mapped_sections':len(covered & section_ids),'mapped_subsections':len(covered & subsection_ids),'mapped_rows':len(rows),'out_of_sync':[]}
    return {p:b},stats

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check',action='store_true');ap.add_argument('--output-dir',type=Path);args=ap.parse_args()
    if not args.check and not args.output_dir:ap.error('choose --check or --output-dir')
    if args.output_dir and args.output_dir.resolve().is_relative_to(ROOT.resolve()):ap.error('output-dir must be outside Paper')
    cache={}
    def cached(p):
        if p not in cache:cache[p]=read(p)
        return cache[p]
    def current_text(p):
        try:return cached(p)
        except subprocess.CalledProcessError:return None
    out,stats=generate(cached);changed=[p for p,s in out.items() if current_text(p)!=s]
    if args.output_dir:
        for p,s in out.items():
            f=args.output_dir/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
    print(json.dumps({**stats,'changed':changed},ensure_ascii=False,indent=2))
    if args.check and changed:raise SystemExit(1)
