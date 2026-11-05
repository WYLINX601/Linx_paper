#!/usr/bin/env python3
"""WJ-01: exact planar intersections of straight wall axes in a declared common level.
Reads the frozen synthetic model; writes a candidate report only. No database writes.
Uses rational decimals, not a survey snapping tolerance or a general solid modeller.
"""
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
import collections
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
CASE = HERE.parent
RULE_ID = 'WJ-01-v1'


def vec(p):
    return tuple(F(str(v)) for v in p)


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def cross(a, b):
    return a[0]*b[1]-a[1]*b[0]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def at(t):
    return 'ATSTART' if t == 0 else 'ATEND' if t == 1 else 'ATPATH'


def intersect(a, b, c, d):
    """Exact segment intersection: none, a point, an overlap, or invalid input."""
    a, b, c, d = map(vec, (a, b, c, d))
    r, s = sub(b, a), sub(d, c)
    if dot(r, r) == 0 or dot(s, s) == 0:
        return {'kind': 'invalid_zero_length'}
    den, delta = cross(r, s), sub(c, a)
    if den:
        t, u = cross(delta, s)/den, cross(delta, r)/den
        if not (0 <= t <= 1 and 0 <= u <= 1):
            return {'kind': 'disjoint'}
    else:
        if cross(delta, r):
            return {'kind': 'disjoint'}
        tc, td = dot(sub(c, a), r)/dot(r, r), dot(sub(d, a), r)/dot(r, r)
        lo, hi = max(F(0), min(tc, td)), min(F(1), max(tc, td))
        if lo > hi:
            return {'kind': 'disjoint'}
        if lo < hi:
            return {'kind': 'overlap_review'}
        t = lo
        point = tuple(a[i]+t*r[i] for i in (0, 1))
        u = dot(sub(point, c), s)/dot(s, s)
    point = tuple(a[i]+t*r[i] for i in (0, 1))
    cosine = min(1., max(0., abs(float(dot(r, s)))/math.sqrt(float(dot(r, r)*dot(s, s)))))
    angle = round(math.degrees(math.acos(cosine)), 8)
    positions = [at(t), at(u)]
    if positions == ['ATPATH', 'ATPATH']:
        form = '中段—中段交叉'
    elif 'ATPATH' in positions:
        form = '端—中段交接'
    else:
        form = '端—端共线延续' if cross(r, s) == 0 else '端—端转角'
    return {'kind': 'point', 'atSource': positions[0], 'atTarget': positions[1],
            'junctionXY': [float(v) for v in point], 'axisAngleDeg': angle,
            'derivedForm': form}


def assess(a, b, c, d, level_a, level_b):
    result = intersect(a, b, c, d)
    if result['kind'] != 'point':
        return result
    if level_a is None or level_b is None:
        return {**result, 'kind': 'level_unknown_review'}
    if level_a != level_b:
        return {**result, 'kind': 'different_levels_projection_only'}
    return result


def check_rules():
    fixtures = [
        ('直角端接', [(0,0),(1,0),(1,0),(1,1)], 0,0, 'point','ATEND','ATSTART'),
        ('T形端中接', [(0,0),(2,0),(1,0),(1,1)], 0,0, 'point','ATPATH','ATSTART'),
        ('X形中中接', [(0,0),(2,0),(1,-1),(1,1)], 0,0, 'point','ATPATH','ATPATH'),
        ('共线端接', [(0,0),(1,0),(1,0),(2,0)], 0,0, 'point','ATEND','ATSTART'),
        ('斜向端接', [(0,0),(1,0),(1,0),(2,1)], 0,0, 'point','ATEND','ATSTART'),
        ('平行分离', [(0,0),(1,0),(0,1),(1,1)], 0,0, 'disjoint',None,None),
        ('同线分离', [(0,0),(1,0),(2,0),(3,0)], 0,0, 'disjoint',None,None),
        ('极小缝仍不吸附', [(0,0),(1,0),(1.0001,0),(2,0)], 0,0, 'disjoint',None,None),
        ('共线重叠待审', [(0,0),(2,0),(1,0),(3,0)], 0,0, 'overlap_review',None,None),
        ('同轴重复待审', [(0,0),(2,0),(2,0),(0,0)], 0,0, 'overlap_review',None,None),
        ('零长度无效', [(0,0),(0,0),(0,0),(1,0)], 0,0, 'invalid_zero_length',None,None),
        ('异层投影不建边', [(0,0),(2,0),(1,-1),(1,1)], 0,3, 'different_levels_projection_only','ATPATH','ATPATH'),
        ('层位未知待审', [(0,0),(2,0),(1,-1),(1,1)], 0,None, 'level_unknown_review','ATPATH','ATPATH'),
    ]
    checks=[]
    for name, points, la, lb, kind, pa, pb in fixtures:
        result=assess(*points, la, lb)
        assert result['kind'] == kind, (name,result)
        if pa:
            assert (result['atSource'],result['atTarget']) == (pa,pb), (name,result)
        checks.append({'name':name,'passed':True,'result':result})
    original=assess((0,0),(2,0),(1,0),(1,1),0,0)
    swapped=assess((1,0),(1,1),(0,0),(2,0),0,0)
    assert original['junctionXY']==swapped['junctionXY']
    assert original['atSource']==swapped['atTarget'] and original['atTarget']==swapped['atSource']
    checks.append({'name':'交换两墙后部位属性同步互换','passed':True})
    return checks


def main():
    raw=(CASE/'案例模型.json').read_bytes()
    model=json.loads(raw)
    # This common-level assumption is stated in V01 meta; it is not inferred from XY.
    assert model['meta']['caseId']=='V01' and '地坪Z=0' in model['meta']['coordinateSystem']
    walls=sorted([n for n in model['nodes'] if 'Wall' in n['labels']],key=lambda n:n['id'])
    pairs=[];edges=[]
    for a,b in combinations(walls,2):
        ga,gb=a['geometry'],b['geometry']
        assert ga['kind']==gb['kind']=='wall' and len(ga['a'])==len(ga['b'])==len(gb['a'])==len(gb['b'])==2
        result=assess(ga['a'],ga['b'],gb['a'],gb['b'],0,0)
        pairs.append({'source':a['id'],'target':b['id'],**result})
        if result['kind']=='point':
            edges.append({'id':f"WJ-{a['id']}-{b['id']}",'source':a['id'],'target':b['id'],
                          'type':'AXIS_JOINS','status':'synthetic_geometry_derived','evidence':['EV01'],
                          'properties':{k:result[k] for k in ('atSource','atTarget','junctionXY')} | {'ruleId':RULE_ID}})
    expected={('W01','W03'),('W01','W06'),('W01','W08'),('W02','W03'),('W02','W07'),('W02','W09'),
              ('W03','W04'),('W03','W05'),('W04','W06'),('W05','W07'),('W08','W10'),('W09','W10')}
    assert {(e['source'],e['target']) for e in edges}==expected
    tests=check_rules()
    report={'status':'candidate_design_verified_not_imported','date':'2026-10-26','caseId':'V01',
            'sourceModelSha256':hashlib.sha256(raw).hexdigest(),
            'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'rule':{'id':RULE_ID,'representation':'straight_wall_plan_axis','coordinateSystem':model['meta']['coordinateSystem'],
                    'levelBasis':'V01 common ground datum Z=0; only this synthetic scope has been checked',
                    'numericalMethod':'exact Fraction(str(decimal)); no snapping','surveyToleranceM':None,
                    'semantics':'symmetric, irreflexive, nontransitive; store smaller ID as source',
                    'scope':'single-point intersection of straight plan axes at a declared common level; no claim of solid contact or structural connection'},
            'wallCount':len(walls),'pairCount':len(pairs),'proposedEdgeCount':len(edges),
            'pairOutcomeCounts':dict(collections.Counter(p['kind'] for p in pairs)),
            'derivedFormCounts':dict(collections.Counter(p['derivedForm'] for p in pairs if p['kind']=='point')),
            'candidateRelationships':edges,'pairAssessments':pairs,'boundaryChecks':tests,
            'verificationBoundary':'14 rule fixtures and exact expected pair set checked; no field data, tolerance calibration, 3D contact verification, or database writes'}
    target=HERE/'墙轴交接核验.json'
    tmp=target.with_suffix('.json.tmp');tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');tmp.replace(target)
    print(json.dumps({k:report[k] for k in ['status','wallCount','pairCount','proposedEdgeCount','pairOutcomeCounts','derivedFormCounts']},ensure_ascii=False))
    print('boundaryChecks',len(tests),'passed; source unchanged:',hashlib.sha256((CASE/'案例模型.json').read_bytes()).hexdigest()==report['sourceModelSha256'])


if __name__=='__main__':
    main()
