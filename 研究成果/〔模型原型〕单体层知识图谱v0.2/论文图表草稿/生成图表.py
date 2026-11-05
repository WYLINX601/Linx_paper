"""从现有 v0.2 数据生成解释性图表，不修改图谱或增加建筑事实。"""
from pathlib import Path
import base64, hashlib, html, json, re, shutil, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
P = OUT.parent
def read(name): return json.loads((P / name).read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name, value): (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
M, G, D, B = [read(n) for n in ['模型定义.json','案例图谱.json','空间关系演示.json','优化依据.json']]
CL = {x['id']: x['label'] for x in M['classes']}
RR = {x['id']: x for x in M['relations']}
GG = {x['id']: x for x in G['nodes']}
AA = {x['id']: x for x in G['assertions']}
DA = {x['id']: x for x in D['assertions']}
EE = {x['id']: x for x in B['evidence']}
SS = {x['id']: x for x in B['sources']}
PALETTE = {'blue':('#dae8fc','#6c8ebf'),'green':('#d5e8d4','#82b366'),'yellow':('#fff2cc','#d6b656'),'orange':('#ffe6cc','#d79b00'),'purple':('#e1d5e7','#9673a6'),'grey':('#f5f5f5','#666666')}

class Figure:
    def __init__(self, stem, title, subtitle, w=1740, h=1000):
        self.stem, self.w, self.h, self.refs = stem,w,h,[]
        self.file=ET.Element('mxfile',host='drawio',version='32.4.1')
        dg=ET.SubElement(self.file,'diagram',name=title,id=stem[:2])
        mod=ET.SubElement(dg,'mxGraphModel',dx=str(w),dy=str(h),grid='1',gridSize='10',page='1',pageScale='1',pageWidth=str(w),pageHeight=str(h),background='#ffffff')
        self.root=ET.SubElement(mod,'root')
        ET.SubElement(self.root,'mxCell',id='0'); ET.SubElement(self.root,'mxCell',id='1',parent='0')
        self.i=1
        self.box('',0,0,w,h,style='fillColor=#ffffff;strokeColor=none;',raw=True)
        self.text(title,40,24,w-80,48,size=30,bold=True)
        self.text(subtitle,40,80,w-80,46,size=17)
    def ident(self): self.i+=1; return str(self.i)
    def box(self,text,x,y,w,h,color='blue',size=19,style='',raw=False):
        i=self.ident();fill,stroke=PALETTE[color]
        base=f'rounded=1;arcSize=8;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize={size};fontColor=#172b4d;spacing=14;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;'
        c=ET.SubElement(self.root,'mxCell',id=i,value=text if raw else html.escape(text).replace('\n','<br>'),style=base+style,vertex='1',parent='1')
        ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
        return i
    def text(self,text,x,y,w,h,size=18,bold=False):
        return self.box(text,x,y,w,h,size=size,style='fillColor=none;strokeColor=none;align=left;spacing=0;'+('fontStyle=1;' if bold else ''))
    def edge(self,a,b,label='',start=(1,.5),end=(0,.5),points=(),dashed=False,both=False,arrow=True):
        i=self.ident()
        style=f'edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;fontFamily=PingFang SC;fontSize=17;strokeColor=#52677f;fontColor=#172b4d;strokeWidth=1.8;labelBackgroundColor=#ffffff;endArrow={"block" if arrow else "none"};endFill=1;exitX={start[0]};exitY={start[1]};entryX={end[0]};entryY={end[1]};'
        if dashed: style+='dashed=1;'
        if both: style+='startArrow=block;startFill=1;'
        c=ET.SubElement(self.root,'mxCell',id=i,value=html.escape(label).replace('\n','<br>'),style=style,edge='1',parent='1',source=a,target=b)
        g=ET.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
        if points:
            ar=ET.SubElement(g,'Array',attrib={'as':'points'})
            for x,y in points:ET.SubElement(ar,'mxPoint',x=str(x),y=str(y))
        self.refs.append((a,b));return i
    def image(self,path,x,y,w,h):
        data=base64.b64encode(path.read_bytes()).decode()
        return self.box('',x,y,w,h,style=f'shape=image;imageAspect=0;image=data:image/png,{data};strokeColor=none;')
    def save(self):
        ids={x.get('id') for x in self.root}
        assert all(a in ids and b in ids for a,b in self.refs)
        ET.indent(self.file)
        ET.ElementTree(self.file).write(OUT/(self.stem+'.drawio'),encoding='utf-8',xml_declaration=True)

# 图1：状态明确的构建过程。虚线框表示待做工作，箭头表示工作流程，不是本体关系。
f=Figure('01-模型构建过程','图1  单体层语义模型的构建过程','流程与状态整理｜研究者综合设计；文献依据与具体建筑证据分别进入模型和实例',1740,860)
texts=[('研究问题','描述空间组织、实体构成\n与类型特征\n明确单体研究边界'),('文献与资料','类型学、形态学研究\nBOT、室内空间语义模型\n知识图谱方法与案例资料'),('定义表达规则','11类概念、30项特征\n18种关系及其成立条件\n保存依据与适用范围'),('实例编码','文献：14节点／27条断言\n合成：7节点／28条断言\n两类数据分别保存')]
ids=[]
for j,(title,body) in enumerate(texts):
    ids.append(f.box(title+'\n\n'+body,50+j*420,180,330,190,color='blue',size=21))
for a,b in zip(ids,ids[1:]): f.edge(a,b)
a=f.box('表达一致性检查\n\n标识、来源、关系约束\n分类复算、查询、防错场景\n程序检验不等于实地验证',1310,510,330,190,'green',21)
b=f.box('原文与独立审查\n\n已有关键原页抽核\n已有模型独立验收\n本轮另核图表与数据对应',890,510,330,190,'green',21)
c=f.box('论文表达草稿\n\n概念图、关系定义表\n实例编码图、查询结果表\n每项保留数据与参考来源',470,510,330,190,'purple',21)
d=f.box('后续真实案例验证\n\n身份明确的住宅平剖面\n现场空间与构件判定\n实测资料、样本比较',50,510,330,190,'grey',21,style='dashed=1;')
f.edge(ids[-1],a,start=(.5,1),end=(.5,0))
f.edge(a,b,start=(0,.5),end=(1,.5)); f.edge(b,c,start=(0,.5),end=(1,.5));f.edge(c,d,start=(0,.5),end=(1,.5),dashed=True)
f.text('依据：模型定义.json、优化依据.json、案例图谱.json、空间关系演示.json、既有独立验收记录。虚线框为后续工作。',50,760,1640,45,17)
f.save()

# 图2：有意只画核心关系，不把所有类和属性强行放入一张图。
f=Figure('02-核心概念关系','图2  核心概念及关系','模型层节选｜节点表示概念类，连线表示允许表达的关系；不是具体住宅的事实图',1740,1200)
d=f.box('民居研究单元\nDwelling',690,170,330,100,'blue',24)
s=f.box('空间\nSpace',230,430,330,100,'green',24)
e=f.box('建筑实体部分\nElement',1160,430,330,100,'orange',24)
i=f.box('界面\nInterface',690,700,330,100,'purple',24)
f.edge(d,s,'包含空间\nhas_space',start=(.15,1),end=(.5,0),points=[(740,340),(395,340)])
f.edge(d,e,'包含实体部分\nhas_element',start=(.85,1),end=(.5,0),points=[(970,340),(1325,340)])
f.edge(e,s,'围合或界定  bounds',start=(0,.5),end=(1,.5))
f.edge(i,s,'界面关联对象\ninterface_of',start=(0,.5),end=(.5,1),points=[(395,750)])
f.edge(i,e,'可选：涉及实体\nrealized_by',start=(1,.5),end=(.5,1),points=[(1325,750)],dashed=True)
f.box('空间之间\n邻接 adjacent_to\n直接通行 direct_access_to\n范围相交 intersects_space',40,850,470,150,'grey',20)
f.box('实体部分之间\n组成 has_element\n支承 supports\n（方向从承托者到被承托者）',1230,850,470,150,'grey',20)
f.text('注：Interface也可通过interface_of关联Element；此图仅选一条实体关联路径以保持可读性。直接通行须另记via界面与通行情境。',50,1030,1640,60,18)
f.text('另有资料、地点、分类体系与类型概念，以及变化、几何、分析扩展类。完整范围见关系表。依据：模型定义.json；BOT01–03、ISM01–04。',50,1110,1640,50,17)
f.save()

# 图3：原页完整嵌入并叠加定位框；没有补绘住宅平面、空间轮廓或侧样几何。
f=Figure('03-文献实例编码','图3  周湖8号：从文献记录到实例编码','文献实例｜原文表格 → 对象与特征 → 分类及证据；源内身份，不代表2026年现状',1800,1160)
f.text('A  原文与定位',40,145,490,40,24,True)
f.text('B  编码对象与特征',600,145,550,40,24,True)
f.text('C  分类判断与追溯',1230,145,520,40,24,True)
source_img=P/'../单体层知识图谱v0.1/证据图页/ZWDJJE99-PDF55.png'
f.image(source_img,40,200,490,693)
# 原图893×1263；第8行约 y=753。定位框为图表标注，不改变原图。
f.box('',109,606,364,17,'orange',style='fillColor=none;strokeColor=#d79b00;strokeWidth=2;rounded=0;')
f.box('原表第8行\n院墙不承重｜后厨“一”字形天井\n五柱五筒｜屋面不分层\nPDF55／印刷44，表3.7',40,925,490,150,'yellow',20)
dw=f.box(GG['D_8']['label']+'\nD_8 · 民居研究单元\n身份仅在该文献内部成立',600,210,540,110,'blue',21)
rep=f.box(GG['R_8']['label']+'\nR_8 · 图纸或调查记录',600,425,540,100,'green',22)
f.edge(dw,rep,'由图纸或记录表述｜REP_8',start=(.5,1),end=(.5,0))
f.box('记录附带的四项特征（不是四个实体）\n\n后院院墙：不承重\n后厨天井：一字形\n侧样柱筒：五柱五筒\n侧样屋面：不分层',600,585,540,240,'green',23)
f.text('F_8_load_bearing／F_8_rear_courtyard_form\nF_8_column_bay_form／F_8_roof_layered\n全部回指 E_Z8；四项描述范围分别保留。',600,850,540,90,17)
f.box('五柱五筒\nT_55 · 类型概念\n归于 SC_COLUMN 分类体系',1230,425,520,100,'purple',21)
# 此边来自CLASS_8的肯定判断，是分类记录的展示投影，不是原断言裸边。
f.edge(rep,str(f.i),'类型匹配\nCLASS_8',start=(1,.5),end=(0,.5))
f.box('原型四项条件试判｜PROTO_8\n\n院墙、天井、屋面三项满足\n柱筒：五柱五筒 ≠ 五柱四筒\n结论：四项合取条件不全部匹配',1230,585,520,240,'yellow',22)
f.box('证据与判断分开保存\n事实：E_Z8 → 学位论文表3.7\n判据：E_PROTOTYPE → 2023论文PDF5\n分类：读者按判据作出的比较',1230,875,520,160,'grey',20)
f.text('图注：左侧原页仅增加第8行定位框；中部四项值来自原表，未从图像自动识别。CLASS_8与PROTO_8为既有分类记录。',40,1090,1710,30,17)
f.text('限制：未确认完整平面、通行或构件分段；原型不匹配不等于无历史关联。出处：赵潇诺学位论文及2023侧样论文，详见图表来源记录。',40,1125,1710,28,17)
f.save()

# 图4：从合成数据投影概念性区域示意；布局不作为坐标/比例/朝向/墙体证据。
f=Figure('04-空间关系编码演示','图4  堂屋—前廊：空间与界面的编码','合成演示｜synthetic_demo｜不是周湖8号平面；不具有尺寸、朝向或建筑实测依据',1800,1060)
f.text('A  区域关系示意（无比例）',40,145,480,40,24,True)
f.text('B  对应实例子图',630,145,510,40,24,True)
f.text('C  通行关系的关键字段',1260,145,500,40,24,True)
f.box('堂屋\nS_HALL',100,250,400,210,'green',27,style='rounded=0;strokeColor=none;')
f.box('前廊\nS_VERANDA\n半开放；交通与停留',100,460,400,190,'green',25,style='rounded=0;strokeColor=none;fillColor=#eef6ec;')
f.box('',100,458,400,4,'purple',style='rounded=0;fillColor=none;dashed=1;strokeWidth=3;')
f.text('I_OPEN：语义分界／无实体隔断',55,700,520,60,22,True)
f.text('色块外缘仅为示意范围，不表示墙体。\n两块区域的形状、大小与上下布局\n都是图示安排，不是测量结果。',55,790,520,100,20)
hall=f.box('堂屋 S_HALL\nSpace',650,250,480,90,'green',24)
ver=f.box('前廊 S_VERANDA\nSpace',650,620,480,90,'green',24)
it=f.box('开放分界 I_OPEN\nInterface',650,435,480,90,'purple',24)
f.edge(it,hall,'interface_of',start=(.5,0),end=(.5,1))
f.edge(it,ver,'interface_of',start=(.5,1),end=(.5,0))
f.edge(hall,ver,'邻接\nADJ_HV',start=(0,.5),end=(0,.5),points=[(600,295),(600,665)],arrow=False)
f.edge(hall,ver,'通行\nACCESS_HV\nACCESS_VH',start=(1,.5),end=(1,.5),points=[(1190,295),(1190,665)],both=True)
f.text('邻接线无方向；右侧双箭头合并显示两条\n有向通行断言。两条通行均限定 via=I_OPEN。',640,770,560,80,19)
f.box('ACCESS_HV\n\n起点：S_HALL 堂屋\n关系：direct_access_to\n终点：S_VERANDA 前廊\n经过界面：I_OPEN\n使用者：可独立行走的成人\n方式：普通步行\n时段：演示正常使用时段',1260,250,500,410,'blue',22,style='align=left;')
f.box('实例依据：E_DEMO\n人工设定的教学场景\n\n模型依据：BOT03、ISM03\n文献支持表达方法，\n不证明此场景是实际住宅。',1260,710,500,220,'yellow',22)
f.text('图注：区域、界面、邻接与通行均对应空间关系演示.json中的既有ID；仅展示堂屋—前廊子图，省略其他演示对象。',40,970,1710,35,17)
f.text('“无实体隔断”是界面特征；“半开放”是空间特征；“可直接通行”是带情境的空间关系。不能仅由邻接或开放自动推断通行。',40,1010,1710,30,17)
f.save()

# 复算在隔离临时副本中进行，原验证文件与图谱均保持原样。
with tempfile.TemporaryDirectory(prefix='kg-figure-check-') as td:
    temp=Path(td)/'outputs';temp.mkdir()
    shutil.copytree(P.parent/'单体层知识图谱v0.1',temp/'单体层知识图谱v0.1')
    target=temp/P.name;target.mkdir()
    for x in P.iterdir():
        if x.is_file(): shutil.copy2(x,target/x.name)
    run=subprocess.run([sys.executable,str(target/'检查图谱.py')],capture_output=True,text=True)
    if run.returncode: raise RuntimeError(run.stdout+run.stderr)
    V=json.loads((target/'验证结果.json').read_text())
    dump('复算验证结果.json',V)

# 关系表：定义来自模型；具体资料需求列是本轮对现有约束的操作性解释。
needs={
'has_space':'对象身份、分析边界及空间划分依据',
'has_element':'物理组成及归属证据；不能仅凭位置接近',
'bounds':'图纸或观察证明该部位参与空间边界',
'adjacent_to':'两空间边界判定及共享边界证据',
'direct_access_to':'两个空间端点、via界面、时间、使用者和通行方式',
'supports':'构造详图、受力或营造说明；不能只看几何接触',
'represented_by':'建筑身份与资料编号的源内对应',
'located_in':'原文地点或调查定位；不补造坐标',
'record_about_place':'资料题名、表题或调查地点说明',
'has_type':'肯定的classification、分类体系、判据与输入断言',
'in_scheme':'类型概念所属的具来源分类体系',
'variant_of':'作者或读者解释、形态操作及依据；不据此补年代',
'affects':'事件、时间、对象及前后状态证据',
'anchored_to':'模型版本、坐标系、区域ID与对象对应',
'interface_of':'同一界面所关联的对象；通行界面需两个不同Space端点',
'realized_by':'墙、门等实体与指定界面的对应；开放界面可以无实体',
'intersects_space':'空间划分体系及三维范围共享的几何依据',
'similar_to':'analysisRun、resultId、输入、方法、参数及对应肯定结果',
}
prior=P.parent/'传统民居类型与形态拆解/证据与阅读记录.md'
prior_text=prior.read_text()
prior_rows={}
for line in prior_text.splitlines():
    if line.startswith('| '):
        fields=[x.strip() for x in line.strip('|').split('|')]
        if fields and re.fullmatch(r'[A-Z0-9]+:E\d+',fields[0]): prior_rows[fields[0]]=fields
def basislink(ref):
    if ref in EE: return f'[{ref}]({EE[ref]["sourceLink"]})'
    assert ref in prior_rows, ref
    return f'[{ref}](../../〔文献拆解〕传统民居类型与形态拆解/证据与阅读记录.md)'
md='# 表1 关系定义、参考依据与实例证据要求\n\n'
md+='数据版本：v0.2。关系名称、范围、定义与basisRefs直接取自模型定义；“实例证据要求”为本轮解释性整理，未新增关系约束。所有本地关系是研究者综合设计，不宣告与外部本体等价。\n\n'
md+='| 关系 | 起点 → 终点 | 含义与成立条件（模型原定义） | 参考依据 | 实例证据要求 |\n|---|---|---|---|---|\n'
for r in M['relations']:
    domain='／'.join(CL[x] for x in r['domain']);rang='／'.join(CL[x] for x in r['range'])
    md+=f'| {r["label"]}<br>`{r["id"]}` | {domain} → {rang} | {r["definition"]} | '+ '、'.join(basislink(x) for x in r['basisRefs'])+f' | {needs[r["id"]]} |\n'
md+='\n## 如何理解这些依据\n\n参考依据支持分析内容、概念区分或表达思路；它们不必直接提出同名关系。尤其has_element中的T3F2ERJG:E5主要说明单体与聚落分析层次，不能单独充当“物理组成关系”的直接定义证据。关系表保留原引用，便于后续回到原文进一步收紧论证，不把已有引用等同于论证已经充分。\n\n'
md+='## 本表引用的依据摘录\n\n以下复用既有阅读记录，不表示本轮重新通读原文。文献研究对象、术语范围与本研究的对应由研究者判断。\n\n'
for ref in sorted({x for r in M['relations'] for x in r['basisRefs']}):
    if ref in EE:
        e=EE[ref];s=SS[e['source']]
        md+=f'### {ref}\n\n{s["title"]}；PDF {e["pdfPages"]}；{e["locator"]}。\n\n{e["claim"]}\n\n适用限制：{e.get("uncertainty", "")} [原文定位]({e["sourceLink"]})\n\n'
    else:
        fields=prior_rows[ref]
        md+=f'### {ref}\n\n'+ '；'.join(fields[1:])+'\n\n[既有证据记录](../../〔文献拆解〕传统民居类型与形态拆解/证据与阅读记录.md)\n\n'
(OUT/'表1-关系定义及依据.md').write_text(md)

# 查询表：当前数据实际复算，并单列核对性质，不误写成完成真实案例人工验证。
summaries={
'Q01':'无可返回的通行记录；当前文献数据没有覆盖此关系。',
'Q02':'前廊；经I_OPEN；断言ACCESS_HV；依据E_DEMO。',
'Q03':'堂屋—卧室在I_WALL相邻，PASS_WALL明确禁止穿越该界面。',
'Q04':'名称=前廊；围合=semi_open；用途=交通、停留。',
'Q05':'CLASS_8、CLASS_1匹配各自柱筒类别；PROTO_8、PROTO_1不全部满足四项原型条件。',
'Q06':'F_1_roof_layered的原表值true与冲突来源E_COMMON同时保留。',
'Q07':'无GeometryRegion实例；未完成实际几何关联。',
'Q08':'无AnalysisRun实例；未完成相似性或聚类分析。',
'Q09':'文献27条与合成28条断言均能解析各自证据ID。',
'Q10':'十项优化均有依据引用、实现状态与验证边界。',
}
paths={
'Q01':'文献数据 direct_access_to；另核当前资料覆盖范围',
'Q02':'S_HALL → direct_access_to → S_VERANDA；via=I_OPEN',
'Q03':'邻接 + 同一界面两端点 + 同情境passage_allowed=false',
'Q04':'S_VERANDA的三组特征断言',
'Q05':'classification → 输入断言 → 类型判据逐项比较',
'Q06':'disputed断言 → evidence + conflictingEvidence',
'Q07':'筛查GeometryRegion类实例',
'Q08':'筛查AnalysisRun类实例',
'Q09':'断言evidence → 本数据集证据记录',
'Q10':'优化记录changes → basisRefs + validationBoundary',
}
md='# 表2 查询与验证结果\n\n本轮在隔离副本中执行原检查脚本，结果见[完整复算结果](复算验证结果.json)。原图谱文件未改变。\n\n'
md+=f'程序执行结果：{len(V["checks"])}项检查通过，其中{len(V["semanticGuards"])}项语义防错试验；输出{len(V["queries"])}项查询。检查通过说明编码及程序行为符合现有规则，不证明样本有效性或规则普适性。\n\n'
md+='| ID／问题 | 数据身份 | 查询路径或条件 | 本轮复算结果摘要 | 核对方式及解释边界 |\n|---|---|---|---|---|\n'
for q in V['queries']:
    md+=f'| {q["id"]} {q["question"]} | {q["datasetKind"]} | {paths[q["id"]]} | {summaries[q["id"]]} | 程序复算；{q["interpretation"]} |\n'
md+='\n## 人工核对记录\n\n本轮目视检查了既有PDF55、PDF56原页图片，确认第8号表行与源内编号底图的资料身份；第8号四项值对应E_Z8。未新增实地调查、通行观测或住宅平面匹配。既有原文审查及模型验收见[独立验收](../独立验收.md)与[原文抽核](../原文抽核记录.md)。图表独立复核另记，不能将其称为真实样本有效性验证。\n\nQ01沿用旧脚本对D_8的查询输出，同时本轮另查全文献数据确无direct_access_to断言；不能把对Dwelling端点的一次空查询单独解释为完整住宅空间搜索。\n'
assert not any(a['predicate']=='direct_access_to' for a in G['assertions'])
(OUT/'表2-查询及验证结果.md').write_text(md)

inputs=[P/n for n in ['模型定义.json','案例图谱.json','空间关系演示.json','优化依据.json','优化记录.json','检查图谱.py','迁移记录.json','独立验收.md','原文抽核记录.md']]+[source_img,prior,P/'../单体层知识图谱v0.1/证据图页/ZWDJJE99-PDF56.png']
manifest={
 'date':'2026-10-22','status':'论文图表讨论稿','modelVersion':'0.2',
 'scope':'由既有模型、案例和演示生成图表；不补造完整平面或建筑事实。',
 'inputs':[{'path':str(x.resolve()),'sha256':sha(x)} for x in inputs],
 'figures':[
  {'file':'01-模型构建过程.drawio','kind':'researcher_workflow_summary','refs':['模型定义.json','优化依据.json','案例图谱.json','空间关系演示.json','独立验收.md'],'note':'流程整理为研究者表达；虚线后续步骤尚未完成。'},
  {'file':'02-核心概念关系.drawio','kind':'schema_projection','relations':['has_space','has_element','bounds','interface_of','realized_by'],'note':'模型节选，不是完整关系图；旁注补充类内关系。'},
  {'file':'03-文献实例编码.drawio','kind':'literature_case','nodes':['D_8','R_8','T_55'],'assertions':['REP_8','F_8_load_bearing','F_8_rear_courtyard_form','F_8_column_bay_form','F_8_roof_layered'],'classifications':['CLASS_8','PROTO_8'],'evidence':['E_Z8','E_MAP','E_PROTOTYPE'],'note':'原页完整嵌入并增加定位框；类型边由CLASS_8投影，属性卡不是实体节点。未画空间或构件的未经证实轮廓。'},
  {'file':'04-空间关系编码演示.drawio','kind':'synthetic_demo','nodes':['S_HALL','S_VERANDA','I_OPEN'],'assertions':['I_OPEN_HALL','I_OPEN_OTHER','SEP_OPEN','ADJ_HV','ACCESS_HV','ACCESS_VH','ENC_V','USE_V1','USE_V2'],'evidence':['E_DEMO'],'basisRefs':['BOT03','ISM03'],'note':'区域色块是无比例图示布局；没有新增尺寸、朝向、墙体或坐标事实。双箭头合并展示两条有向断言。'}
 ],
 'checks':{'modelChecks':len(V['checks']),'semanticGuards':len(V['semanticGuards']),'queries':len(V['queries']),'allPassed':V['ok']},
 'limits':['实例编码图3仅为文献记录示例，不能替代完整建筑平面编码。','实例编码图4为合成演示，不能计入真实样本。','理论依据沿用既有记录，本轮不声称完成新的全文精读。']}
# 使用实际演示ID，避免将讲解用名称误当数据标识。
manifest['figures'][3]['assertions']=[a['id'] for a in D['assertions'] if a['id'] in manifest['figures'][3]['assertions'] or (a['subject']=='S_VERANDA' and a['predicate'] in ['space_use','enclosure_degree'])]
for item in manifest['figures']:
    dataset=D if item['kind']=='synthetic_demo' else G
    for group in ['nodes','assertions','classifications','evidence']:
        if group in item:
            known={x['id'] for x in dataset[group]}; assert set(item[group])<=known,(item['file'],group)
    path=OUT/item['file']; ET.parse(path)
dump('图表来源记录.json',manifest)

md='''# 单体层知识图谱：论文图表草稿

制作日期：2026-10-22。依据现有v0.2生成；本目录是解释与论文表达草稿，未改变模型、案例或正文。优先查看图3和图4。

## 图表入口

| 图表 | 读法 | 文件 |
|---|---|---|
| 图1 模型构建过程 | 看理论、实例资料、编码、检查及待验证工作怎样衔接 | [图片](01-模型构建过程.png)／[可编辑源文件](01-模型构建过程.drawio) |
| 图2 核心概念关系 | 看概念类和允许关系，不把它当作具体住宅 | [图片](02-核心概念关系.png)／[可编辑源文件](02-核心概念关系.drawio) |
| 表1 关系定义及依据 | 18种关系的范围、定义、引用、证据要求及依据摘录 | [打开表1](表1-关系定义及依据.md) |
| 图3 文献实例编码 | 左侧原表第8行，中部对象与特征，右侧分类及证据 | [图片](03-文献实例编码.png)／[可编辑源文件](03-文献实例编码.drawio) |
| 图4 空间关系编码演示 | 左侧区域示意，中部空间/界面子图，右侧一条通行断言 | [图片](04-空间关系编码演示.png)／[可编辑源文件](04-空间关系编码演示.drawio) |
| 表2 查询及验证结果 | 看查询输入、输出与可以支持的结论 | [打开表2](表2-查询及验证结果.md) |

## 两种实例应分别使用

图3有文献事实依据，展示记录级特征及类型判定。原表的四项值限定在各自部位或侧样范围，不能全部归给整栋建筑。类型归属边来自已有肯定分类记录，不是无条件增加的事实。它适合说明“文献资料如何编码”。

图4解释空间关系的表达机制。其色块大小、矩形形状、上下布局只是绘图安排，外围不表示实体围墙；没有比例尺或方位。它适合方法说明，标题与图注必须保留“合成演示”。

要形成“真实平面/剖面—对象编号—实例子图—证据”的实证图，还需要身份对应明确的住宅图纸，以及空间边界、界面和通行的资料。当前图谱不能逆推出缺失平面，也不能把合成演示移植为周湖8号事实。

## 图注建议

图1：单体层语义模型构建与验证路径。依据既有研究与本研究工作记录整理；虚线框表示尚待开展的真实案例验证。

图2：单体层语义模型核心概念及关系节选。概念与关系为研究者综合设计；文献依据及完整关系范围见表1。

图3：周湖8号文献记录的实例编码示例。左侧为赵潇诺学位论文PDF55（印刷44）表3.7原页及第8行定位标注，中部为源内对象、记录及四项特征，右侧为分类记录与证据追溯。四项原型试判采用2023侧样论文PDF5（印刷14）的条件作读者操作化比较，不作历史谱系推断。

图4：堂屋—前廊空间关系编码的合成演示。空间、界面、邻接与带情境的通行分别记录；区域示意无比例、无实测坐标，不对应实际住宅。

## 可追溯材料

- [图表来源与输入哈希](图表来源记录.json)：记录所用模型、原始图片、断言ID、分类ID、依据ID及适用边界。
- [本轮程序复算结果](复算验证结果.json)：隔离副本中重新运行既有检查脚本；不改变原文件。
- [图表独立验收](图表独立验收.md)：独立核对原页、图形、数据、引用及验证边界。
- [图表核验记录](图表核验记录.json)：来源哈希、本地链接、XML连接及PNG结构检查。
- [生成脚本](生成图表.py)：从模型和案例数据重建图表定义；PNG由本地draw.io导出。
- [既有语义模型讲解](../语义模型讲解与论文呈现.md)。

本轮原页核对范围为已有PDF55和PDF56图片；方法文献依据沿用已有精读记录。程序检查、原页核对、图表独立审查和实地有效性验证分别记录，不互相替代。

正式论文排版时，图3应增补原表表头和第8行的局部放大，以适应缩印；当前整页保留主要用于交代上下文与位置。图4仅选取一条通行关系的关键字段，完整记录回查原JSON。
'''
(OUT/'README.md').write_text(md)
print(json.dumps({'figures':4,'relationRows':len(M['relations']),'queries':len(V['queries']),'modelChecks':len(V['checks']),'sourceHashes':len(inputs)},ensure_ascii=False))
