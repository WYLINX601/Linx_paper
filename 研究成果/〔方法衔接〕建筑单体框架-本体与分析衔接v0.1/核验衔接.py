"""内容完整性与输出一致性检查；不替代建筑学语义审核。"""
import csv,hashlib,json,re,subprocess,importlib.util,html
from collections import Counter
from pathlib import Path
BASE=Path(__file__).resolve().parent;VAULT=BASE.parent.parent
def plain(s):
 return html.unescape(re.sub(r"<[^>]*>","",s))
def main():
 d=json.loads((BASE/'衔接拆解.json').read_text());rs=d['items'];ids=[r['id'] for r in rs];errors=[]
 source=VAULT/d['source'];orig=list(csv.DictReader(source.open(encoding='utf-8-sig')))
 def check(ok,msg):
  if not ok:errors.append(msg)
 check(ids==[r['编号'] for r in orig],'原始编号/顺序不一致')
 check(len(ids)==100 and len(set(ids))==100,'数量/唯一性')
 check(hashlib.sha256(source.read_bytes()).hexdigest()==d['sourceSha256'],'源CSV指纹')
 for r,o in zip(rs,orig):
  check(r['original']==o,r['id']+' 原行改变')
  check(r['destination'] in ['本体与数据为主','分析为主','兼有','研究与证据规则'],r['id']+' 去向')
  check(bool(r['parts']),r['id']+' 未拆分')
  for p in r['parts']:check(p['role'] in d['roles'] and bool(p['content']),r['id']+' 角色')
  for x in r['inputs']:check(x['item'] in ids and bool(x['fields']),r['id']+' 输入不存在')
  for x in r['derivations']:check(all(x.get(k) for k in ['name','rule','output','gate']),r['id']+' 派生规则缺项')
  check(all(r['analysis'].get(k) for k in ['question','method','output','limit']),r['id']+' 分析缺项')
  check(all(k in r['ontology'] for k in ['objects','attributes','relations','note']),r['id']+' 候选表达缺项')
  check(bool(r['rationale']),r['id']+' 无拆分理由')
 csvrows=list(csv.DictReader((BASE/'衔接总表.csv').open(encoding='utf-8-sig')))
 check([x['编号'] for x in csvrows]==ids,'CSV顺序')
 for r,c in zip(rs,csvrows):
  check(all(c[k]==v for k,v in r['original'].items()),r['id']+' CSV原字段')
  check(json.loads(c['拆分内容'])==r['parts'],r['id']+' CSV拆分')
  check(json.loads(c['输入对应'])==r['inputs'],r['id']+' CSV输入')
  check(json.loads(c['派生规则'])==r['derivations'],r['id']+' CSV派生')
 md=(BASE/'按顺序拆解.md').read_text();seen=re.findall(r'^## ((?:A|C)\d{2}|B\d{3}) ',md,re.M)
 check(seen==ids,'Markdown顺序/覆盖')
 # 确认核心内容实际进入视图，不仅编号出现
 for r in rs:
  for p in r['parts']:check(p['content'] in md,r['id']+' Markdown内容')
  check(r['original']['依据ID'] in md,r['id']+' Markdown证据')
 baseline=json.loads((BASE/'原文件指纹.json').read_text());changed=[]
 for s,h in baseline.items():
  p=VAULT/s
  if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:changed.append(s)
 # 指纹差异独立报告，不能据内容通过宣称原文件字节不变。
 maps=[]
 spec=importlib.util.spec_from_file_location('bridge_view',BASE/'生成阅读视图.py');view=importlib.util.module_from_spec(spec);spec.loader.exec_module(view)
 mapdir=VAULT/'研究成果/〔讨论图示〕思维导图/建筑单体框架-本体与分析衔接v0.1'
 for p in sorted(mapdir.glob('*.smm.md')):
  cp=subprocess.run(['node','/Users/wangyuelin/.codex/skills/obsidian-mindmap/scripts/mindmap.cjs','validate','--file',str(p),'--summary'],capture_output=True,text=True)
  v=json.loads(cp.stdout);check(cp.returncode==0 and v.get('ok') is True,p.name+' 导图解析失败')
  text=p.read_text().split('# textdata',1)[1]
  got=re.findall(r'^((?:A|C)\d{2}|B\d{3}) ',text,re.M)
  expected=ids if p.name.startswith('00') else [r['id'] for r in rs if (p.name.startswith('01') and r['id'].startswith(('A','B1','B2','B3'))) or (p.name.startswith('02') and r['id'].startswith(('B4','B5','B6'))) or (p.name.startswith('03') and r['id'].startswith(('B7','B8','C')))]
  check(got==expected,p.name+' 导图编号顺序')
  if not p.name.startswith('00'):
   ip=subprocess.run(['node','/Users/wangyuelin/.codex/skills/obsidian-mindmap/scripts/mindmap.cjs','inspect','--file',str(p),'--json'],capture_output=True,text=True,check=True)
   native=json.loads(ip.stdout)['payload']['root'];nodes=[]
   def collect(n):
    nodes.append(n)
    for c in n.get('children',[]):collect(c)
   collect(native)
   for r in rs:
    if r['id'] not in expected:continue
    ns=[n for n in nodes if plain(n['data']['text']).startswith(r['id']+' ')]
    check(len(ns)==1,r['id']+' 导图项唯一')
    if ns:
     check(ns[0]['data'].get('note')=='\n'.join(view.lines(r)),r['id']+' 导图完整备注未同步')
     check([plain(n['data']['text']) for n in ns[0].get('children',[])]==[view.role_label(x) for x in r['parts']],r['id']+' 导图角色未同步')
     check([n['data'].get('note') for n in ns[0].get('children',[])]==[x['content'] for x in r['parts']],r['id']+' 导图角色完整备注未同步')
  maps.append({'file':str(p.relative_to(VAULT)),'items':len(got),'validation':v})
 check(len(maps)==4,'应有四张导图')
 # 检查新增手写说明和生成阅读文件的本地文件链接（锚点由阅读器解释）
 for p in BASE.glob('*.md'):
  for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' in target or target.startswith('#'):continue
   target=target.strip('<>').split('#')[0]
   check((p.parent/target).exists(),p.name+' 链接不存在:'+target)
 result={'date':'2026-10-23','ok':not errors,'errors':errors,'originalItems':len(orig),'decomposedItems':len(rs),'roleParts':sum(len(r['parts']) for r in rs),'destinations':dict(Counter(r['destination'] for r in rs)),'originalEvidenceReferences':sum(len(r['original']['依据ID'].split(';')) for r in rs),'uniqueEvidenceIds':len({e for r in rs for e in r['original']['依据ID'].split(';')}),'protectedFileCount':len(baseline),'changedProtectedFiles':changed,'protectedBytesUnchanged':not changed,'warnings':(['保护范围内存在文件指纹变化；原基线保留，原因与内容核查见主会话修订与验收.md；ok仅表示本轮交付内容检查通过'] if changed else []),'mapChecks':maps,'limits':['无新增PDF原文复核','无实样试采或统计复算','无正式本体部署或Neo4j写入','导图通过文件/插件解析核验，不是GUI像素验收','文件检查不替代独立语义审核；输入表不是计算DAG']}
 (BASE/'文件核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in result.items() if k!='mapChecks'},ensure_ascii=False))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
