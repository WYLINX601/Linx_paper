#!/usr/bin/env python3
"""Build the authorized V01 topology extension from its archived source.
Exact decimal geometry for this synthetic scope, never a survey/solid recognizer.
No database access. verify recomputes without mutating the canonical model.
"""
import argparse
import copy
from fractions import Fraction as F
import hashlib
import importlib.util
from itertools import combinations, product
import json
import math
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CASE = HERE.parent
ARCHIVE = CASE.parents[1] / 'archive/2026-10-26-V01拓扑更新前'
BASE = ARCHIVE / '本地基线/案例模型.json'
spec = importlib.util.spec_from_file_location('wj', HERE/'墙轴交接核验.py')
wj = importlib.util.module_from_spec(spec); spec.loader.exec_module(wj)

def save(path, obj):
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    tmp.replace(path)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def wall_column(wall, column, floor_z):
    """Axis-aligned, butt-ended uncut rectangle × constant lower height; circular column.
    Gable triangles above the wall's lowest top are excluded (sufficient for V01 columns).
    Interior overlap includes containment; NOT OGC's narrower named Overlaps predicate.
    """
    if floor_z is None:
        return {'kind':'unknown_level_review'}
    a,b = map(wj.vec, (wall['a'],wall['b']))
    if a == b or (a[0] != b[0] and a[1] != b[1]):
        return {'kind':'unsupported_wall_review'}
    t=F(str(wall['thickness']))/2
    cx,cy,cz = wj.vec(column['center']); radius=F(str(column['radius']))
    if t <= 0 or radius <= 0 or column['height'] <= 0:
        return {'kind':'invalid_geometry_review'}
    bounds=[(min(a[i],b[i]),max(a[i],b[i])) if a[i]!=b[i] else (a[i]-t,a[i]+t) for i in (0,1)]
    nearest=tuple(max(lo,min(hi,p)) for p,(lo,hi) in zip((cx,cy),bounds))
    d2=sum((p-q)**2 for p,q in zip((cx,cy),nearest))
    top=min(F(str(p[2])) for p in wall['topProfile'])
    bottom=F(str(floor_z)); zlo=max(bottom,cz); zhi=min(top,cz+F(str(column['height'])))
    if top <= bottom:
        return {'kind':'invalid_geometry_review'}
    if d2 > radius**2 or zlo > zhi:
        return {'kind':'disjoint'}
    direction=wj.sub(b,a)
    u=wj.dot(wj.sub((cx,cy),a),direction)/wj.dot(direction,direction)
    u=max(F(0),min(F(1),u))
    return {'kind':'intersection',
            'intersectionKind':'interior_overlap' if d2 < radius**2 and zlo < zhi else 'boundary_contact',
            'atWall':wj.at(u),'commonZ':[float(zlo),float(zhi)]}

def cross3(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def common_segment(a,b,c,d):
    a,b,c,d=map(wj.vec,(a,b,c,d));r=wj.sub(b,a);s=wj.sub(d,c)
    if not any(r) or not any(s): return None
    if any(cross3(r,s)) or any(cross3(wj.sub(c,a),r)):return None
    t0=wj.dot(wj.sub(c,a),r)/wj.dot(r,r);t1=wj.dot(wj.sub(d,a),r)/wj.dot(r,r)
    lo=max(F(0),min(t0,t1));hi=min(F(1),max(t0,t1))
    if lo>=hi:return None  # a point is not a shared boundary curve
    return tuple(sorted((tuple(a[i]+t*r[i] for i in range(3)) for t in (lo,hi))))

def strip_valid(vertices):
    # Restricted RS-01 scope: convex roof patches spanning X, linear height over Y.
    # Exact validation prevents general polygons, bowties and nonplanar input leaking in.
    v=list(map(wj.vec,vertices))
    if len(v)!=4 or len(set(v))!=4:return False
    xs=sorted({p[0] for p in v});ys=sorted({p[1] for p in v})
    if len(xs)!=2 or len(ys)!=2:return False
    if {(p[0],p[1]) for p in v} != set(product(xs,ys)):return False
    if any(len({p[2] for p in v if p[1]==y})!=1 for y in ys):return False
    return all((a[0]==b[0]) != (a[1]==b[1]) for a,b in zip(v,v[1:]+v[:1]))

def roof_shared(va,vb):
    if not strip_valid(va) or not strip_valid(vb):return {'kind':'unsupported_patch_review'}
    a,b=list(map(wj.vec,va)),list(map(wj.vec,vb))
    if set(a)==set(b):return {'kind':'duplicate_patch_review'}
    # Disjoint projected interiors are a sufficient condition for this pair's disjoint
    # 3D interiors; other projected overlaps are left for a general 3D engine.
    ranges=lambda v,i:(min(p[i] for p in v),max(p[i] for p in v))
    if all(min(ranges(a,i)[1],ranges(b,i)[1])>max(ranges(a,i)[0],ranges(b,i)[0]) for i in (0,1)):
        return {'kind':'projected_interior_overlap_review'}
    shared=set()
    for p,q in zip(a,a[1:]+a[:1]):
        for r,s in zip(b,b[1:]+b[:1]):
            segment=common_segment(p,q,r,s)
            if segment:shared.add(segment)
    if not shared:return {'kind':'no_shared_curve'}
    if len(shared)!=1:return {'kind':'multiple_shared_curves_review'}
    start,end=next(iter(shared));role='unclassified'
    if start[2]==end[2]:
        # Valid only for the linear convex strips accepted above, not arbitrary roofs.
        za=sum(p[2] for p in a)/4;zb=sum(p[2] for p in b)/4
        if za<start[2] and zb<start[2]:role='ridge'
        elif za>start[2] and zb>start[2]:role='valley'
    return {'kind':'shared_curve','boundaryStart':[float(x) for x in start],
            'boundaryEnd':[float(x) for x in end],'boundaryRole':role}

def checks():
    out=wj.check_rules()
    wall={'a':[0,0],'b':[2,0],'thickness':0.2,'topProfile':[[0,0,2],[2,0,2]]}
    def col(x,y,z=0,h=2,r=.1):return {'center':[x,y,z],'radius':r,'height':h}
    tests=[('柱包络内部重叠',col(0,0),'interior_overlap'),
           ('墙中段侧向相切',col(1,.2),'boundary_contact'),
           ('墙端外侧相切',col(-.1,0),'boundary_contact'),
           ('微缝不吸附',col(1,.20001),'disjoint'),
           ('Z分离不误接',col(1,0,3),'disjoint'),
           ('Z端面相切',col(1,0,2),'boundary_contact'),
           ('截面包含仍算内部相交',col(1,0,r=.05),'interior_overlap')]
    for name,c,expected in tests:
        result=wall_column(wall,c,0);assert result.get('intersectionKind',result['kind'])==expected,(name,result)
        out.append({'name':name,'passed':True})
    assert wall_column(wall,col(1,0),None)['kind']=='unknown_level_review'
    reverse=copy.deepcopy(wall);reverse['a'],reverse['b']=wall['b'],wall['a']
    assert wall_column(wall,col(0,0),0)['atWall']=='ATSTART' and wall_column(reverse,col(0,0),0)['atWall']=='ATEND'
    out.extend([{'name':'墙柱层位缺失保留待审','passed':True},{'name':'墙端顺序互换部位同步','passed':True}])
    a=[[0,0,0],[2,0,0],[2,1,1],[0,1,1]];b=[[0,1,1],[2,1,1],[2,2,0],[0,2,0]]
    assert roof_shared(a,b)['boundaryRole']=='ridge'
    assert roof_shared(a,b)==roof_shared(b,a)==roof_shared(a,list(reversed(b)))
    assert roof_shared(a,[[x,y,z+1] for x,y,z in b])['kind']=='no_shared_curve'
    assert roof_shared(a,[[x+2,y,z] for x,y,z in b])['kind']=='no_shared_curve'
    assert roof_shared(a,a)['kind']=='duplicate_patch_review'
    assert roof_shared([[x,y,-z] for x,y,z in a],[[x,y,-z] for x,y,z in b])['boundaryRole']=='valley'
    assert roof_shared(a,[b[0],b[2],b[1],b[3]])['kind']=='unsupported_patch_review'
    assert roof_shared(a,[[x,y-.2,z] for x,y,z in b])['kind']=='projected_interior_overlap_review'
    coplanar=[[0,1,1],[2,1,1],[2,2,2],[0,2,2]]
    assert roof_shared(a,coplanar)['boundaryRole']=='unclassified'
    out.extend({'name':n,'passed':True} for n in ['三维共边及正脊','交换坡面及环方向','投影重合但Z不同不共边','单点不当共边','重复坡面待审','天沟分类','自交四边形拒绝','内部投影重叠待审','共面共边不擅称折线'])
    return out

def build():
    model=json.loads(BASE.read_text());nodes={n['id']:n for n in model['nodes']}
    assert sha(BASE)=='03aef114820ba2b9b998e8d36f5e226aad4d45d8e5a2051e1876f6d7bc9e7c05'
    walls=sorted((n for n in model['nodes'] if 'Wall' in n['labels']),key=lambda n:n['id'])
    columns=sorted((n for n in model['nodes'] if 'Column' in n['labels']),key=lambda n:n['id'])
    added=[];wp=[];cp=[]
    def edge(id,typ,source,target,properties,evidence=None):
        e={'id':id,'type':typ,'source':source,'target':target,'properties':properties,
           'status':'synthetic_geometry_derived','evidence':evidence or ['EV01']}
        added.append(e);return e
    for a,b in combinations(walls,2):
        ga,gb=a['geometry'],b['geometry'];r=wj.assess(ga['a'],ga['b'],gb['a'],gb['b'],0,0)
        wp.append({'source':a['id'],'target':b['id'],**r})
        if r['kind']=='point':
            edge(f"WJ-{a['id']}-{b['id']}",'AXIS_JOINS',a['id'],b['id'],{k:r[k] for k in ['atSource','atTarget','junctionXY']}|{'ruleId':'WJ-01-v1'})
    for w,c in product(walls,columns):
        r=wall_column(w['geometry'],c['geometry'],model['parameters']['floor_z_m']);cp.append({'source':w['id'],'target':c['id'],**r})
        if r['kind']=='intersection':
            edge(f"WC-{w['id']}-{c['id']}",'ENVELOPE_INTERSECTS',w['id'],c['id'],{k:r[k] for k in ['intersectionKind','atWall','commonZ']}|{'ruleId':'WC-01-v1'})
    g=nodes['RF01']['geometry'];x0,x1=g['x'];y0,y1=g['y'];yr=g['ridgeY'];ze,zr=g['eaveZ'],g['ridgeZ']
    south=[[x0,y0,ze],[x1,y0,ze],[x1,yr,zr],[x0,yr,zr]]
    north=[[x0,yr,zr],[x1,yr,zr],[x1,y1,ze],[x0,y1,ze]]
    for id,name,verts,azimuth in [('RS01','主屋南坡面',south,180),('RS02','主屋北坡面',north,0)]:
        a,b,c=verts[:3];area=math.sqrt(sum(v*v for v in cross3(wj.sub(b,a),wj.sub(c,a))))
        ys=[p[1] for p in verts];zs=[p[2] for p in verts]
        n={'id':id,'name':name,'class':'Element','labels':['Element','RoofSurface'],
           'properties':{'caseId':'V01','recordStatus':'synthetic_geometry_derived','areaM2':area,
                         'slopeDeg':math.degrees(math.atan2(max(zs)-min(zs),max(ys)-min(ys))),
                         'slopeAzimuthDeg':azimuth,'representation':'ideal_zero_thickness_roof_patch'},
           'geometry':{'kind':'polygon3d','vertices':verts},'evidence':['EV01','EV07','EV08'],
           'propertyOrigins':{'geometry':{'status':'synthetic_geometry_derived','sourceObject':'RF01','ruleId':'RS-01-v1'},
                              'areaM2':{'status':'synthetic_geometry_derived','ruleId':'RS-01-v1'},
                              'slopeDeg':{'status':'synthetic_geometry_derived','ruleId':'RS-01-v1'}}}
        model['nodes'].append(n)
        edge(f'RS-PART-{id}','PART_OF',id,'RF01',{'meaning':'屋顶系统中的理想坡面分析单元'})
        for ev,scope in [('EV01','同源合成参数支持坡面生成，不是实测'),('EV07','同源生成剖面提供坡度与高度参照，不独立证明完整面域'),('EV08','同源生成投影提供平面范围，不独立证明三维高度')]:
            edge(f'RS-DOC-{ev}-{id}','DOCUMENTS',ev,id,{'scope':scope,'dependency':'same_synthetic_source_EV01'})
    shared=roof_shared(south,north);assert shared['kind']=='shared_curve'
    edge('RS-RS01-RS02','SHARES_BOUNDARY','RS01','RS02',{k:shared[k] for k in ['boundaryStart','boundaryEnd','boundaryRole']}|{'ruleId':'RS-01-v1'})
    definitions=[
        {'type':'AXIS_JOINS','zh':'墙轴交接','definition':'同一分析层位两条有限直线墙轴的唯一公共点；不保证实体接触或构造连接。','direction':'语义对称；按ID排序单边存储，双方部位按存储端解释','minimum':'双方交接部位、交点XY、规则引用及证据','example':'W08与W10在(0,-4.8)端部交接'},
        {'type':'ENVELOPE_INTERSECTS','zh':'墙柱简化包络相交','definition':'在WC-01限定的未扣洞、未裁切简化包络中，墙矩形柱体与圆柱有非空交集；区分内部重叠和边界接触，不等同于实际构造相接。','direction':'墙→柱；几何含义对称，角色固定','minimum':'相交类别、柱中心投影在墙轴的部位、共同Z区间、规则引用及证据','example':'W01与C01的简化包络内部重叠，实际端部处理待查'},
        {'type':'SHARES_BOUNDARY','zh':'坡面共享边界','definition':'RS-01限定的理想坡面在三维空间共享一段正长度边界；不以平面投影交叉替代。','direction':'语义对称；按ID排序存一条边','minimum':'公共直线段的两个XYZ端点、边界角色、规则引用及证据','example':'RS01与RS02共享正脊线，长度由端点计算'}]
    model['relationVocabulary'].extend(definitions)
    model['relationships'].extend(added)
    model['meta'].update(updated='2026-10-26',revision='V01-topology-20261026',previousSourceSha256=sha(BASE))
    model['meta']['formatNote']='本文件是维护主源；Neo4j为其查询投影，实际同步状态见Neo4j/拓扑入库核验.json。'
    model['topologyRules']=[
        {'id':'WJ-01-v1','sourceIds':['S01','S03'],'record':'构建方法与决策记录.md#r01用最少信息补齐墙与墙的交接','scope':'共同层位直线墙轴唯一交点','numericPolicy':'exact decimal fractions; no survey snapping'},
        {'id':'WC-01-v1','sourceIds':['S03'],'record':'构建方法与决策记录.md#r02墙柱推广与实施','scope':'轴对齐、端部平截、未扣洞墙矩形包络×统一地坪至最低墙顶；直立圆柱。内部重叠包含截面包含，不是OGC Overlaps专名。','numericPolicy':'exact decimal fractions; no survey tolerance','interpretation':'只有简化几何关系被确认；真实接触、嵌柱、裁切和受力均未确定'},
        {'id':'RS-01-v1','sourceIds':['S03','S07'],'record':'构建方法与决策记录.md#r03坡面推广与实施','scope':'沿X拉伸、Z沿Y线性变化的凸四边形面，投影内部不重叠；三维共直线段；非通用曲面算法','numericPolicy':'exact decimal fractions for common boundary; floating point for derived area/slope','interpretation':'坡面无厚度、不继承屋顶木材/陶瓦标签；正脊是本例几何分类，不是独立构件或实地证据'}]
    model['topologySources']=[
        {'id':'S01','title':'IFC 4.3.2.0 IfcConnectionTypeEnum','url':'https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcConnectionTypeEnum.htm','locator':'6.1.2.7.1–.2','use':'连接部位词汇','checked':'2026-10-26'},
        {'id':'S03','title':'OGC 06-103r4 Simple feature access Part 1 v1.2.1','url':'https://docs.ogc.org/is/06-103r4/06-103r4.pdf','locator':'6.1.6.1; 6.1.10–6.1.13; 6.1.15.1–.3','use':'边界/内部/交集；多面片公共曲线，不提供本例墙柱或脊沟算法','checked':'2026-10-26'},
        {'id':'S07','title':'IFC4 FINAL IfcConnectionCurveGeometry','url':'https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcgeometricconstraintresource/lexical/ifcconnectioncurvegeometry.htm','locator':'8.7.3.1 definition / attributes','use':'关联曲线几何的表达参考；本研究不声称完整IFC映射或物理连接成立','checked':'2026-10-26'}]
    report={'date':'2026-10-26','status':'local_geometry_verified_database_status_separate','baselineSha256':sha(BASE),
            'scriptSha256':sha(Path(__file__)),'wallRuleScriptSha256':sha(HERE/'墙轴交接核验.py'),
            'wallPairs':wp,'wallColumnPairs':cp,'roofPair':shared,'boundaryChecks':checks(),
            'newNodeIds':['RS01','RS02'],'addedRelationshipIds':[e['id'] for e in added],
            'counts':{'wallPairs':len(wp),'wallJoins':sum(e['type']=='AXIS_JOINS' for e in added),'wallColumnPairs':len(cp),
                      'envelopeIntersections':sum(e['type']=='ENVELOPE_INTERSECTS' for e in added),'sharedBoundaries':1,'newRelationships':len(added)},
            'scope':'single synthetic case; exact scoped geometry, no survey precision / physical connection / structural inference claims'}
    assert report['counts']=={'wallPairs':45,'wallJoins':12,'wallColumnPairs':40,'envelopeIntersections':4,'sharedBoundaries':1,'newRelationships':25}
    assert {(p['source'],p['target']) for p in cp if p['kind']=='intersection'}=={('W01','C01'),('W08','C01'),('W02','C04'),('W09','C04')}
    assert math.isclose(sum(n['properties']['areaM2'] for n in model['nodes'] if 'RoofSurface' in n['labels']),model['analysisResults'][1]['value'],abs_tol=1e-4)
    assert len({n['id'] for n in model['nodes']})==len(model['nodes'])==42
    assert len({e['id'] for e in model['relationships']})==len(model['relationships'])==191
    return model,report

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['build','verify']);mode=p.parse_args().mode
    model,report=build();path=CASE/'案例模型.json'
    if mode=='build':
        current=json.loads(path.read_text())
        assert sha(path)==sha(BASE) or current==model,'Unexpected model change; do not overwrite'
        save(path,model)
    else:
        assert json.loads(path.read_text())==model,'Current model differs from reproducible extension'
    report['sourceModelSha256']=sha(path);save(HERE/'拓扑关系核验.json',report)
    print(json.dumps({'mode':mode,'nodes':len(model['nodes']),'relationships':len(model['relationships']),**report['counts'],'boundaryChecks':len(report['boundaryChecks'])},ensure_ascii=False))

if __name__=='__main__':main()
