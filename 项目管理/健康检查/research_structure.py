"""Read-only generation of dynamic research views. Publish reviewed output via mac-paper."""
from pathlib import Path
import argparse,hashlib,json,posixpath,re,subprocess,yaml
from urllib.parse import quote
import topic_artifact_views as artifacts
import research_questions as thesis
ROOT=Path(__file__).resolve().parents[2]
BRIDGE='/Users/wangyuelin/.hermes/profiles/academic/bin/mac-paper'
OUTLINE='论文章节/大纲结构.yaml'
ROUTE='研究成果/〔研究路线〕论文研究路径/研究路径结构.json'
ROLES=('研究界定','理论与文献依据','体系设计','研究方法','操作方法','检验与评价')
ROLE_PURPOSE={'研究界定':'研究什么、不研究什么','理论与文献依据':'已有认识、借鉴依据与缺口','体系设计':'对象、信息和关系如何组成整体','研究方法':'如何获得认识及其依据','操作方法':'如何执行、记录与复核','检验与评价':'如何判断有效性及适用边界'}
def read(path):
    if Path(path).name.startswith('._'):return ''
    p=subprocess.run([BRIDGE,'read',path],capture_output=True,text=True,check=True);r=json.loads(p.stdout)
    if not r.get('ok'):raise RuntimeError(r)
    return r['result']['text']
def meta(s):return artifacts.meta(s)
def header(s,fm):
    body=s.split('---',2)[2].lstrip('\n') if s.startswith('---\n') else s
    return '---\n'+yaml.safe_dump(fm,allow_unicode=True,sort_keys=False,width=120)+'---\n\n'+body
def note(uid,title,body):return header('# '+title+'\n\n'+body,{'wiki_id':uid,'type':'derived-index','status':'active','summary':title})
def link(source,target,label):return '['+label.replace('|','／')+']('+quote(posixpath.relpath(target.split('#')[0],posixpath.dirname(source) or '.'))+('#'+quote(target.split('#',1)[1]) if '#' in target else '')+')'
def clean(s):return str(s).replace('|','／').replace('\n',' ')
def label(s):return str(s).replace('&','&amp;').replace('"','&quot;').replace('<','&lt;').replace('>','&gt;').replace('\n',' ')
def topic_name(path):return re.sub(r'^〔[^〕]+〕','',Path(path).parent.name)

def validate(model,topics,root=ROOT):
    assert model['schema_version']==1 and model['chapters'],'invalid outline schema'
    ids=set();paths=set();section_ids=set();subsection_ids=set()
    for c in model['chapters']:
        assert re.fullmatch(r'[A-Za-z][\w-]*',c['id']) and c['id'] not in ids,'duplicate/invalid chapter id'
        ids.add(c['id']);assert re.match(r'^论文章节/(?:章节导航/[^/]+\.md|[^/]+/章节导航\.md)$',c['path']) and '..' not in Path(c['path']).parts and c['path'] not in paths,'invalid chapter path';paths.add(c['path'])
        assert isinstance(c['included'],bool) and c['title'] and c['purpose'] and c['status']
        bs=c.get('body_source')
        if bs:assert (root/bs.split('#')[0]).is_file(),'body source missing'
        else:assert c.get('body_note'),'chapter needs body_source or body_note'
        for s in c['sections']:
            assert re.fullmatch(r'[A-Za-z][\w-]*',s['id']) and s['id'] not in section_ids,'duplicate/invalid section id'
            section_ids.add(s['id']);assert isinstance(s['included'],bool) and s['title'] and s['purpose'] and s['status'] and s['change_note']
            assert s['topics'] and len(set(s['topics']))==len(s['topics']) and set(s['topics'])<=set(topics),'unknown/duplicate topic'
            assert isinstance(s.get('subsections',[]),list),'subsections must be a list'
            for sub in s.get('subsections',[]):
                assert re.fullmatch(r'[A-Za-z][\w-]*',sub['id']) and sub['id'] not in subsection_ids,'duplicate/invalid subsection id'
                subsection_ids.add(sub['id'])
                assert isinstance(sub['included'],bool) and all(sub.get(k) for k in ('title','purpose','status','change_note')),'incomplete subsection'
                assert not sub.get('subsections'),'only three outline levels supported'
    assert not (ids & section_ids or ids & subsection_ids or section_ids & subsection_ids),'outline ids must be globally unique'
    for c in model['chapters']:
        for s in c['sections']:
            for sub in s.get('subsections',[]):
                assert sub.get('origin_chapter_path',c['path']) in paths,'unknown subsection origin'
    # Keep explicit inactive nodes, rather than silently orphaning an old navigation file.
    for p in root.glob('论文章节/*/章节导航.md'):
        if str(p.relative_to(root)) not in paths:raise ValueError('existing chapter missing; retain it with included: false: '+str(p))

def adoption_records(model):
    rows=[];n=0
    for c in model['chapters']:
        if not c['included']:continue
        n+=1;j=0
        for s in c['sections']:
            if not s['included']:continue
            j+=1
            for topic in s['topics']:rows.append({'chapter':c['path'],'section':f'{n}.{j} '+s['title'],'topic':topic,'status':s['status'],'chapter_id':c['id'],'section_id':s['id'],'purpose':s['purpose']})
    return rows

def adoption_body(rows,topics=None):
    p='项目管理/章节主题映射.md';body='本表由[[论文章节/大纲结构.yaml|大纲结构主源]]生成；采用状态只在该主源维护。章节顺序和编号可变，节点ID保持稳定。\n'
    for t in sorted({x['topic'] for x in rows}):
        name=topic_name(t);primary=(topics or {}).get(t,{}).get('research_role')
        body+='\n## '+('〔'+primary+'〕' if primary else '')+name+'\n\n'+link(p,t,'主题主源')+'\n\n'
        for x in rows:
            if x['topic']==t:body+='- '+link(p,x['chapter']+'#'+x['section_id'],x['section'])+'：'+x['status']+'。\n'
    return note('map-adoption','章节—主题反向入口',body)

def validate_route(route,topics):
    route=thesis.resolve_route(route)
    assert route['schema_version']==1 and route['nodes']
    ids=[n['id'] for n in route['nodes']];assert len(ids)==len(set(ids))
    graph={i:[] for i in ids}
    for n in route['nodes']:
        assert re.fullmatch(r'[A-Za-z][\w-]*',n['id']) and n['title'] and n['status']
        assert set(n['topics'])<={topic_name(t) for t in topics}
    for e in route['edges']:
        assert e['from'] in ids and e['to'] in ids and e['kind'] in ('dependency','feedback') and e['label']
        if e['kind']=='dependency':graph[e['from']].append(e['to'])
    done=set();visiting=set()
    def visit(i):
        assert i not in visiting,'dependency cycle; label feedback explicitly'
        if i in done:return
        visiting.add(i)
        for j in graph[i]:visit(j)
        visiting.remove(i);done.add(i)
    for i in ids:visit(i)

def generate(read_fn,root=ROOT):
    model=yaml.safe_load(read_fn(OUTLINE));route_source=json.loads(read_fn(ROUTE));route=thesis.resolve_route(route_source);topics={};out={}
    discovered=artifacts.discover_topics(read_fn,root)
    for info in discovered.values():
        p=info['path'];s=read_fn(p);m=meta(s)
        assert m['research_role'] in ROLES and set(m['research_roles_secondary'])<=set(ROLES) and m['research_role'] not in m['research_roles_secondary']
        expected=['研究角色/'+r for r in [m['research_role']]+m['research_roles_secondary']]
        m['tags']=[t for t in m.get('tags',[]) if not t.startswith('研究角色/')]+expected
        s=header(s,m)
        topics[p]=m
        role='**研究角色：〔'+m['research_role']+'〕**　辅助角色：'+('、'.join(m['research_roles_secondary']) or '无')+'。\n\n角色说明本主题承担的职责，不表示章节归属、研究进度或已验证；主角色和辅助角色只在本主题页维护，标签与展示前缀由它们生成。\n'
        out[p]=artifacts.block(s,'research-role',role,'## 问题与范围')
    validate(model,topics,root);validate_route(route_source,topics)
    for p,m in topics.items():
        assert len(set(m['research_roles_secondary']))==len(m['research_roles_secondary'])
    # First update artifact relationship views using the same role metadata.
    ar,arstats=artifacts.generate(lambda p:out.get(p) or read_fn(p),root)
    out.update(ar)
    rows=adoption_records(model);out['项目管理/章节采用记录.json']=json.dumps(rows,ensure_ascii=False,indent=2)+'\n';out['项目管理/章节主题映射.md']=adoption_body(rows,topics)
    overview='flowchart LR\n  outline-root["论文工作大纲"]\n';number=0;active_sections=0;summary=[];retired=[]
    for c in model['chapters']:
        p=c['path'];s=read_fn(p);fm=meta(s) if s.startswith('---\n') else {'wiki_id':c['id'],'type':'chapter-navigation','status':'active','summary':'动态章节导航'}
        fm['outline_id']=c['id'];fm['outline_source']=OUTLINE;fm['outline_included']=c['included'];fm['depends_on']=list(dict.fromkeys([OUTLINE]+fm.get('depends_on',[])))
        if c['included']:number+=1
        visible=f'第{number}章 '+c['title'] if c['included'] else '停用节点：'+c['title']
        m=re.search(r'^# .+$',s,re.M)
        if m:s=s[:m.start()]+'# '+visible+s[m.end():]
        else:s='# '+visible+'\n\n'
        s=header(s,fm)
        b='## 当前工作安排\n\n> 由[[论文章节/大纲结构.yaml|大纲结构]]生成。修改主源后运行同步；文件夹编号仅为历史路径，不决定当前章节顺序。\n\n'
        b+='**本章任务：** '+c['purpose']+'\n\n**结构状态：** '+c['status']+'\n\n'
        if c.get('body_source'):b+=link(p,c['body_source'],'打开既有正文对应章')+'。正文未随结构自动改写。\n\n'
        else:b+='**正文接续：** '+c.get('body_note','无直接旧稿')+'\n\n'
        if c.get('argument_flow'):b+='**章内逻辑：** '+c['argument_flow']+'。\n\n'
        if c.get('handoff'):b+='**向后接续：** '+c['handoff']+'。\n\n'
        if c['included']:
            overview+='  '+c['id']+'["'+label(visible)+'"]\n  outline-root --> '+c['id']+'\n'
            summary.append('| '+link('论文章节/现行大纲.md',p,visible)+' | '+clean(c['purpose'])+' | '+clean(c['status'])+' |')
            b+='## 小节与主题成果采用表\n\n| 小节 | 主题及成果入口 | 本节用途 | 采用状态与证据缺口 |\n|---|---|---|---|\n'
            graph='flowchart LR\n  '+c['id']+'["'+label(visible)+'"]\n';j=0
            for sec in c['sections']:
                if not sec['included']:continue
                j+=1;active_sections+=1;num=f'{number}.{j}';tlinks='、'.join(link(p,t,'〔'+topics[t]['research_role']+'〕'+topic_name(t)) for t in sec['topics'])
                b+='| '+num+' '+clean(sec['title'])+' | '+tlinks+' | '+clean(sec['purpose'])+' | '+clean(sec['status'])+' |\n'
                graph+='  '+sec['id']+'["'+label(num+' '+sec['title'])+'"]\n  '+c['id']+' --> '+sec['id']+'\n'
                for k,sub in enumerate([x for x in sec.get('subsections',[]) if x['included']],1):
                    graph+='  '+sub['id']+'["'+label(num+'.'+str(k)+' '+sub['title'])+'"]\n  '+sec['id']+' --> '+sub['id']+'\n'
            if any(sub['included'] for sec in c['sections'] if sec['included'] for sub in sec.get('subsections',[])):
                b+='\n## 三级标题与论证分工\n\n三级标题用于思路梳理；理论及分析视角是比较对象，不表示全部采用。成果入口和采用关系沿用父节，不重复计数。\n\n| 三级标题 | 论证任务 | 状态 |\n|---|---|---|\n'
                for j,sec in enumerate([x for x in c['sections'] if x['included']],1):
                    for k,sub in enumerate([x for x in sec.get('subsections',[]) if x['included']],1):
                        b+='| '+f'{number}.{j}.{k} '+clean(sub['title'])+' | '+clean(sub['purpose'])+' | '+clean(sub['status'])+' |\n'
            b+='\n## 逐节研究问题与证据要求\n\n以下是待执行的研究要求，不是已完成或已验证声明；采用状态仍以上表为准。\n\n'
            for sec in c['sections']:
                if not sec['included']:continue
                b+='### '+sec['title']+'\n\n- **问题**：'+sec.get('question',sec['purpose'])+'\n'
                b+='- **所需证据／待核材料**：'+'；'.join(sec.get('evidence_required',['待根据研究任务补充']))+'。\n'
                b+='- **完成判据**：'+sec.get('completion_gate','待明确，不以文档存在认定完成')+'。\n\n'
            b+='\n## 本章结构图\n\n```mermaid\n'+graph+'```\n\n## 稳定节点与原稿接续\n\n'
            for sec in c['sections']:
                b+='<a id="'+sec['id']+'"></a>\n- `'+sec['id']+'`：'+sec['title']+'；'+('纳入当前工作大纲' if sec['included'] else '停用、保留追溯')+'。原稿编号：'+sec.get('origin_number','新节点')+'；变更说明：'+sec['change_note']+'。\n'
        else:
            retired.append((p,c['title']));b+='此章暂不纳入当前大纲；正文及证据入口保留，不计入当前采用关系。\n'
            for sec in c['sections']:b+='\n<a id="'+sec['id']+'"></a>\n- 停用节点 `'+sec['id']+'`：'+sec['title']+'。\n'
        subs=[(sec,sub) for sec in c['sections'] for sub in sec.get('subsections',[])]
        if subs:
            b+='\n## 三级稳定节点\n\n'
            for sec,sub in subs:
                active=c['included'] and sec['included'] and sub['included']
                b+='<a id="'+sub['id']+'"></a>\n- `'+sub['id']+'`：'+sub['title']+'；'+('纳入当前工作大纲' if active else '停用、保留追溯')+'；'+sub['change_note']+'。\n'
        moved_subs=[(other,sub) for other in model['chapters'] if other['path']!=p for sec in other['sections'] for sub in sec.get('subsections',[]) if sub.get('origin_chapter_path')==p]
        if moved_subs:
            b+='\n## 已移往其他章节的三级节点\n\n'
            for other,sub in moved_subs:b+='<a id="'+sub['id']+'"></a>\n- '+link(p,other['path']+'#'+sub['id'],sub['title'])+'：三级稳定ID不变，原入口转接。\n'
        moved=[(other,sec) for other in model['chapters'] if other['path']!=p for sec in other['sections'] if sec.get('origin_chapter_path')==p]
        if moved:
            b+='\n## 已移往其他章节的原节点\n\n'
            for other,sec in moved:b+='<a id="'+sec['id']+'"></a>\n- '+link(p,other['path']+'#'+sec['id'],sec['title'])+'：稳定ID不变，原入口转接。\n'
        b+='\n## 调整与反馈\n\n需要调整题名、顺序、节的归属或采用状态时，修改大纲结构；稳定ID不随编号改变。新增、停用、拆分合并必须保留理由及原稿接续，不能由文件数自动认定研究完成。\n'
        out[p]=artifacts.block(s,'dynamic-chapter',b)
    body='**这是可调整的工作大纲，不是定稿目录，也不是正文自动改写结果。**\n\n结构维护：[[论文章节/大纲结构.yaml]]；研究目标：[[context/PROJECT_CONTEXT.md]]；工作路线：[[研究成果/〔研究路线〕论文研究路径/研究路径工作图.md]]。\n\n'+model['scope']+'。结构修订不代表样本、规则、有效性或论文结论已验证；旧正文与原稿锚点继续保留。\n\n## 章节总览\n\n```mermaid\n'+overview+'```\n\n| 当前章节 | 论证任务 | 结构状态 |\n|---|---|---|\n'+'\n'.join(summary)+'\n'
    if model.get('outline_focus'):body+='\n## 当前整理重点\n\n'+model['outline_focus']+'\n'
    if model.get('logic_chain'):body+='\n**全文逻辑：** '+model['logic_chain']+'。\n'
    body+='\n## 标题总览（二级与已展开的三级）\n\n'
    for index,c in enumerate([x for x in model['chapters'] if x['included']],1):
        body+='### 第'+str(index)+'章 '+c['title']+'\n\n'
        if c.get('argument_flow'):body+='**章内逻辑：** '+c['argument_flow']+'。\n\n'
        for j,sec in enumerate([x for x in c['sections'] if x['included']],1):
            body+='- '+link('论文章节/现行大纲.md',c['path']+'#'+sec['id'],f'{index}.{j} '+sec['title'])+'\n'
            for k,sub in enumerate([x for x in sec.get('subsections',[]) if x['included']],1):
                body+='  - '+link('论文章节/现行大纲.md',c['path']+'#'+sub['id'],f'{index}.{j}.{k} '+sub['title'])+'\n'
        if c.get('handoff'):body+='\n**向后接续：** '+c['handoff']+'。\n'
        body+='\n'
    body+='\n## 后续证据任务（不作为本轮标题梳理的完成门槛）\n\n'
    for index,c in enumerate([x for x in model['chapters'] if x['included']],1):
        body+='### 第'+str(index)+'章 '+c['title']+'\n\n'
        for j,sec in enumerate([x for x in c['sections'] if x['included']],1):
            body+='- **'+link('论文章节/现行大纲.md',c['path']+'#'+sec['id'],f'{index}.{j} '+sec['title'])+'**：'+sec['purpose']+'\n'
            body+='  - 所需证据：'+'；'.join(sec.get('evidence_required',['待补']))+'。\n'
    body+='\n## 调整方式\n\n在大纲结构中调整顺序即调整展示编号；稳定ID不变。`included: false`表示停用而非删除证据。章节路径保留历史编号；主题角色或成果类型改名须显式迁移并同步引用，生成器只检查、不自行移动。标题、论证任务、采用状态与证据要求均由同一主源生成。\n\n'+link('论文章节/现行大纲.md','项目管理/动态研究体系.md','设计与日常维护说明')+' · '+link('论文章节/现行大纲.md','项目管理/学术大纲与角色命名修订说明.md','本轮逐项修订及旧稿接续')+'。\n'
    if retired:body+='\n## 停用但保留的章节\n\n'+'\n'.join('- '+link('论文章节/现行大纲.md',p,t) for p,t in retired)+'\n'
    out['论文章节/现行大纲.md']=note('dynamic-outline','现行工作大纲',body)
    p='论文章节/README.md';s=read_fn(p);b='## 当前章节与角色入口\n\n'+link(p,'论文章节/现行大纲.md','现行工作大纲与结构图')+' · '+link(p,'研究成果/〔研究路线〕论文研究路径/研究路径工作图.md','研究路径与反馈图')+' · '+link(p,'主题研究/README.md','按研究角色查看主题')+'\n\n'
    for c in model['chapters']:
        if c['included']:b+='- '+link(p,c['path'],c['title'])+'\n'
    out[p]=artifacts.block(s,'dynamic-outline-index',b)
    p='主题研究/README.md';s=out.get(p,read_fn(p));b='## 按研究角色进入\n\n角色在各主题页维护；主角色用于展示前缀，辅助角色用于补充检索。不把角色等同于完成状态或章节归属。\n\n'
    b+='| 主角色 | 职责 | 主题入口 |\n|---|---|---|\n'
    for role in ROLES:
        matches=[link(p,t,'〔'+role+'〕'+topic_name(t)) for t,m in topics.items() if m['research_role']==role]
        b+='| '+role+' | '+ROLE_PURPOSE[role]+' | '+('、'.join(matches) or '当前无独立主角色主题；见下表的辅助角色')+' |\n'
    b+='\n| 主题 | 主角色 | 辅助角色 |\n|---|---|---|\n'
    for t,m in topics.items():b+='| '+link(p,t,topic_name(t))+' | '+m['research_role']+' | '+('、'.join(m['research_roles_secondary']) or '无')+' |\n'
    out[p]=artifacts.block(s,'research-role-index',b)
    p='研究成果/〔研究路线〕论文研究路径/研究路径工作图.md';g='flowchart TB\n'
    for n in route['nodes']:g+='  '+n['id']+'["'+label(n['title'])+'"]\n'
    for e in route['edges']:g+='  '+e['from']+(' -. "' if e['kind']=='feedback' else ' -->|"')+label(e['label'])+('" .-> ' if e['kind']=='feedback' else '"| ')+e['to']+'\n'
    body='**工作依赖图，不是已完成流程图。** 实线表示依赖，虚线表示反馈；合成试例不替代真实样本检验。\n\n维护源：[[研究成果/〔研究路线〕论文研究路径/研究路径结构.json]]；论文叙述结构见[[论文章节/现行大纲.md]]。\n\n```mermaid\n'+g+'```\n\n| 环节 | 相关主题 | 当前边界 |\n|---|---|---|\n'
    for n in route['nodes']:
        ts=[discovered[t]['path'] for t in n['topics']]
        body+='| '+n['title']+' | '+'、'.join(link(p,t,'〔'+topics[t]['research_role']+'〕'+topic_name(t)) for t in ts)+' | '+clean(n['status'])+' |\n'
    body+='\n## 图源职责\n\n本工作图由JSON生成，随研究依赖调整，不等于正文结构同步或研究完成。原[[研究成果/〔研究路线〕论文研究路径/研究路径图.drawio|draw.io图源]]及[[研究成果/〔研究路线〕论文研究路径/研究路径图.png|PNG]]保留为2026-10-20定位同步的阶段汇报快照；没有自动同步，不称为最新工作图。需要新的正式汇报图时，另行从已核对的工作主源更新draw.io并重新导出核验。\n'
    out[p]=thesis.route_view(route_source) if route_source.get('view_mode')==thesis.MODE else note('dynamic-research-path','研究路径工作图',body)
    active_subsections=sum(sub['included'] for c in model['chapters'] if c['included'] for sec in c['sections'] if sec['included'] for sub in sec.get('subsections',[]))
    return out,{'chapters':sum(c['included'] for c in model['chapters']),'sections':active_sections,'subsections':active_subsections,'adoptions':len(rows),'topics':len(topics),'roles':len(ROLES),'route_nodes':len(route['nodes']),'artifact_packages':arstats['packages'],'artifact_relations':arstats['relations']}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check',action='store_true');ap.add_argument('--output-dir',type=Path);ap.add_argument('--route-only',action='store_true',help='check or render only the deferred thesis-question skeleton');a=ap.parse_args()
    if not a.check and not a.output_dir:ap.error('choose --check or --output-dir')
    if a.output_dir and a.output_dir.resolve().is_relative_to(ROOT):ap.error('output must be outside Paper')
    cache={}
    def cached(p):
        if p not in cache:cache[p]=read(p) if (ROOT/p).exists() else ''
        return cache[p]
    if a.route_only:
        route=json.loads(cached(ROUTE));questions=thesis.validate(route)
        out={'研究成果/〔研究路线〕论文研究路径/研究路径工作图.md':thesis.route_view(route)}
        stats={'route_nodes':len(questions),'route_edges':len(route['edges']),'lower_links':0}
    else:
        out,stats=generate(cached)
    changed=[p for p,s in out.items() if s!=cached(p)]
    if a.output_dir:
        for p,s in out.items():
            f=a.output_dir/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
    print(json.dumps({**stats,'out_of_sync':changed},ensure_ascii=False,indent=2))
    if a.check and changed:raise SystemExit(1)
