"""Read-only Paper Wiki checks. Reports go to an explicit workspace path.
No network, no auto-fixes, no credibility scores, no baseline refresh.
"""
from pathlib import Path
from collections import defaultdict,Counter,deque
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
import argparse,datetime,hashlib,json,os,posixpath,re,unicodedata
import yaml
VERSION='1.3'
class HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__();self.targets=[]
    def handle_starttag(self,tag,attrs):
        for name,value in attrs:
            if name in ('href','src') and value:self.targets.append((value,'html'))
EXCLUDE={'.obsidian','.git','.trash','.hermes-academic-backups','.openclaw','.langgraph_api','__pycache__'}
def role(p):
    if p.startswith('archive/'):return 'history'
    if '/审阅资料快照/' in p or p.startswith('研究资料/来源证据/2026-10-28-研究Wiki技能参考/') or '/历史配置/' in p:return 'snapshot'
    if p.endswith('.smm.md'):return 'native-map'
    return 'active'
def frontmatter(text):
    if not text.startswith('---\n'):return {}
    value=yaml.safe_load(text.split('---',2)[1])
    if not isinstance(value,dict):raise ValueError('frontmatter must be mapping')
    return value

def without_code(text):
    text=re.sub(r'^(`{3,}|~{3,})[^\n]*\n.*?^\1[^\n]*(?:\n|$)','',text,flags=re.M|re.S)
    return re.sub(r'`[^`\n]*`','',text)

def links(text):
    """Yield (target, kind). Preserve case and unicode; skip code examples."""
    text=without_code(text)
    for m in re.finditer(r'\[\[([^]\n]+)\]\]',text):yield m[1].split('|')[0],'wiki'
    for m in re.finditer(r'\]\(',text):
        i=m.end();start=i;depth=1;angle=False
        while i<len(text) and text[i]!='\n':
            c=text[i]
            if i==start and c=='<':angle=True
            if c=='>' and angle:angle=False
            if not angle:
                if c=='(':depth+=1
                elif c==')':
                    depth-=1
                    if not depth:break
            i+=1
        if depth:continue
        raw=text[start:i].strip()
        if raw.startswith('<') and '>' in raw:raw=raw[1:raw.index('>')]
        else:raw=re.sub(r'\s+[\"\'][^\n]*[\"\']$','',raw)
        if raw:yield raw,'markdown'
    # HTML href/src in Markdown notes.
    for m in re.finditer(r'(?:href|src)=[\"\']([^\"\']+)[\"\']',text):yield m[1],'html'

def slug(s):
    s=re.sub(r'<[^>]+>','',s).lower()
    s=re.sub(r'[^\w\s-]','',s,flags=re.U)
    return re.sub(r'\s+','-',s.strip())

def resolve(target,source,paths,kind='markdown'):
    target=unquote(target.replace('&amp;','&')).strip()
    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',target) or target.startswith('//'):return 'external',None,''
    path,sep,anchor=target.partition('#')
    if path.startswith('/'):return 'external-local',None,anchor
    path=path.split('?',1)[0]
    if not path:return 'ok',source,anchor
    candidates=[]
    rel=posixpath.normpath(posixpath.join(posixpath.dirname(source),path))
    def exists(p):
        return [p] if p in paths else ([p+'.md'] if p+'.md' in paths else [])
    if kind=='wiki':
        # Explicit root path first; relative paths can still be accepted.
        candidates=exists(path) or exists(rel)
        if not candidates:
            suffix='/'+path
            candidates=[p for p in paths if p.endswith(suffix) or p.endswith(suffix+'.md')]
    else:candidates=exists(rel)
    if not candidates and any(p.startswith(rel.rstrip('/')+'/') for p in paths):return 'directory',None,anchor
    if len(candidates)>1:return 'ambiguous',None,anchor
    return ('ok',candidates[0],anchor) if candidates else ('missing',None,anchor)

def scan(root,baseline=None):
    root=Path(root);paths=[];excluded=[]
    for base,dirs,files in os.walk(root,followlinks=False):
        for d in list(dirs):
            if d in EXCLUDE or (Path(base)/d).is_symlink():
                excluded.append(str((Path(base)/d).relative_to(root)));dirs.remove(d)
        for f in files:
            p=Path(base)/f
            if f=='.DS_Store' or f.endswith('.provenance.json') or p.is_symlink():continue
            paths.append(p.relative_to(root).as_posix())
    paths=set(paths);texts={};meta={};issues=[];edges=defaultdict(set);external=Counter();checked=Counter();ids=defaultdict(list)
    def issue(code,p,target,detail,severity='review'):
        issues.append({'code':code,'path':p,'target':target,'detail':detail,'severity':severity})
    for p in sorted(paths):
        if not p.endswith(('.md','.html','.json','.drawio')):continue
        if role(p) in ('snapshot','history'):continue
        try:texts[p]=(root/p).read_text(encoding='utf-8')
        except (UnicodeError,OSError) as e:issue('READ',p,'',str(e),'error');continue
        if p.endswith('.json'):
            try:json.loads(texts[p]);checked['json']+=1
            except Exception as e:issue('JSON',p,'',str(e),'error')
        if p.endswith('.drawio'):
            import xml.etree.ElementTree as ET
            try:ET.fromstring(texts[p]);checked['drawio_xml']+=1
            except Exception as e:issue('XML',p,'',str(e),'error')
        if p.endswith('.md') and not p.endswith('.smm.md'):
            try:meta[p]=frontmatter(texts[p])
            except Exception as e:issue('YAML',p,'',str(e),'error');continue
            if meta[p].get('wiki_id'):ids[meta[p]['wiki_id']].append(p)
            if meta[p].get('type') in ('research-topic','chapter-navigation','research-index','management','derived-index') and '/模板/' not in p:
                for field in ('wiki_id','type','status','summary'):
                    if not meta[p].get(field):issue('FIELD',p,field,'new Wiki page lacks required metadata','error')
    for uid,items in ids.items():
        if len(items)>1:issue('DUPLICATE_ID',items[0],uid,'; '.join(items),'error')
    for p,text in sorted(texts.items()):
        if not p.endswith(('.md','.html')):continue
        checked['link_documents']+=1
        items=list(links(text))
        if p.endswith('.smm.md'):checked['native_link_indexes']+=1
        raw_web=p.endswith('.html') and ('/sources/' in p or p.endswith('/官网原始页.html'))
        if p.endswith('.html'):
            # HTML sources have no Obsidian parser: raw Wiki syntax is not counted as usable HTML navigation.
            parser=HTMLLinks();parser.feed(text);items=parser.targets
        for target,kind in items:
            status,dst,anchor=resolve(target,p,paths,kind)
            checked['links']+=1
            if status in ('external','external-local'):external[status]+=1;continue
            if status=='directory':continue
            if status!='ok':
                issue('SOURCE_RESOURCE' if raw_web else 'LINK_'+status.upper(),p,target,'saved web snapshot is not a self-contained website' if raw_web else 'target absent or ambiguous','review' if raw_web else 'error');continue
            edges[p].add(dst)
            if anchor and dst.endswith('.md') and not dst.endswith('.smm.md'):
                t=texts.get(dst)
                if t is None:
                    try:t=(root/dst).read_text()
                    except Exception:continue
                headings=re.findall(r'^#{1,6}\s+(.+?)\s*#*$',without_code(t),re.M)
                valid={x for x in headings}|{slug(x) for x in headings}
                valid|={'^'+x for x in re.findall(r'\^([\w-]+)',t)}
                valid|=set(re.findall(r'(?:id|name)=[\"\']([^\"\']+)[\"\']',t))
                if anchor not in valid:issue('ANCHOR',p,target,'heading/block anchor needs review')
    for p,fm in meta.items():
        if fm.get('type')=='research-topic':
            for heading in ('问题与范围','当前认识与状态','依据与阶段成果','验证反例与待解决问题'):
                if heading not in texts[p]:issue('TOPIC_SECTION',p,heading,'missing research section','error')
            if not fm.get('depends_on'):issue('EVIDENCE_ENTRY',p,'','topic has no declared dependency','error')
        for dep in fm.get('depends_on',[]):
            if dep not in paths:issue('DEPENDENCY_MISSING',p,dep,'declared dependency absent','error');continue
            key=p+'::'+dep
            if baseline is None or key not in baseline:issue('BASELINE_UNKNOWN',p,dep,'no previous content baseline; no freshness claim','info')
            else:
                h=hashlib.sha256((root/dep).read_bytes()).hexdigest()
                if baseline[key]!=h:issue('DEPENDENCY_CHANGED',p,dep,'content changed since recorded baseline; semantic review required')
        if fm.get('type')=='chapter-navigation':
            for line in texts[p].splitlines():
                if re.match(r'^\| \d+\.\d+ ',line):
                    checked['chapter_sections']+=1
                    if '[[主题研究/' not in line and '主题研究/' not in unquote(line) and not re.search('待|缺口|不适用',line):issue('COVERAGE',p,line,'no topic or explicit gap','error')
    reachable=set();queue=deque(['README.md'])
    while queue:
        p=queue.popleft()
        if p in reachable:continue
        reachable.add(p);queue.extend(sorted(edges[p]-reachable))
    for p,fm in meta.items():
        if fm.get('type') in ('research-topic','chapter-navigation') and p not in reachable:issue('UNREACHABLE',p,'','not reachable from root entry','error')
    # Supersession loops are deterministic metadata faults; no automatic promotion.
    supersedes={p:f.get('superseded_by') for p,f in meta.items() if isinstance(f.get('superseded_by'),str)}
    for p in supersedes:
        seen=set();q=p
        while q in supersedes:
            if q in seen:issue('SUPERSESSION_CYCLE',p,q,'superseded_by cycle','error');break
            seen.add(q);q=supersedes[q]
    issues.sort(key=lambda x:(x['severity'],x['code'],x['path'],x['target']))
    return {'checker_version':VERSION,'file_count':len(paths),'checked':dict(checked),'excluded':sorted(excluded),'history_or_snapshots':sum(role(p) in ('history','snapshot') for p in paths),'external_not_fetched':dict(external),'counts':dict(Counter(x['severity'] for x in issues)),'issues':issues,'not_checked':['原论文证据支持充分性与作者结论复核','未声明的全部派生关系及历史导出同步状态','Zotero条目/附件实时可达性','Linux Neo4j连接、数据与查询结果','原生导图像素级排版（另行解析验证）','外部URL实时可用性','语义矛盾自动判定与研究有效性'],'reachable_pages':len(reachable)}

def adoption_view(root):
    root=Path(root);rows=[]
    outline=root/'论文章节/大纲结构.yaml'
    if outline.is_file():
        from research_structure import adoption_records,adoption_body
        model=yaml.safe_load(outline.read_text())
        from topic_artifact_views import discover_topics
        topics={v['path']:v['meta'] for v in discover_topics(lambda p:(root/p).read_text(),root).values()}
        rows=adoption_records(model)
        return rows,adoption_body(rows,topics)
    for p in sorted(root.glob('论文章节/*/章节导航.md')):
        for line in p.read_text().splitlines():
            if not re.match(r'^\| \d+\.\d+ ',line):continue
            cells=line[2:-2].split(' | ')
            if len(cells)!=4:raise ValueError('Unexpected adoption table: '+str(p))
            for m in re.finditer(r'\[\[(主题研究/[^]|]+)(?:\|[^]]+)?\]\]',cells[1]):
                rows.append({'chapter':p.relative_to(root).as_posix(),'section':cells[0],'topic':m[1],'status':cells[3]})
    body='---\nwiki_id: map-adoption\ntype: derived-index\nstatus: active\nsummary: 从章节采用表生成的反向入口\n---\n\n# 章节—主题反向入口\n\n本表机器生成，采用状态只在章节页维护。\n'
    for topic in sorted({x['topic'] for x in rows}):
        body+='\n## '+Path(topic).parent.name+'\n\n[['+topic+'|主题主源]]\n\n'
        for x in rows:
            if x['topic']==topic:body+='- [['+x['chapter']+'|'+x['section']+']]：'+x['status']+'。\n'
    return rows,body

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',required=True);ap.add_argument('--output',required=True);ap.add_argument('--baseline');ap.add_argument('--adoption-output');a=ap.parse_args()
    root=Path(a.root).resolve();out=Path(a.output).resolve()
    if out==root or root in out.parents:raise SystemExit('Report output must be outside the vault; publish through mac-paper.')
    b=json.loads(Path(a.baseline).read_text()) if a.baseline else None
    r=scan(root,b);r['run_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2))
    if a.adoption_output:
        target=Path(a.adoption_output).resolve()
        if root in target.parents or root==target:raise SystemExit('Adoption output must be outside vault')
        rows,body=adoption_view(root);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(rows,ensure_ascii=False,indent=2));target.with_suffix('.md').write_text(body)
    print(json.dumps({k:v for k,v in r.items() if k not in ('issues','excluded')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
