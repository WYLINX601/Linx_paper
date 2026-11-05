"""Recompute the synthetic case's numeric and semantic checks; never mutates its truth/input."""
import json, math, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'案例模型.json').read_text()); ns={n['id']:n for n in d['nodes']}; rels=d['relationships']
result={'scope':'单个合成案例的文件一致性、计算与5题推演核对；不代表真实样本验证','checks':[]}
def check(name,ok,detail):
    result['checks'].append({'name':name,'pass':bool(ok),'detail':detail})
check('节点ID唯一',len(ns)==len(d['nodes']),len(ns))
check('关系ID唯一',len({r['id'] for r in rels})==len(rels),len(rels))
check('关系端点存在',all(r['source'] in ns and r['target'] in ns for r in rels),len(rels))
check('关系类型均有基础定义',all(r['type'] in {v['type'] for v in d['relationVocabulary']} for r in rels),len(d['relationVocabulary']))
check('每条关系有有效证据',all(r.get('evidence') and all(e in ns and ns[e]['class']=='Evidence' for e in r['evidence']) for r in rels),'合成证据EV01—EV08')
check('材料标签字典一致',all(x in d['materialLabels'] for n in ns.values() for x in n['labels'] if x.startswith('材质_')),'木、砖、灰泥、陶瓦')
check('材料标签来源可追溯',all(n.get('labelEvidence',{}).get(x,{}).get('status')=='synthetic_assignment' for n in ns.values() for x in n['labels'] if x.startswith('材质_')),'全部来自EV01合成设定，非实测')
check('合成证据不冒充实测',all(n['properties']['isRealWorldEvidence'] is False for n in ns.values() if n['class']=='Evidence'),'8份同源合成记录')
access=[r for r in rels if r['type']=='DIRECT_ACCESS_TO']
def via_valid(r):
    i=ns[r['properties']['via']]
    ss={q['target'] for q in rels if q['type']=='INTERFACE_OF' and q['source']==i['id']}
    return i['properties']['passage']=='yes' and {r['source'],r['target']}==ss and r['properties']['bidirectional'] is True and bool(r['properties'].get('context'))
check('直接通行边有界面和情境',len(access)==5 and all(via_valid(r) for r in access),'5组双向关系；不将普通有向边自动视为双向')
check('窗不生成步行通道',not any(ns[r['properties']['via']]['properties']['kind']=='window_opening' for r in access),'I06—I10不属于步行通道')
check('开放分界无需实体墙',not any(r['type']=='REALIZED_IN' and r['source'] in ['I01','I04'] for r in rels),'I01堂屋—前廊、I04前廊—前院')
# Openings must lie on their host wall centerline and within its length.
def opening_on_host(r):
    g=ns[r['source']]['geometry'];w=ns[r['target']]['geometry'];a,b=w['a'],w['b']
    def on(q):
        cross=(q[0]-a[0])*(b[1]-a[1])-(q[1]-a[1])*(b[0]-a[0])
        dot=(q[0]-a[0])*(b[0]-a[0])+(q[1]-a[1])*(b[1]-a[1]);length2=math.dist(a,b)**2
        return abs(cross)<1e-8 and -1e-8<=dot<=length2+1e-8
    return on(g['a']) and on(g['b'])
check('门窗开口位于宿主墙',all(opening_on_host(r) for r in rels if r['type']=='REALIZED_IN'),'8处开口，2处无墙开放分界')
p=d['parameters'];slope=math.degrees(math.atan2(p['ridge_height_m']-p['wall_support_height_m'],p['depth_m']/2))
check('坡度计算可复现',abs(slope-d['analysisResults'][0]['value'])<0.0001,{'slopeDeg':slope})
run=p['depth_m']/2+p['roof_overhang_m'];rise=run*(p['ridge_height_m']-p['wall_support_height_m'])/(p['depth_m']/2)
area=2*(p['width_m']+2*p['roof_overhang_m'])*math.hypot(run,rise)
check('含挑檐屋面面积可复现',abs(area-d['analysisResults'][1]['value'])<0.0001,{'areaM2':area})
eave=p['wall_support_height_m']-p['roof_overhang_m']*math.tan(math.radians(slope))
check('檐口与承托线分开',abs(eave-ns['RF01']['geometry']['eaveZ'])<1e-8 and eave<3.6,{'actualEaveZ':eave,'wallAxisSupportZ':3.6})
centers={i:[sum(v)/2 for v in zip(ns[i]['geometry']['min'],ns[i]['geometry']['max'])] for i in ['S02','S03']}
check('方位距离按统一口径',abs(math.dist(centers['S02'],centers['S03'])-6.4)<1e-8 and centers['S03'][0]>centers['S02'][0] and centers['S03'][1]==centers['S02'][1],centers)
protocol=json.loads((ROOT/'验证/试验约定.json').read_text())
for f,key in [('合成真值.json','truth_sha256'),('遮蔽输入.json','input_sha256')]:
    actual=hashlib.sha256((ROOT/'验证'/f).read_bytes()).hexdigest();check('冻结文件未更改：'+f,actual==protocol[key],actual)
truth=json.loads((ROOT/'验证/合成真值.json').read_text()); pred=json.loads((ROOT/'验证/推演结果.json').read_text());a={x['id']:x for x in pred['answers']}
check('推演题目无缺漏',set(a)==set(truth),list(a))
err=abs(a['P1']['structuredValue']['slope_degrees']-truth['P1']['value'])
check('P1：几何推导',a['P1']['status']=='derived' and err<0.01,{'absoluteErrorDeg':err,'usedToolCalculation':True})
x=a['P2']['structuredValue'];check('P2：关系推导',a['P2']['status']=='derived' and x['from']=='S01' and x['to']=='S03' and x['interface']=='I03' and x['direction']=='双向' and bool(x['scenario']),x)
check('P3：有据标签提取',a['P3']['status']=='supported' and set(a['P3']['structuredValue']['labels'])==set(truth['P3']['value']),a['P3']['structuredValue']['labels'])
for id in ['P4','P5']:check(id+'：不足信息保留未知',a[id]['status']=='unknown' and bool(a[id]['verification_needed']),{'status':a[id]['status'],'notScoredAsIncorrectForAbstaining':True})
result['summary']={'passed':sum(c['pass'] for c in result['checks']),'total':len(result['checks']),'allPassed':all(c['pass'] for c in result['checks']),'blindPilot':{'questions':5,'deterministicDerivations':2,'evidenceExtraction':1,'underdeterminedAbstentions':2,'geometryAbsoluteErrorDeg':err,'interpretation':'本次仅检查一个明确给定信息的5题流程，不估计模型性能；通行题基本是规则展开，不是新建筑事实发现。'},'reviewLimit':'程序核对不代替图纸视觉检查、建筑专业审查或现场校验。'}
(ROOT/'验证/核对结果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result['summary'],ensure_ascii=False))
if not result['summary']['allPassed']:raise SystemExit(1)
