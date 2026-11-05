"""Render current CMS source to a scratch directory; never writes Paper.
Run: python generate_views.py --out ABSOLUTE_SCRATCH_DIRECTORY
Publish selected outputs only via mac-paper with current expected hashes.
"""
import argparse,json,pathlib,subprocess
BASE='研究成果/〔案例拆解〕敕木山村资料与对象拆解'
VIL='研究资料/村落资料/敕木山'
BRIDGE='/Users/wangyuelin/.hermes/profiles/academic/bin/mac-paper'
def read(path):
    r=json.loads(subprocess.check_output([BRIDGE,'read',path],text=True))
    if not r.get('ok'):raise RuntimeError(r)
    return json.loads(r['result']['text']),r['result']['sha256']
def text(v):
    if isinstance(v,dict):return '；'.join(k+'：'+text(x) for k,x in v.items())
    if isinstance(v,list):return '；'.join(text(x) for x in v)
    return str(v)
def clean(v):return text(v).replace('|','／').replace('\n','<br>')
def render(d,old):
    lines=['# 敕木山村资料与对象拆解','','> 派生视图；唯一维护源：拆解主源.json。不是建筑名录、真实图谱或当前现场核实。', '', '## 覆盖与计数','',text(d['statistics']), '',text(d['corpus_boundary']), '', '## 对象与模式主表','','|编号/对象|当前处理|候选表达|依据|查证条件|','|---|---|---|---|---|']
    for o in d['objects']:lines.append('|'+ '|'.join(map(clean,[o['id']+' '+o['name'],o['decision'],o['model_role'],o['basis'],o['check']]))+'|')
    lines+=['','## 关系候选','']
    for r in d['relations']:lines.append('- '+r['id']+'：'+r['from']+' → '+r.get('to',r.get('to_text',''))+'；'+r['meaning']+'；'+text(r['basis'])+'；'+r['status'])
    lines+=['','## 冲突与待核','']
    for q in d['issues']:lines+=['### '+q['id']+' '+q['question'],'',q['current']+' 依据：'+text(q['evidence'])+'。查证：'+q['next'],'']
    lines+=['## BOT对照与表达','']
    for k in d['model_preparation']:lines.append('- '+k['id']+' '+k['rule']+' 依据：'+k['basis']+'。状态：'+k['status'])
    panels=[]
    for p in d['papers']:
        lines+=['','## '+p['key']+' '+p['title'],'',text(p['authors'])+'；'+str(p['year'])+'；附件 '+p['attachment'], '', '**贡献：** '+text(p['contribution']),'','**方法：** '+text(p['method']), '', '**范围/局限：** '+text(p['scope'])+'；'+text(p['limitations']), '', '**阅读覆盖：** '+text(p['pages_read'])+'；'+text(p['visual_pages']),'','|材料/定位|范围|陈述/用途|边界|','|---|---|---|---|']
        entries=[]
        for m in p['materials']:
            cs=[c for c in p['claims'] if c['material_id']==m['id']]
            body='；'.join(c['text']+'〔'+c['attribution']+'〕；用途：'+c['knowledge_use'] for c in cs) or '图表编目，不自动生成实例事实。'
            lines.append('|'+ '|'.join(map(clean,[m['id']+' '+m['title']+'；'+m['locator'],m['scope'],body,m['boundary']]))+'|')
            entries.append({'id':m['id'],'title':m['title'],'text':m['locator']+'\n'+(body if cs else text(m['scope']))+'\n边界：'+m['boundary'],'link':m['source_link'],'asset':m.get('asset')})
        panels.append({'id':p['key'],'title':text(p['authors'])+' '+str(p['year'])+'｜'+p['title'],'intro':text(p['scope'])+'\n'+p.get('reading_status',''),'entries':entries})
    entries=[]
    lines+=['','## 既有资料接续','','[旧资料主索引](../../'+VIL+'/资料索引.md)；只引用，不在此维护第二份事实。','']
    for r in old['records']:
        orig=r.get('original_local_path','');asset=None
        if orig.lower().endswith(('.jpg','.png')) and '/Paper/' in orig:asset=orig.split('/Paper/',1)[1]
        if not asset or r['id'] in ['CMS-M006','CMS-M007']:asset=next((VIL+'/'+f for f in r['local_copy_paths'] if f.lower().endswith(('.jpg','.png'))),None)
        body=r['title']+'\n'+r['source_title']+'\n'+r['original_locator']+'\n'+r['correspondence']+'；'+r['pending']
        entries.append({'id':r['id'],'title':r['title'],'text':body,'link':'[['+VIL+'/资料索引.md]]','asset':asset})
        lines.append('- '+r['id']+' '+r['title']+'；'+r['correspondence']+'；'+r['pending'])
    panels.append({'id':'LEGACY','title':'既有资料逐项接续｜CMS-M001—M032','intro':'旧索引单源维护；核查履历不升级为本轮重验。','entries':entries})
    lines+=['','## 审核履历','',text(d['review'])]
    return '\n'.join(lines)+'\n',{'target':BASE+'/素材与对象审核图.excalidraw.md','objects':d['objects'],'issues':d['issues'],'panels':panels,'statistics':d['statistics']}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);a=parser.parse_args()
    out=pathlib.Path(a.out).resolve()
    if pathlib.Path('/Users/wangyuelin/Desktop/Obsidian/Paper') in out.parents:raise ValueError('Output must be outside Paper')
    out.mkdir(parents=True,exist_ok=True)
    d,sha=read(BASE+'/拆解主源.json');old,oldsha=read(VIL+'/资料索引.json')
    md,atlas=render(d,old)
    (out/'拆解主表.md').write_text(md)
    (out/'atlas-input.json').write_text(json.dumps(atlas,ensure_ascii=False,indent=2))
    (out/'来源版本.json').write_text(json.dumps({'main':sha,'legacy':oldsha},ensure_ascii=False,indent=2))
    print(json.dumps({'out':str(out),'panels':len(atlas['panels']),'source_sha256':sha},ensure_ascii=False))
