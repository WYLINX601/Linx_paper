from pathlib import Path
from collections import OrderedDict
from html import escape
from io import BytesIO
import base64, json, re, hashlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / '研究对象候选汇总-按村落.md'
HTML = OUT / '研究对象候选汇总-导师浏览版.html'
MD = ROOT / '研究对象候选汇总-导师浏览版.md'
source_text = SOURCE.read_text()
manifest = json.loads((ROOT / '01_sources/assets/she-web-2026-10-06/manifest.json').read_text())
assets = {r['id']: dict(path=r['local_path'], caption=r['visual_description'].split('；')[0], credit=f"{r['source_id']} · 发布于{r['publication_date']} · 摄影：{r['photographer']}", url=r['page_url'], crop=None, rotation=0) for r in manifest if r.get('selected')}
web_captions = {
 'S01-01':'敕木山 · 山地聚落远景','S01-02':'敕木山 · 土墙瓦顶与外廊','S01-03':'敕木山 · 民居山墙及附屋',
 'S02-01':'敕木山 · 聚落与山势','S02-02':'敕木山 · 夯土民居外观','S02-03':'敕木山 · 门楼与檐廊','S02-04':'敕木山 · 山地建筑群',
 'S02-05':'敕木山 · 土墙转角与檐口','S02-06':'敕木山 · 石阶与院墙','S02-07':'敕木山 · 展览馆相关木构正屋与院落',
 'S02-08':'敕木山 · 瓦顶与院墙门洞','S02-12':'敕木山 · 民居正侧面','S02-15':'敕木山 · 瓦屋面与山墙装饰','S02-17':'敕木山 · 坡地建筑组合',
 'S03-01':'东弄 · 聚落全景','S04-03':'东弄 · 宗祠相关外观','S04-04':'东弄 · 传统民居组团','S04-05':'东弄 · 坡地建筑组合',
 'S04-07':'东弄 · 夯土山墙与石墙','S04-08':'东弄 · 建筑组团近景','S04-09':'东弄 · 展示空间入口','S04-11':'东弄 · 连续瓦屋面与檐口','S04-12':'东弄 · 水体、坡地与建筑边界',
 'S05-03':'大张坑 · 民居与石阶巷道','S05-06':'大张坑 · 聚落与民居组团','S05-07':'大张坑 · 山地建筑组合','S05-08':'大张坑 · 村落环境',
 'S06-03':'桃源 · 沿溪聚落全景','S06-04':'桃源 · 村落与水体','S06-12':'桃源 · 五显爷殿相关外观','S06-13':'桃源 · 殿宇门楼与院墙',
 'S06-14':'桃源 · 殿宇外观及装饰','S06-15':'桃源 · 公共建筑细部','S06-16':'桃源 · 柱及彩绘细部','S06-17':'桃源 · 殿宇相关场景',
 'S06-19':'桃源 · 民居屋面与侧墙','S06-20':'桃源 · 木构檐廊与板壁','S06-21':'桃源 · 石台基与坡地民居','S06-22':'桃源 · 石阶巷道与围墙',
 'S06-23':'桃源 · 瓦屋面与檐口','S06-24':'桃源 · 围墙门洞与瓦顶','S06-25':'桃源 · 雕花牛腿','S06-26':'桃源 · 街巷与墙体','S06-27':'桃源 · 木窗与石墙',
 'S06-28':'桃源 · 街巷与屋檐','S06-29':'桃源 · 民居街巷','S06-30':'桃源 · 瓦檐与围墙','S06-31':'桃源 · 石墙、板壁与附属建筑',
 'S07-01':'周湖 · 门楼与街巷拼版','S07-03':'周湖 · 院墙、门楼与坡地道路','S07-04':'周湖 · 建筑与街巷拼版','S07-06':'周湖 · 巷道与屋面',
 'S08-05':'深垟 · 石墙与院落门楼','S08-06':'深垟 · 院落与住宅外观','S08-07':'深垟 · 木构民居与院墙','S08-09':'深垟 · 清泉石上居相关院落','S08-10':'深垟 · 畲医畲药展示馆门面'
}
for r in manifest:
    if r['id'] in assets:
        assets[r['id']]['caption']=web_captions.get(r['id'],assets[r['id']]['caption'])
        assets[r['id']]['credit']=f"{r['source_id']} · 网页发布于{r['publication_date']}"

def doc(key, path, caption, credit, crop=None, rotation=0):
    assets[key] = dict(path=path, caption=caption, credit=credit, crop=crop, rotation=rotation, url='')

bank = '01_sources/assets/she-image-bank/'
crops = '01_sources/assets/she-crops/'
new = 'outputs/研究对象候选导师浏览版/assets/'
doc('phoenix-28',bank+'7KCJR9EB-002.png','28号蓝姓寮 · 卷草凤凰纹分段示意','蓝法勤，2013，95页，图1',(.115,.699,.371,.086))
doc('phoenix-chief',bank+'7KCJR9EB-003.png','蓝村长家 · 门楼梁部装饰','蓝法勤，2013，96页，图6',(.516,.204,.366,.099))
doc('phoenix-lan',bank+'7KCJR9EB-003.png','蓝凤新寮 · 前檐梁凤凰纹','蓝法勤，2013，96页，图3',(.115,.437,.371,.121))
doc('phoenix-lan-order',bank+'7KCJR9EB-004.png','蓝凤新寮 · 前后纹样排列','蓝法勤，2013，97页，图8',(.115,.395,.371,.136))
doc('phoenix-lei',bank+'7KCJR9EB-003.png','小佐雷姓寮 · 金鸡头式纹样','蓝法勤，2013，96页，图4',(.115,.615,.371,.095))
doc('phoenix-dajun',bank+'7KCJR9EB-003.png','大均民居 · 金鸡头式纹样','蓝法勤，2013，96页，图5',(.115,.769,.371,.125))
doc('phoenix-li',bank+'7KCJR9EB-004.png','李氏大屋 · 住宅及装饰细部','蓝法勤，2013，97页，图7',(.115,.160,.371,.22))
doc('tan-decoration',bank+'7KCJR9EB-003.png','丽水潭宅 · 梁部龙纹比较','蓝法勤，2013，96页，图2',(.115,.204,.371,.18))
doc('blue-front',crops+'BUUUUWRW-p064-fig42-front-door.png','蓝坤宝寮 · 门楼外观','赵圣洁，2015，48页，图4-2',(18/290,20/450,257/290,318/450))
doc('blue-perspective',crops+'BUUUUWRW-p064-fig43-section.png','蓝坤宝寮 · 剖透视','赵圣洁，2015，48页，图4-3')
doc('blue-ground',crops+'BUUUUWRW-p065-fig44-ground.png','蓝坤宝寮 · 一层平面及照片','赵圣洁，2015，49页，图4-4')
doc('blue-upper',crops+'BUUUUWRW-p065-fig45-upper.png','蓝坤宝寮 · 二层平面及照片','赵圣洁，2015，49页，图4-5')
doc('blue-section',crops+'BUUUUWRW-p073-fig419-section.png','蓝坤宝寮 · 1-1剖面','赵圣洁，2015，57页，图4-19')
doc('blue-roof',bank+'BUUUUWRW-106.png','蓝坤宝寮 · 屋顶平面','赵圣洁，2015，90页',rotation=90)
doc('blue-elevation',bank+'BUUUUWRW-108.png','蓝坤宝寮 · 2-2剖立面','赵圣洁，2015，92页',rotation=90)
doc('blue-south',bank+'BUUUUWRW-109.png','蓝坤宝寮 · 南立面','赵圣洁，2015，93页',rotation=90)
doc('blue-entrance',bank+'BUUUUWRW-110.png','蓝坤宝寮 · 主入口立面','赵圣洁，2015，94页',rotation=90)
doc('dongnong-map',crops+'BUUUUWRW-p115-map.png','东弄 · 原论文编号分布与质量图','赵圣洁，2015，99页')
doc('dazhang-village',crops+'ETTYATRB-p019-photos.png','大张坑 · 村落全貌与水口树','王文辉，2016，11页',(0,.19,.81,.55))
doc('dazhang-houses',crops+'ETTYATRB-p023-photos.png','大张坑 · 雷氏祠堂与室内陈设','王文辉，2016，15页',(0,0,.86,.52))
doc('dazhang-survey',bank+'VSES7L3M-pdf37.png','大张坑 · 聚落、材料与建筑调研','朱凌，2012，28页，图3-16',(.151,.115,.729,.305))
doc('lei-ancestral',bank+'VSES7L3M-pdf37.png','大张坑 · 雷氏祠堂历史照片','朱凌，2012，28页，图3-16',(.184,.375,.176,.037))
doc('chenbi-entrance',bank+'VSES7L3M-pdf37.png','陈璧大宅资料 · 宅前入口石作','朱凌，2012，28页，图3-17',(.676,.610,.196,.188))
doc('zhouhu-model',bank+'VSES7L3M-pdf40.png','周湖8号民居 · 建筑模型','朱凌，2012，31页，图3-20',(.088,.140,.709,.285))
doc('zhouhu-elevation',bank+'VSES7L3M-pdf40.png','周湖8号民居 · 立面','朱凌，2012，31页，图3-21',(.200,.440,.530,.405))
doc('tangwan-plan',bank+'VSES7L3M-pdf41.png','汤湾4号民宅 · 平面与室内使用','朱凌，2012，32页，图3-22',(.148,.350,.710,.380))
doc('zhouhu-types',bank+'ZWDJJE99-055.png','周湖 · 侧样分型原表','赵潇诺，2023，44页',(.133,.38,.752,.365))
doc('zhangzhuang-types',bank+'ZWDJJE99-056.png','张庄 · 侧样分型与编号分布','赵潇诺，2023，45页',(.133,.447,.752,.423))
doc('jizhuang-types',bank+'ZWDJJE99-057.png','季庄 · 侧样分型与编号分布','赵潇诺，2023，46页',(.133,.107,.752,.545))
doc('huiming-location',bank+'6NQGHZQC-pdf58.png','惠明寺 · 村落区位','潘钊，2015，50页，图4.1',(.113,.375,.800,.30))
doc('ganlan-house',bank+'VRWLBN8X-pdf3.png','东坑附近 · 河边坡地木构干栏民居','牛建农等，2009，59页，图1',(.115,.100,.497,.265))
doc('lei-row-house',bank+'VRWLBN8X-pdf4.png','东坑镇雷姓住宅 · 联排共居','牛建农等，2009，60页，图2',(.326,.106,.496,.26))
doc('mei-house',bank+'VRWLBN8X-pdf5.png','梅林老先生宅 · 多层屋檐','牛建农等，2009，61页，图3',(.115,.098,.332,.386))
doc('yanxia-platform',bank+'VRWLBN8X-pdf5.png','岩下住宅 · 侧挑晾台','牛建农等，2009，61页，图4',(.474,.615,.392,.241))
doc('dajicun-bridges',bank+'VRWLBN8X-pdf6.png','大祭村 · 木构廊桥','牛建农等，2009，62页，图5',(.065,.11,.497,.24))
doc('xiapu-house',crops+'VSES7L3M-p038-fig318.png','半月里 · 雷世儒雷氏大宅','朱凌，2012，29页，图3-18')
doc('chai-ancestral',new+'柴一涵-2025-PDF81.png','东弄 · 蓝氏宗祠及附楼','柴一涵，2025，67页，图3.14',(222/953,550/1347,507/953,380/1347))
doc('chai-temple',new+'柴一涵-2025-PDF82.png','东弄 · 汤三公庙','柴一涵，2025，68页，图3.15',(302/953,242/1347,386/953,290/1347))
doc('gangshi-home',new+'柴一涵-2025-PDF85.png','蓝景芬住宅 · 民歌传承馆及院落','柴一涵，2025，71页，图3.20',(154/953,270/1347,683/953,263/1347))
doc('gangshi-square',new+'柴一涵-2025-PDF85.png','岗石 · 清莲广场','柴一涵，2025，71页，图3.21',(225/953,886/1347,541/953,205/1347))
doc('gangshi-hall',new+'柴一涵-2025-PDF87.png','岗石 · 文化礼堂','柴一涵，2025，73页，图3.23',(274/953,117/1347,442/953,332/1347))
doc('gangshi-office',new+'柴一涵-2025-PDF87.png','岗石 · 原村委会外观与院落','柴一涵，2025，73页，图3.24',(249/953,740/1347,455/953,340/1347))
doc('taoyuan-map',new+'柴一涵-2025-PDF125.png','桃源 · 道路与建筑层数分析','柴一涵，2025，111页，图5.3—5.4',(165/953,130/1347,670/953,465/1347))
doc('taoyuan-bridges',new+'柴一涵-2025-PDF128.png','桃源 · 三座石拱桥','柴一涵，2025，114页，图5.11',(112/953,318/1347,725/953,296/1347))

rows=[]
for line in (OUT/'展示内容.tsv').read_text().splitlines():
    if not line or line.startswith('#'): continue
    fields=line.split('|')
    assert len(fields)==6,(line,len(fields))
    village,name,summary,materials,credit,keys=fields
    rows.append(dict(village=village,name=name,summary=summary,materials=materials,credit=credit,images=[k for k in keys.split(',') if k]))
groups=OrderedDict()
for row in rows: groups.setdefault(row['village'],[]).append(row)
villages=[g for g in groups if g not in ['地点线索补充','比较资料']]
assert len(villages)==47
used=[k for row in rows for k in row['images']]
assert len(used)==len(set(used)), 'Repeated image identifiers'
for key in used: assert (ROOT/assets[key]['path']).exists(),key
stats=dict(village_name_entries=len(villages),literature_records=23,selected_web_images=sum(r.get('selected',False) for r in manifest),village_material_rows=sum(len(groups[g]) for g in villages),supplement_rows=len(groups['地点线索补充']),comparison_rows=len(groups['比较资料']),illustration_units=len(used),web_illustrations=sum(k.startswith('S') for k in used),document_illustrations=sum(not k.startswith('S') for k in used))

cache={}
def uri(path):
    if path not in cache:
        im=Image.open(ROOT/path).convert('RGB');im.thumbnail((2100,2100))
        b=BytesIO();im.save(b,format='JPEG',quality=90,optimize=True)
        cache[path]='data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
    return cache[path]

def window(a, lightbox=False):
    data=uri(a['path'])
    width,height=Image.open(ROOT/a['path']).size
    if a['crop']:
        x,y,w,h=a['crop'];ratio=width*w/(height*h)
        style=f'width:{100/w:.6f}%;left:{-100*x/w:.6f}%;top:{-100*y/h:.6f}%;'
        content=f'<span class="crop-frame" style="--ratio:{ratio:.8f};--native-width:{width*w:.2f}px"><img src="{data}" alt="{escape(a["caption"])}" style="{style}"></span>'
    elif a['rotation']:
        ratio=height/width
        style=f'width:{100*width/height:.6f}%;left:50%;top:50%;transform:translate(-50%,-50%) rotate(90deg);'
        content=f'<span class="crop-frame" style="--ratio:{ratio:.8f}"><img src="{data}" alt="{escape(a["caption"])}" style="{style}"></span>'
    else:
        content=f'<span class="native-frame"><img src="{data}" alt="{escape(a["caption"])}"></span>'
    return content

def figure(key):
    a=assets[key]
    ref=f'<a href="{escape(a["url"])}" target="_blank" rel="noopener">{escape(a["credit"])}</a>' if a['url'] else escape(a['credit'])
    return f'<figure><button class="image-button" type="button" data-image="{key}" aria-label="放大：{escape(a["caption"])}">{window(a)}</button><figcaption>{escape(a["caption"])}<span class="image-credit">{ref}</span></figcaption></figure>'

def table_head():
    return '<thead><tr><th scope="col" class="name">对象</th><th scope="col">已有资料与认识</th><th scope="col" class="materials">资料配置</th></tr></thead>'
def table_row(row):
    return f'<tr><td>{escape(row["name"])}</td><td>{escape(row["summary"])}</td><td>{escape(row["materials"])}</td></tr>'
def record(row,index):
    if not row['images']:
        return f'<div class="record text-record"><table>{table_head()}<tbody>{table_row(row)}</tbody></table><div class="source">来源：{escape(row["credit"])}</div></div>'
    pics=row['images']
    first=pics[:2]
    lead=f'<div class="record-lead"><table>{table_head()}<tbody>{table_row(row)}</tbody></table><div class="gallery-pair">'+''.join(figure(k) for k in first)+'</div></div>'
    tail=('<div class="gallery-flow">'+''.join(figure(k) for k in pics[2:])+'</div>') if len(pics)>2 else ''
    density=' dense-gallery' if len(pics)>=6 and row['name']!='蓝坤宝寮' else ''
    return f'<article class="record{density}" id="record-{index}">{lead}{tail}<div class="source">来源：{escape(row["credit"])}</div></article>'

scale_rows=[('敕木山','典型大户民居4幢','官方介绍，2022'),('东弄老村','民居107幢，其中传统民居73幢、空置传统民居16幢','吴钰论文，2022提交'),('大张坑','自然村民居37幢，其中钢筋水泥结构1幢','王文辉，2015提交／2016书目'),('桃源','清代建筑10幢／处','赵潇诺2023；柴一涵2025')]
scope_note='本文依据已保存文献与网络资料整理，供候选对象讨论；描述保留资料时点，当前存续、保存状况及进入条件需现场核实。'
count_note='村落按原名称条目统计，尚未做地名归并；资料条目含建筑群、单体及相关设施，不换算为独立建筑数；各村建筑数量分别保留原口径。'
intro=f'<header><div class="eyebrow">导师讨论材料 · 2026年10月12日</div><h1>景宁畲族建筑研究对象候选汇总</h1><p class="subtitle">按村落浏览 · 总体统计与建筑图像</p><div class="stats"><div><span>村落名称线索</span><strong>47<small>条</small></strong></div><div><span>已汇集文献书目</span><strong>23<small>条</small></strong></div><div><span>资料库精选网页图像</span><strong>58<small>份</small></strong></div></div><p class="inventory">本版整理村内资料{stats["village_material_rows"]}条、地点补充7条、比较资料7条，配置图像{stats["illustration_units"]}幅。</p><p class="note">{scope_note}</p><h2>文献中的建筑规模</h2><table class="scale"><thead><tr><th>村落</th><th>文献记载</th><th>来源时点</th></tr></thead><tbody>'+''.join(f'<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>' for a,b,c in scale_rows)+f'</tbody></table><p class="note">{count_note}</p></header>'
nav='<nav aria-label="村落导航">'+''.join(f'<a href="#village-{i}">{escape(v.split("（")[0])}</a>' for i,v in enumerate(groups))+'</nav>'
sections=[]
i=0
compact_villages=villages[16:45]
compact_done=False
for g,rs in groups.items():
    if g in compact_villages:
        if compact_done: continue
        compact_done=True
        compact='<section class="compact-villages"><h2>其余具名与名单村落</h2><table class="compact-table"><thead><tr><th class="compact-place">村落</th><th class="compact-object">对象</th><th>已有资料与认识</th></tr></thead><tbody>'
        for village in compact_villages:
            for n,row in enumerate(groups[village]):
                anchor=f'id="village-{list(groups).index(village)}"' if n==0 else ''
                compact+=f'<tr {anchor} data-village="{escape(village)}"><td>{escape(village)}</td><td>{escape(row["name"])}</td><td>{escape(row["summary"])}<span class="compact-source">{escape(row["credit"])}</span></td></tr>'
                i+=1
        compact+='</tbody></table></section>'
        sections.append(compact)
        continue
    display=g.replace('（原文地点）','').replace('（族群关联待核）','').replace('（原文名，地名待核）','（原文名）')
    section=f'<section class="village" id="village-{list(groups).index(g)}"><h2>{escape(display)}</h2>'
    if g=='东弄村': section+='<p class="condition">现状核查重点：2025年官方答复提到古村部分老房严重失修，现场存续与进入条件应优先核实。</p>'
    if g=='地点线索补充': section+='<p class="section-note">按文献原地点写法保留的住宅与建筑群资料。</p>'
    if g=='比较资料': section+='<p class="section-note">外地住宅、县内比较及泛类型背景。</p>'
    for row in rs: section+=record(row,i);i+=1
    sections.append(section+'</section>')

bibliography=[
 '赵潇诺，2023，《景宁畲族传统民居营造技艺研究》。',
 '赵圣洁，2015，《浙江省景宁县东弄村畲族民居初探》。',
 '吴钰，2023书目（2022提交），《基于民族特性的新畲寮风格民居设计研究——以景宁东弄村为例》。',
 '王文辉，2016书目（2015提交），《浙江景宁传统畲族民居及其保护与更新——以大张坑村为中心》。',
 '蓝法勤，2013，《浙江景宁畲族传统民居卷草凤凰纹装饰研究》。',
 '柴一涵，2025，《聚落“双修”视角下景宁畲族传统村落公共文化空间重构研究》。',
 '朱凌，2012，《浙江景宁畲族自治县县城建筑有机更新研究》。',
 '潘钊，2015，《景宁畲族传统村落的保护与发展研究》。',
 '汪梅，2006，《人与自然的完美演绎——记景宁畲族住宅建筑的特色》。',
 '牛建农等，2009，《浙江景宁畲族自治县畲族民居特色探析》。',
 '阮仪三，2008，《国家历史文化名城研究中心历史街区调研——浙江景宁东弄畲族村》。'
]
web_sources=json.loads((ROOT/'01_sources/2026-10-06-民居网络照片来源.json').read_text())
refs='<section class="references"><h2>主要资料来源</h2><ol>'+''.join('<li>'+escape(r)+'</li>' for r in bibliography)+'</ol><ul>'+''.join(f'<li>{r["id"]} · <a href="{escape(r["page_url"])}">{escape(r["title"])}</a> · {r["publication_date"]} · 摄影署名：{escape(r["photographer"])}</li>' for r in web_sources)+'</ul><p class="note">图像保留原署名与水印。网页日期为发布日期；拍摄时间及原文页码、图注、对象关系可回查完整底稿与照片索引。</p></section>'

style='''
:root{color-scheme:light;--ink:#26352e;--muted:#68756d;--line:#d8dfda;--soft:#f1f4f0;--accent:#476453;}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif;font-size:14px;line-height:1.75;color:var(--ink);background:#fff}main{max-width:980px;margin:0 auto;padding:36px 34px 60px}h1{font-size:25px;font-weight:600;margin:8px 0}h2{font-size:19px;font-weight:600;margin:22px 0 12px}p{margin:8px 0}.eyebrow{font-size:12px;color:var(--muted);letter-spacing:.07em}.subtitle{color:var(--muted);margin:0 0 22px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.stats>div{padding:14px 18px;background:var(--soft);border-radius:12px}.stats span{display:block}.stats strong{display:block;font-size:30px;line-height:1.5;font-weight:600}.stats small{font-size:14px;margin-left:6px;font-weight:400}.inventory{margin:14px 0;color:var(--muted)}.note{font-size:12px;color:var(--muted)}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}nav{display:flex;flex-wrap:wrap;gap:5px 16px;margin:24px 0;padding:16px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);font-size:12px}.village{margin:26px 0 0}.village h2{border-bottom:1px solid var(--line);padding-bottom:9px;break-after:avoid}.condition,.section-note{font-size:12px;color:var(--muted);margin:0 0 12px}.record{margin:0 0 18px;}.record table{table-layout:fixed}.record th.name{width:22%}.record th.materials{width:19%}table{border-collapse:collapse;width:100%;margin:0 0 10px}th,td{text-align:left;vertical-align:top;padding:9px 10px 9px 0;border-bottom:1px solid var(--line);overflow-wrap:anywhere}th{font-weight:600;font-size:12px}.scale th:first-child{width:15%}.scale th:last-child{width:29%}.gallery-pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin:0 0 14px;align-items:start}figure{margin:0;min-width:0;break-inside:avoid}.image-button{display:block;border:0;padding:0;width:100%;background:transparent;text-align:left;color:inherit;cursor:zoom-in}.image-button:focus-visible{outline:2px solid var(--accent);outline-offset:4px}.native-frame{display:flex;align-items:center;justify-content:center;min-width:0}.native-frame img{display:block;max-width:100%;max-height:320px;width:auto;height:auto}.crop-frame{display:block;position:relative;overflow:hidden;width:100%;max-width:calc(320px * var(--ratio));aspect-ratio:var(--ratio);margin:0 auto}.crop-frame img{position:absolute;display:block;max-width:none;height:auto}figcaption{font-size:12px;margin-top:6px;line-height:1.6}.image-credit{display:block;font-size:10px;color:var(--muted);margin-top:2px}.image-credit a{color:inherit}.source{font-size:11px;color:var(--muted);margin:5px 0 0;break-before:avoid}.text-record{break-inside:avoid}.references{font-size:12px;margin-top:32px;border-top:1px solid var(--line)}.references li{margin-bottom:4px}dialog{border:0;padding:22px;width:min(96vw,1180px);max-height:96vh;background:#fff;color:var(--ink)}dialog::backdrop{background:rgba(20,30,25,.72)}dialog .crop-frame{max-width:calc(76vh * var(--ratio))}dialog .native-frame img{max-height:76vh;max-width:100%}dialog .close{float:right;border:1px solid var(--line);background:var(--soft);padding:6px 14px;font:inherit;color:inherit;cursor:pointer}dialog h2{font-size:16px;margin:0 100px 12px 0}.dialog-credit{font-size:12px;color:var(--muted)}
@media(max-width:600px){main{padding:24px 16px}h1{font-size:21px}.stats{gap:8px}.stats>div{padding:10px}.stats strong{font-size:25px}.stats span{font-size:11px}.gallery-pair{grid-template-columns:1fr}.record th.name{width:25%}.record th.materials{width:22%}body{font-size:13px}.image-credit{font-size:11px}}
@media print{@page{size:A4;margin:13mm 14mm 15mm}body{font-size:10.5pt;line-height:1.6}main{max-width:none;margin:0;padding:0}h1{font-size:19pt}h2{font-size:13pt;margin:14px 0 8px}.eyebrow,.subtitle,.inventory,.note,.condition,.section-note{font-size:8.5pt}.stats{gap:10px}.stats>div{border-radius:8px;padding:10px 14px}.stats strong{font-size:22pt}.stats span{font-size:9pt}.stats small{font-size:10pt}nav{display:none}.village{margin-top:18px}.gallery-pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-bottom:10px;break-inside:avoid}.record-lead{break-inside:avoid}.native-frame img{max-height:62mm}.crop-frame{max-width:calc(62mm * var(--ratio))}figcaption{font-size:8pt}.image-credit{font-size:7pt}.source{font-size:8pt}.record{margin-bottom:14px}th{font-size:8.5pt}th,td{padding:7px 8px 7px 0}a{color:inherit}.references{font-size:8.5pt}dialog{display:none!important}button{cursor:default}p,td{orphans:2;widows:2}}
'''
style+='''
.gallery-flow{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-bottom:14px;align-items:start}.crop-frame{max-width:min(calc(320px * var(--ratio)),var(--native-width,3000px))}.compact-table{table-layout:fixed}.compact-place{width:21%}.compact-object{width:25%}.compact-table tr{break-inside:avoid}.compact-source{display:block;font-size:11px;color:var(--muted);margin-top:3px}.compact-villages h2{break-after:avoid}dialog .crop-frame{max-width:calc(76vh * var(--ratio))}
@media(max-width:600px){.gallery-flow{grid-template-columns:1fr}.compact-place{width:25%}.compact-object{width:25%}}
@media print{.gallery-flow{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-bottom:10px}.dense-gallery .gallery-flow{grid-template-columns:repeat(3,minmax(0,1fr))}.gallery-flow figure{break-inside:avoid}.compact-source{font-size:7.5pt}.compact-table{font-size:9pt}.crop-frame{max-width:min(calc(62mm * var(--ratio)),var(--native-width,3000px))}.image-button:focus-visible{outline:none}thead{display:table-header-group}}
'''
dialogs='<dialog id="image-dialog" aria-labelledby="dialog-title"><button type="button" class="close" id="dialog-close">关闭</button><h2 id="dialog-title"></h2><div id="dialog-image"></div><p class="dialog-credit" id="dialog-credit"></p></dialog>'
script='''<script>
const dialog=document.getElementById('image-dialog');
document.querySelectorAll('.image-button').forEach(button=>button.addEventListener('click',()=>{const figure=button.closest('figure');document.getElementById('dialog-title').textContent=figure.querySelector('figcaption').firstChild.textContent;document.getElementById('dialog-image').replaceChildren(button.firstElementChild.cloneNode(true));document.getElementById('dialog-credit').textContent=figure.querySelector('.image-credit').textContent;dialog.showModal();}));
document.getElementById('dialog-close').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
</script>'''
document='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>研究对象候选汇总 · 导师浏览版</title><style>'+style+'</style></head><body><main>'+intro+nav+''.join(sections)+refs+'</main>'+dialogs+script+'</body></html>'
HTML.write_text(document)

md=['---','type: deliverable','status: advisor-browsing-draft','created: 2026-10-12','updated: 2026-10-12','source_reviewed: 2026-10-06','scope: 导师图文浏览版的可编辑文本与图片索引；非正式样本或现存数量调查','---','','# 景宁畲族建筑研究对象候选汇总 · 导师浏览版','','[打开完整图文浏览版](outputs/研究对象候选导师浏览版/研究对象候选汇总-导师浏览版.html) · [PDF分享版](outputs/研究对象候选导师浏览版/研究对象候选汇总-导师浏览版.pdf) · [[研究对象候选汇总-按村落|完整查证底稿]]','','本页保存可编辑文字和图源索引；按已确认布局排版的完整图片展示见上方图文版与PDF。','','## 总体统计','','| 村落名称线索 | 已汇集文献书目 | 资料库精选网页图像 |','| --- | --- | --- |','| 47条 | 23条 | 58份 |','',f'本版整理村内资料{stats["village_material_rows"]}条、地点补充7条、比较资料7条，配置图像{stats["illustration_units"]}幅。','',scope_note,'',count_note,'','## 文献中的建筑规模','','| 村落 | 文献记载 | 来源时点 |','| --- | --- | --- |']
md.extend('| '+' | '.join(r)+' |' for r in scale_rows)
md+=['','村落按原列表顺序浏览；下列文字概述为文献与既有图像的简要归纳，原文定位见每项来源及完整底稿。','']
for g,rs in groups.items():
    display=g.replace('（原文名，地名待核）','（原文名）')
    md+=['## '+display,'']
    if g=='东弄村': md+=['2025年官方答复提到古村部分老房严重失修，现场存续与进入条件应优先核实。','']
    for row in rs:
        md+=['| 对象 | 已有资料与认识 | 资料配置 |','| --- | --- | --- |','| '+' | '.join([row['name'],row['summary'],row['materials']])+' |','']
        if row['images']:
            md+=['配图：'+' · '.join(f'[{assets[key]["caption"]}]({assets[key]["path"]})' for key in row['images'])+'。','']
        md+=['来源：'+row['credit']+'。','']
md+=['## 主要资料来源','']+['- '+r for r in bibliography]+['','图像来源及拍摄信息：[[01_sources/2026-10-06-民居网络照片索引]]。完整来源、对象关系和待核细节：[[研究对象候选汇总-按村落]]。研究定位：[[景宁畲族传统民居风貌特征提取与知识图谱构建研究v0.5]]。','']
MD.write_text('\n'.join(md))

audit={'created':'2026-10-12','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'statistics':stats,'villages':villages,'rows':rows,'image_records':{k:assets[k] for k in used},'source_image_corrections':['雷氏祠堂与陈璧大宅改用VSES7L3M-pdf37完整原页的对应区域；旧合并裁切未完整覆盖对应照片。','干栏照片位于VRWLBN8X-pdf3的图1；pdf2仅含文字，未作配图。','VRWLBN8X-pdf5对应梅林老先生宅与岩下晾台；未将这两张照片赋给潘家大院。','蓝姓村落文字记录未提供可明确对应的照片，不将同页东坑干栏照片挪用。'],'notes':['网页图像及PDF工作副本仅编码和缩放以便内嵌；图源文件不改动，定向显示与图表区域由版式视窗控制。','47为原村名条目数；村内资料条目和图像单元均不视为独立建筑数量。']}
(OUT/'核对记录.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
print(json.dumps({'html':str(HTML),'markdown':str(MD),'statistics':stats,'html_bytes':HTML.stat().st_size},ensure_ascii=False,indent=2))
