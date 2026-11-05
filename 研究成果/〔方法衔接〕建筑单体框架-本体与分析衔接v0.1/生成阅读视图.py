"""从唯一维护源生成只读阅读视图及临时原生导图输入；不写原框架/模型。"""
import csv, hashlib, html, json, re
from pathlib import Path

BASE=Path(__file__).resolve().parent
VAULT=BASE.parent.parent
DATA=BASE/'衔接拆解.json'
MAPDIR=VAULT/'研究成果/〔讨论图示〕思维导图/建筑单体框架-本体与分析衔接v0.1'
def node(text,children=None,note=None,link=None):
 d={'text':text}
 if children:d['children']=children
 if note:d['note']=note
 if link:d['link']=link
 return d
def module(r):return r['original']['模块']
def j(v):return json.dumps(v,ensure_ascii=False)
def role_label(p):
 s=p['content'].split('；')[0].split('。')[0]
 return p['role']+'｜'+(s[:36]+'…' if len(s)>36 else s)
def lines(r):
 o=r['original']; t=r['ontology']; a=r['analysis']
 z=[f"## {r['id']} {o['研究内容']}", '',f"- **原模块／对象：**{o['模块']}／{o['分析对象']}",f"- **主要去向：**{r['destination']}；原采用建议：{o['采用建议']}（两轴独立）",f"- **拆分理由：**{r['rationale']}",'','### 按研究角色拆解','']
 z += [f"- **{p['role']}：**{p['content']}" for p in r['parts']]
 z += ['','### 本体与数据候选','',f"- 对象：{'；'.join(t['objects']) or '无新增领域对象'}",f"- 属性／记录字段：{'；'.join(t['attributes']) or '无新增字段'}",f"- 关系：{'；'.join(t['relations']) or '无新增领域关系'}",f"- 限制：{t['note']}",'','### 输入、操作与结果','']
 z += [f"- 输入 **{x['item']}**：{x['fields']}" for x in r['inputs']]
 if not r['derivations']:z+=['- 派生计算：本项不预设独立计算；观察、访谈或研究操作仍须保存依据。']
 for d in r['derivations']:
  z += [f"- **{d['name']}**：{d['rule']} 输出：{d['output']}。条件：{d['gate']}"]
 z += [f"- 分析／质量问题：{a['question']}",f"- 建议方法：{a['method']}",f"- 结果形式：{a['output']}",f"- 解释边界：{a['limit']}",'','### 原依据与迁移边界','',f"- 原操作：{o['建议操作与判据（研究者）']}",f"- 原所需资料：{o['所需资料']}",f"- 依据ID：{o['依据ID']}",f"- 原文定位：{o['原文定位']}",f"- 原证据状态：{o['来源证据状态']}",f"- 原迁移限制：{o['迁移限制']}",'- 本轮新增部分均为研究者衔接建议；复用既有证据记录，未新增原PDF逐页复核。','']
 return z

def main():
 data=json.loads(DATA.read_text()); rows=data['items']
 md=['# 建筑单体研究内容：按原顺序拆解','', '> 候选衔接稿，2026-10-23。按原CSV的A→B1…B8→C顺序，不改变原文依据与采用建议。对象、属性、关系均为候选表达，不是已部署字段。事实记录是有来源的记录，不等于现场确认。派生结果可以回写，但必须保留输入、方法及归属。','', '[使用说明](README.md) · [规则与重点示例](拆解规则与重点示例.md) · [原文献依据索引](../〔候选框架〕建筑单体研究内容框架v0.1/文献依据索引.md)','', '## 顺序导航','']
 for r in rows:
  md.append(f"- [{r['id']} {r['original']['研究内容']}](#{r['id'].lower()}-{r['original']['研究内容']})")
 md+=['']
 for r in rows:md+=lines(r)
 (BASE/'按顺序拆解.md').write_text('\n'.join(md))
 fields=['原序号','编号','模块','研究内容','主要去向','研究角色','拆分内容','对象候选','属性记录候选','关系候选','输入对应','派生规则','分析问题','方法','结果','解释边界','拆分理由']+list(rows[0]['original'])
 fields=list(dict.fromkeys(fields))
 with (BASE/'衔接总表.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for k,r in enumerate(rows,1):
   o=r['original']; t=r['ontology']; a=r['analysis']
   out=dict(o);out.update({'原序号':k,'主要去向':r['destination'],'研究角色':'；'.join(p['role'] for p in r['parts']),'拆分内容':j(r['parts']),'对象候选':'；'.join(t['objects']),'属性记录候选':'；'.join(t['attributes']),'关系候选':'；'.join(t['relations']),'输入对应':j(r['inputs']),'派生规则':j(r['derivations']),'分析问题':a['question'],'方法':a['method'],'结果':a['output'],'解释边界':a['limit'],'拆分理由':r['rationale']});w.writerow(out)
 analyses=['# 分析问题与数据依赖索引','','此表是逐条拆解的投影视图。A、C中的质量问题也保留，不能将所有行都计为风貌指标。自引用指本项基础记录；这张表不是可执行计算依赖图。C类通用操作的具体B项输入须在选题时明确。','', '| 编号 | 问题 | 输入条目及具体内容 | 结果 | 条件或边界 |','|---|---|---|---|---|']
 clean=lambda s:s.replace('|','／').replace('\n',' ')
 for r in rows:
  a=r['analysis'];analyses.append('| '+' | '.join(clean(s) for s in [r['id']+' '+r['original']['研究内容'],a['question'],'；'.join(x['item']+'：'+x['fields'] for x in r['inputs']),a['output'],a['limit']])+' |')
 (BASE/'分析问题与数据依赖.md').write_text('\n'.join(analyses)+'\n')
 batches=[('01-基础与整体空间',[r for r in rows if r['id'].startswith(('A','B1','B2','B3'))]),('02-体量构造与细部',[r for r in rows if r['id'].startswith(('B4','B5','B6'))]),('03-变化解释与分析步骤',[r for r in rows if r['id'].startswith(('B7','B8','C'))])]
 overview=[]; temp=Path('/tmp/paper-bridge-map-input');temp.mkdir(exist_ok=True)
 for name,rs in batches:
  groups={}
  for r in rs:
   children=[node(role_label(p),note=p['content']) for p in r['parts']]
   full='\n'.join(lines(r)); groups.setdefault(module(r),[]).append(node(r['id']+' '+r['original']['研究内容']+'【'+r['destination']+'】',children,note=full,link='研究成果/〔方法衔接〕建筑单体框架-本体与分析衔接v0.1/按顺序拆解.md#'+r['id'].lower()+'-'+r['original']['研究内容']))
  tree=node(name+'｜候选衔接', [node(m,v) for m,v in groups.items()],note='原采用建议不变；本轮拆解为研究者建议。查看条目备注可读输入、规则、证据和限制。')
  (temp/(name+'.json')).write_text(j(tree))
  overview.append(node(name,[node(m,[node(r['id']+' '+r['original']['研究内容']+'｜'+r['destination']) for r in rs if module(r)==m]) for m in groups],link='研究成果/〔讨论图示〕思维导图/建筑单体框架-本体与分析衔接v0.1/'+name+'.smm.md'))
 tree=node('建筑单体框架｜本体与分析衔接v0.1', [node('阅读规则',[node('原编号顺序保留；复合项拆分'),node('主要去向与原采用建议分开'),node('基础记录→派生判断→分析问题'),node('结果可回写；来源与规则必须保留'),node('全部为候选；未修改现有图谱模型')])]+overview,link='研究成果/〔方法衔接〕建筑单体框架-本体与分析衔接v0.1/README.md')
 (temp/'00-顺序总览.json').write_text(j(tree))
 print(j({'rows':len(rows),'map_inputs':str(temp),'batches':[{'name':n,'items':len(rs)} for n,rs in batches]}))
if __name__=='__main__':main()
