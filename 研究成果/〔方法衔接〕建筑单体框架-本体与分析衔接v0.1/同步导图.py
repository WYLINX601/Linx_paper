"""将重新生成的临时树与现有导图局部同步；UID保留、指纹锁、工具自动备份。"""
import json,re,subprocess,html
from pathlib import Path
BASE=Path(__file__).resolve().parent;VAULT=BASE.parent.parent
TOOL='/Users/wangyuelin/.codex/skills/obsidian-mindmap/scripts/mindmap.cjs'
def plain(text):
 return html.unescape(re.sub(r"<[^>]*>","",text))
def key(text):
 text=plain(text)
 m=re.match(r'^((?:A|C)\d{2}|B\d{3}) ',text)
 if m:return m.group(1)
 return text.split('｜',1)[0]
def main():
 receipts=[]
 for p in sorted(Path('/tmp/paper-bridge-map-input').glob('*.json')):
  target=VAULT/'研究成果/〔讨论图示〕思维导图/建筑单体框架-本体与分析衔接v0.1'/f'{p.stem}.smm.md'
  cp=subprocess.run(['node',TOOL,'inspect','--file',str(target),'--json'],capture_output=True,text=True,check=True)
  old=json.loads(cp.stdout);new=json.loads(p.read_text());ops=[]
  def walk(a,b):
   da=a['data'];changes={}
   for name in ['text','note']:
    before=plain(da.get(name,'')) if name=='text' else da.get(name,'')
    if before!=b.get(name,''):
     val=b.get(name,'')
     changes[name]=('<p>'+html.escape(val)+'</p>') if name=='text' and da.get('richText') else val
   if changes:ops.append({'op':'update','target':{'uid':da['uid']},'set':changes})
   ac=a.get('children',[]);bc=b.get('children',[]);am={key(x['data']['text']):x for x in ac}
   assert len(am)==len(ac),'同级键重复，停止自动同步'
   wanted={key(x['text']) for x in bc}
   for x in ac:
    if key(x['data']['text']) not in wanted:ops.append({'op':'delete','target':{'uid':x['data']['uid']}})
   for i,x in enumerate(bc):
    prior=am.get(key(x['text']))
    if prior:walk(prior,x)
    else:ops.append({'op':'add','parent':{'uid':da['uid']},'index':i,'node':x})
  walk(old['payload']['root'],new)
  if not ops:continue
  f=Path('/tmp')/(p.stem+'-bridge-ops.json');f.write_text(json.dumps(ops,ensure_ascii=False))
  cp=subprocess.run(['node',TOOL,'edit','--file',str(target),'--input',str(f),'--expect-sha256',old['sha256'],'--backup-dir','/tmp/paper-bridge-map-backups','--summary'],capture_output=True,text=True)
  v=json.loads(cp.stdout)
  if cp.returncode or not v.get('ok'):raise RuntimeError(cp.stdout+cp.stderr)
  receipts.append({'file':str(target.relative_to(VAULT)),'operations':len(ops),'result':v})
  print(p.stem,len(ops),'ok')
 (BASE/'导图修订记录.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
