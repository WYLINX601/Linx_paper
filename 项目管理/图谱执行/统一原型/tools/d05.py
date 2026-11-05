"""D05 同一 V01 的限定合成扩展。无文件/数据库访问；结果逐次重算。"""
import math
import copy
from shapely.geometry import Polygon, Point, box

NEW_IDS = ('B03', 'CG01', 'ST01', 'TP01')
EXCLUDED = ['D02-internal-frame', 'D07-history', 'D08-perception']


def _need(ok, message):
    if not ok:
        raise ValueError(message)


def _finite(value):
    if isinstance(value, float):
        _need(math.isfinite(value), 'non-finite number')
    elif isinstance(value, dict):
        for x in value.values():
            _finite(x)
    elif isinstance(value, (list, tuple)):
        for x in value:
            _finite(x)


def _poly(flat):
    _need(isinstance(flat, list) and len(flat) >= 6 and len(flat) % 2 == 0, 'polygon coordinates')
    p = Polygon(list(zip(flat[::2], flat[1::2])))
    _need(p.is_valid and p.area > 0, 'invalid polygon')
    return p


def _index(model):
    return {n['id']: n for n in model['nodes']}


def _interval_union(ranges):
    if not ranges:
        return []
    merged = []
    for a, b in sorted(ranges):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def _length(ranges):
    return sum(b-a for a, b in _interval_union(ranges))


def _eq(a, b):
    return math.isclose(a, b, abs_tol=1e-8, rel_tol=1e-9)


def _edge(model, suffix, kind, source, target, **properties):
    model['relationships'].append(dict(id='D05-'+suffix, type=kind, source=source,
        target=target, properties=properties, status='synthetic_assignment', evidence=['EV01']))


def extend(model):
    """原位补充；不升级版本、不补来源边、不覆盖既有节点或几何。"""
    _need(isinstance(model, dict), 'model must be dict')
    v = model['modelVersion']
    n = _index(model)
    if 'D05' in model.get('analysisContract', {}):
        validate(model)
        return model
    _need(not any(i in n for i in NEW_IDS), 'D05 ID collision')
    _need(not any(e['id'].startswith('D05-') for e in model['relationships']), 'D05 edge collision')
    for i in ('B01', 'B02', 'U01', 'W10', 'S05', 'S06', 'I05', 'DATUM01', 'EV01'):
        _need(i in n, 'missing prerequisite '+i)
    shared = {k: n['B02']['properties'][k] for k in ('unit', 'scenario', 'coordinateFrame',
        'measurementBoundaryBasis', 'heightBasis', 'precisionMeaning')}
    common = dict(caseId='V01', recordStatus='synthetic_assignment', geometryVersion=v)
    def add(i, name, cls, labels, props, geometry):
        model['nodes'].append(dict(id=i, name=name, **{'class': cls}, labels=labels,
            properties={**common, **props}, geometry=geometry, evidence=['EV01']))
    lo, hi = [0, -12, 0], [9.6, -8.8, 4.8]
    add('B03', '人工邻宅（不同物理身份，非实测）', 'Building', ['Building', 'Zone'],
        {**shared, 'geometryActive': True, 'role': 'neighbor-dwelling',
         'identityBasis': '人工设定的另一住居身份；不是B01副本，不属于U01侧房，不复制院落或构架',
         'widthM': hi[0]-lo[0], 'depthM': hi[1]-lo[1], 'widthDirection': '+X', 'depthDirection': '+Y',
         'groundZM': 0, 'eaveZM': 3, 'ridgeZM': 4.8,
         'groundPointXYZ': [4.8, -8.8, 0], 'eavePointXYZ': [4.8, -8.8, 3],
         'ridgePointXYZ': [4.8, -10.4, 4.8], 'footprintShape': 'rectangle',
         'footprintXY': [lo[0], lo[1], hi[0], lo[1], hi[0], hi[1], lo[0], hi[1]]},
        dict(kind='box', min=lo, max=hi, interpretation='简化外包参照盒，非完整实体'))
    coords = dict(unit=shared['unit'], coordinateFrame=shared['coordinateFrame'], scenario=shared['scenario'])
    add('CG01', '当前合成建筑组二维分析集合', 'AnalysisCollection', ['AnalysisCollection'],
        {**coords, 'boundaryVersion': v, 'inclusionReason': '比较同宅主屋侧房及街对面人工邻宅',
         'coverage': '仅声明二维窗口内三栋选定建筑；非完整三维组团，非地方组团分类；三栋不等于三个独立宅院'},
        dict(kind='analysis_window_2d', min=[-1, -13], max=[15, 8]))
    add('ST01', '代表性完整直线合成街段', 'SpatialReference', ['SpatialReference', 'StreetSegment'],
        {**coords, 'surfaceSource': 'synthetic_assignment', 'surfaceState': 'known',
         'boundaryVersion': v, 'coverage': 'complete-representative-straight-segment',
         'widthMeaning': '路面横向范围宽，不是通行净宽；边界间距另报',
         'surfaceMeaning': '合成平整路面；不证明无障碍或不存在其他障碍'},
        dict(kind='street_reference', centerline=[[0, -6.8], [9.6, -6.8]],
             surfaceXY=[0, -8.8, 9.6, -8.8, 9.6, -4.92, 0, -4.92], surfaceZM=0))
    add('TP01', '人工地面样点剖面（非屋顶）', 'GeometryRepresentation', ['GeometryRepresentation', 'GroundProfile'],
        {**coords, 'groundSource': 'synthetic_assignment', 'groundState': 'known',
         'coverage': '仅两个人工地面样点之间的直线参照，不是实测坡面或基础构造',
         'interpretation': '独立人工赋值，不由B02地坪反推真实坡面'},
        dict(kind='ground_profile', pointsXYZ=[[9.6, -6.8, 0], [10, -3, 3]]))
    for i, role, order in [('B01', 'same-U01-main', 1), ('B02', 'same-U01-annex', 2), ('B03', 'neighbor-dwelling', 3)]:
        _edge(model, 'MEM-'+i, 'HAS_ANALYSIS_MEMBER', 'CG01', i, ordinal=order, role=role, boundaryVersion=v)
    for i in NEW_IDS:
        _edge(model, 'DATUM-'+i, 'USES_DATUM', i, 'DATUM01', frameVersion=v,
              fields=['geometry', 'groundZM', 'eaveZM', 'ridgeZM'] if i == 'B03' else ['geometry'])
    _edge(model, 'LEFT', 'STREET_BOUNDARY_PARTICIPANT', 'ST01', 'W10', side='left', role='wall-side',
          geometryVersion=v, segments=[{'rangeM': [0, 4], 'state': 'entity', 'basis': 'W10'},
          {'rangeM': [4, 5.6], 'state': 'opening', 'basis': 'I05'},
          {'rangeM': [5.6, 9.6], 'state': 'entity', 'basis': 'W10'}])
    _edge(model, 'RIGHT', 'STREET_BOUNDARY_PARTICIPANT', 'ST01', 'B03', side='right', role='building-side',
          geometryVersion=v, segments=[{'rangeM': [0, 9.6], 'state': 'entity', 'basis': 'B03'}])
    _edge(model, 'GROUND', 'REFERENCES_GROUND', 'B02', 'TP01', pointIndex=1,
          objectPointField='groundPointXYZ', geometryVersion=v)
    model.setdefault('analysisContract', {})['D05'] = dict(version=v, collectionId='CG01', streetId='ST01',
        groundProfileId='TP01', datumId='DATUM01', pairs=[['B01', 'B02'], ['B01', 'B03']],
        streetSectionZM=1.0,
        pairReason='同宅主侧房及主屋与街对面邻宅，非全量两两比较',
        sequenceOrder='center-X-ascending-ties', sequenceMode='center-X-projection',
        excluded=EXCLUDED[:], applicability='限定V01合成直线街段与人工两点地表，不是任意街段算法')
    vocabulary = model.setdefault('relationVocabulary', [])
    for kind, definition in [('HAS_ANALYSIS_MEMBER', '二维分析集合→既有建筑，ordinal和role不表示独立宅院数'),
            ('STREET_BOUNDARY_PARTICIPANT', '街段→墙或建筑侧，局部里程与明确开口/未知分开'),
            ('REFERENCES_GROUND', '对象已声明地面点→独立人工地面剖面样点，不推构造或因果')]:
        if not any(e['type'] == kind for e in vocabulary):
            vocabulary.append(dict(type=kind, definition=definition, origin='research-extension'))
    validate(model)
    return model


def _validate(model):
    _finite(model)
    _need(isinstance(model['modelVersion'], str) and bool(model['modelVersion']), 'modelVersion')
    nodes, edges = model['nodes'], model['relationships']
    _need(isinstance(nodes, list) and isinstance(edges, list), 'node/edge lists')
    n = _index(model)
    _need(len(n) == len(nodes), 'duplicate node IDs')
    _need(len({e['id'] for e in edges}) == len(edges), 'duplicate edge IDs')
    for e in edges:
        _need(e['source'] in n and e['target'] in n, 'dangling endpoint')
    c = model['analysisContract']['D05']
    v = model['modelVersion']
    _need(c['version'] == v and c['excluded'] == EXCLUDED, 'contract version/suspended scope')
    _need((c['collectionId'], c['streetId'], c['datumId']) == ('CG01', 'ST01', 'DATUM01'), 'contract targets')
    _need(c['groundProfileId'] in (None, 'TP01'), 'ground target')
    _need(c['pairs'] == [['B01', 'B02'], ['B01', 'B03']], 'explicit pairs')
    _need(type(c['streetSectionZM']) in (int, float) and c['streetSectionZM'] == 1.0, 'only declared z=1 section supported')
    _need(c['sequenceMode'] == 'center-X-projection' and c['sequenceOrder'] in
          ('center-X-ascending-ties', 'center-X-descending-ties'), 'sequence rule')
    for i in NEW_IDS:
        if i == 'TP01' and i not in n:
            continue
        a = n[i]
        _need(all(k in a for k in ('id', 'name', 'class', 'labels', 'properties', 'geometry', 'evidence')), 'node schema')
        _need(a['evidence'] == ['EV01'] and a['properties']['recordStatus'] == 'synthetic_assignment'
              and a['properties']['caseId'] == 'V01', 'synthetic node identity')
    datum = n['DATUM01']['properties']
    _need(datum['unit'] == 'm' and datum['frameVersion'] == v, 'datum unit/version')
    for i in ('B01', 'B02', 'B03', 'CG01', 'ST01', 'S05', 'S06') + (('TP01',) if 'TP01' in n else ()):
        p = n[i]['properties']
        _need(p['unit'] == 'm' and p['coordinateFrame'] == datum['frame'] and
              p['scenario'] == n['B01']['properties']['scenario'] and p['geometryVersion'] == v, 'incompatible unit/frame/scenario/version '+i)
        if i not in ('CG01', 'ST01', 'TP01'):
            _need(p.get('geometryActive') is True, 'inactive geometry')
        ds = [e for e in edges if e['source'] == i and e['type'] == 'USES_DATUM']
        _need(len(ds) == 1 and ds[0]['target'] == 'DATUM01' and ds[0]['properties']['frameVersion'] == v, 'datum link '+i)
    _need(n['CG01']['class'] == 'AnalysisCollection' and not {'Zone', 'Site'} & set(n['CG01']['labels']), 'collection is not BOT Zone')
    for i, cls, label in [('B03', 'Building', 'Zone'), ('ST01', 'SpatialReference', 'StreetSegment')]:
        _need(n[i]['class'] == cls and label in n[i]['labels'], 'new node class')
    _need(not any(k in n['B03']['properties'] for k in ('legacyUid', 'sourceUid', 'd03GroundEligibility')), 'copied B02 facts')
    _need(n['B03']['properties']['role'] == 'neighbor-dwelling', 'neighbor role')
    for i in ('W10', 'I05'):
        _need(n[i]['properties']['geometryVersion'] == v, 'participant version')
    own = [e for e in edges if e['id'].startswith('D05-')]
    expected_edges = {'D05-MEM-'+i for i in ('B01', 'B02', 'B03')}
    expected_edges |= {'D05-DATUM-'+i for i in NEW_IDS if i in n}
    expected_edges |= {'D05-LEFT', 'D05-RIGHT'}
    if 'TP01' in n:
        expected_edges.add('D05-GROUND')
    _need({e['id'] for e in own} == expected_edges, 'unexpected/missing D05 relationship')
    permitted = {'HAS_ANALYSIS_MEMBER', 'STREET_BOUNDARY_PARTICIPANT', 'USES_DATUM', 'REFERENCES_GROUND'}
    for e in own:
        _need(e['type'] in permitted and e['status'] == 'synthetic_assignment' and e['evidence'] == ['EV01'], 'D05 edge schema/scope')
        _need(isinstance(e['properties'], dict), 'edge properties')
    members = [e for e in edges if e['source'] == 'CG01' and e['type'] == 'HAS_ANALYSIS_MEMBER']
    _need(len(members) == 3 and {e['target'] for e in members} == {'B01', 'B02', 'B03'}, 'member uniqueness/identity')
    _need({e['properties']['ordinal'] for e in members} == {1, 2, 3}, 'member ordinals')
    _need(all(type(e['properties']['ordinal']) is int for e in members), 'integer ordinals')
    roles = {'B01': 'same-U01-main', 'B02': 'same-U01-annex', 'B03': 'neighbor-dwelling'}
    for e in members:
        _need(e['properties']['role'] == roles[e['target']] and e['properties']['boundaryVersion'] == v, 'member role/version')
    for i in ('B01', 'B02'):
        _need(any(e['type'] == 'BOT_HAS_BUILDING' and e['source'] == 'U01' and e['target'] == i for e in edges), 'same dwelling membership')
    _need(not any(e['type'] == 'BOT_HAS_BUILDING' and e['source'] == 'U01' and e['target'] == 'B03' for e in edges), 'neighbor not annex')
    cg = n['CG01']; g = cg['geometry']; p = cg['properties']
    _need(g['kind'] == 'analysis_window_2d' and p['boundaryVersion'] == v and bool(p['coverage']) and bool(p['inclusionReason']), 'window metadata')
    _need(all(g['min'][j] < g['max'][j] for j in (0, 1)), 'window extents')
    window = box(*g['min'], *g['max'])
    for i in ('B01', 'B02', 'B03'):
        a = n[i]; g = a['geometry']; p = a['properties']
        _need(g['kind'] == 'box' and len(g['min']) == len(g['max']) == 3 and all(g['min'][j] < g['max'][j] for j in range(3)), 'building reference box')
        poly = _poly(p['footprintXY'])
        _need(poly.equals(box(*g['min'][:2], *g['max'][:2])), 'footprint vs reference geometry')
        _need(window.covers(poly), 'member outside window')
        axes = {'+X': 0, '+Y': 1}
        wi, di = axes[p['widthDirection']], axes[p['depthDirection']]
        _need(wi != di and _eq(p['widthM'], g['max'][wi]-g['min'][wi]) and
              _eq(p['depthM'], g['max'][di]-g['min'][di]), 'dimensions vs box')
        for field, point in [('groundZM', 'groundPointXYZ'), ('eaveZM', 'eavePointXYZ'), ('ridgeZM', 'ridgePointXYZ')]:
            _need(len(p[point]) == 3 and _eq(p[field], p[point][2]), 'height point mismatch')
        _need(_eq(p['groundZM'], g['min'][2]) and _eq(p['ridgeZM'], g['max'][2]) and
              p['groundZM'] <= p['eaveZM'] <= p['ridgeZM'], 'vertical reference')
        _need(bool(p['measurementBoundaryBasis']) and bool(p['heightBasis']), 'measurement definition')
    st = n['ST01']; sg = st['geometry']; sp = st['properties']
    _need(sp['boundaryVersion'] == v and sp['coverage'] == 'complete-representative-straight-segment', 'street version/coverage')
    _need(sg['kind'] == 'street_reference' and sg['centerline'] == [[0, -6.8], [9.6, -6.8]], 'only stated eastward line supported')
    wall, gate = n['W10']['geometry'], n['I05']['geometry']
    _need(wall['kind'] == 'wall' and wall['a'] == [0, -4.8] and wall['b'] == [9.6, -4.8], 'straight wall prerequisite')
    _need(wall['heightMode'] == 'constant' and wall['height'] > 0 and wall['thickness'] > 0, 'wall section')
    left = wall['a'][1]-wall['thickness']/2
    right = n['B03']['geometry']['max'][1]
    _need(left > -6.8 > right, 'street sides')
    _need(_poly(sg['surfaceXY']).equals(box(0, right, 9.6, left)), 'pavement bounds vs participants')
    _need(sp['surfaceState'] in ('known', 'unknown') and sp['surfaceSource'] in ('synthetic_assignment', 'unknown'), 'surface provenance')
    _need(sg['surfaceZM'] == 0, 'synthetic flat pavement z0')
    _need(gate['a'][1] == gate['b'][1] == wall['a'][1] and 0 <= gate['a'][0] < gate['b'][0] <= 9.6, 'gate projection')
    _need(gate['z'][0] <= c['streetSectionZM'] < gate['z'][1] <= wall['height'], 'opening at section')
    _need(_eq(n['I05']['properties']['sillZ'], gate['z'][0]) and
          _eq(n['I05']['properties']['headZ'], gate['z'][1]) and
          _eq(n['I05']['properties']['widthM'], gate['b'][0]-gate['a'][0]), 'gate parameters vs geometry')
    _need(any(e['source'] == 'I05' and e['target'] == 'W10' and e['type'] == 'INTERFACE_OF'
              and e['properties'].get('role') == 'opening-host' for e in edges), 'gate host')
    participants = [e for e in edges if e['source'] == 'ST01' and e['type'] == 'STREET_BOUNDARY_PARTICIPANT']
    _need(len(participants) == 2 and {e['properties']['side'] for e in participants} == {'left', 'right'}, 'unique street sides')
    for e in participants:
        p = e['properties']; side = p['side']; target = 'W10' if side == 'left' else 'B03'
        _need(e['target'] == target and p['role'] == ('wall-side' if side == 'left' else 'building-side') and p['geometryVersion'] == v, 'participant role/version')
        segs = p['segments']; ranges = []
        for s in segs:
            a, b = s['rangeM']; _need(0 <= a < b <= 9.6, 'local range')
            _need(s['state'] in ('entity', 'opening', 'unknown'), 'unknown is not open')
            _need(s['basis'] == ('I05' if s['state'] == 'opening' else 'unknown' if s['state'] == 'unknown' else target), 'segment evidence')
            ranges.append([a, b])
        _need(_interval_union(ranges) == [[0, 9.6]], 'uncovered segment must be explicit unknown')
        groups = {s: [x['rangeM'] for x in segs if x['state'] == s] for s in ('entity', 'opening', 'unknown')}
        _need(_eq(sum(_length(x) for x in groups.values()), 9.6), 'conflicting interval states')
        expected = [[gate['a'][0], gate['b'][0]]] if side == 'left' else []
        _need(_interval_union(groups['opening']) == expected, 'omitted/false opening')
    refs = [e for e in edges if e['type'] == 'REFERENCES_GROUND' and e['target'] == 'TP01']
    if 'TP01' in n:
        tp = n['TP01']; p = tp['properties']
        _need(tp['class'] == 'GeometryRepresentation' and 'GroundProfile' in tp['labels'], 'ground representation')
        _need(p['groundState'] in ('known', 'unknown') and p['groundSource'] in ('synthetic_assignment', 'unknown'), 'ground provenance')
        pts = tp['geometry']['pointsXYZ']
        _need(tp['geometry']['kind'] == 'ground_profile' and len(pts) == 2 and all(len(x) == 3 for x in pts), 'ground sample structure')
        _need(math.dist(pts[0][:2], pts[1][:2]) > 0, 'positive horizontal distance')
        _need(len(refs) == 1 and refs[0]['source'] == 'B02' and refs[0]['properties']['pointIndex'] == 1 and
              refs[0]['properties']['objectPointField'] == 'groundPointXYZ' and refs[0]['properties']['geometryVersion'] == v and
              pts[1] == n['B02']['properties']['groundPointXYZ'], 'ground reference point/version')
    else:
        _need(not refs, 'missing ground reference endpoint')
    return True


def validate(model):
    """合法返回True；结构不合规统一ValueError。允许显式未知/缺失地表。"""
    try:
        return _validate(model)
    except ValueError:
        raise
    except (KeyError, TypeError, IndexError, AttributeError, OverflowError) as exc:
        raise ValueError('invalid D05 structure: '+str(exc)) from exc


def analyze(model):
    validate(model)
    n = _index(model); c = model['analysisContract']['D05']; edges = model['relationships']
    cg = n[c['collectionId']]; g = cg['geometry']; window = box(*g['min'], *g['max'])
    members = sorted([e for e in edges if e['source'] == cg['id'] and e['type'] == 'HAS_ANALYSIS_MEMBER'],
                     key=lambda e: (e['properties']['ordinal'], e['target']))
    t1 = dict(status='synthetic', boundary=cg['geometry'], boundaryVersion=cg['properties']['boundaryVersion'],
              unit=cg['properties']['unit'], coordinateFrame=cg['properties']['coordinateFrame'], datumId=c['datumId'],
              coverage=cg['properties']['coverage'], members=[dict(id=e['target'], **e['properties'],
              boundaryState='touching' if window.boundary.intersects(_poly(n[e['target']]['properties']['footprintXY'])) else 'inside') for e in members],
              buildingCount=len(members), independentDwellingCount='not-established', sameDwelling=['B01', 'B02'])
    pairs = []
    for a, b in c['pairs']:
        pa, pb = n[a]['properties'], n[b]['properties']; ga, gb = n[a]['geometry'], n[b]['geometry']
        ca, cb = _poly(pa['footprintXY']).centroid, _poly(pb['footprintXY']).centroid
        axis = {'+X': 0, '+Y': 90}
        angle = abs(axis[pa['widthDirection']]-axis[pb['widthDirection']]) % 180
        pairs.append(dict(pair=[a, b], buildingClearance=dict(status='refused', reason='axis vs outer boundary incomparable; reference boxes are not physical solids'),
            referenceBoxDistance2DM=box(*ga['min'][:2], *ga['max'][:2]).distance(box(*gb['min'][:2], *gb['max'][:2])),
            distanceMeaning='简化外包参照盒二维距离，不是建筑净距或实体接触',
            centerDisplacementXYM=[cb.x-ca.x, cb.y-ca.y], displacementReference='declared footprint centroid; east/north',
            widthAxisAngleDeg=min(angle, 180-angle), directionMeaning='无向宽度轴，非正立面朝向',
            groundDifferenceM=pb['groundZM']-pa['groundZM'], eaveDifferenceM=pb['eaveZM']-pa['eaveZM'],
            ridgeDifferenceM=pb['ridgeZM']-pa['ridgeZM'], heightReference='second minus first; DATUM01 common elevation'))
    st = n['ST01']; sg = st['geometry']; sides = {}
    for e in sorted([e for e in edges if e['source'] == 'ST01' and e['type'] == 'STREET_BOUNDARY_PARTICIPANT'], key=lambda x: x['properties']['side']):
        p = e['properties']; side = p['side']; target = e['target']; g = n[target]['geometry']
        ranges = {s: _interval_union([x['rangeM'] for x in p['segments'] if x['state'] == s]) for s in ('entity', 'opening', 'unknown')}
        top = g['height'] if side == 'left' else n[target]['properties']['eaveZM']
        sides[side] = dict(participant=target, role=p['role'], ranges=ranges,
            knownEntityLengthM=_length(ranges['entity']), knownEntityProportion=_length(ranges['entity'])/9.6,
            completeEntityProportion=None if ranges['unknown'] else _length(ranges['entity'])/9.6,
            boundaryYM=g['a'][1]-g['thickness']/2 if side == 'left' else g['max'][1],
            sectionVerticalRangeZM=[0, top], heightAbovePavementM=top-sg['surfaceZM'],
            heightMeaning='W10恒高实体表面' if side == 'left' else '仅邻宅北侧至檐断面，不是另造墙；不使用屋脊')
    surface = _poly(sg['surfaceXY']); bounds = surface.bounds
    t3 = dict(status='synthetic-straight-only', centerline=sg['centerline'], chainageM=[0, 9.6], sides=sides,
              analysisSectionZM=c['streetSectionZM'],
              pavementWidthM=bounds[3]-bounds[1], boundarySeparationM=sides['left']['boundaryYM']-sides['right']['boundaryYM'],
              widthScope='路面宽与边界间距单独定义；数值在此合成设置相同，不是通行净宽或无障碍验证', pavementSource=st['properties']['surfaceSource'])
    t4 = dict(status='unknown', reason='ground profile absent/unavailable', thresholdToSamePointPavement=dict(status='unknown', reason='not computed'))
    tp = n.get(c['groundProfileId']) if c['groundProfileId'] else None
    if tp and tp['properties']['groundState'] == 'known' and tp['properties']['groundSource'] == 'synthetic_assignment':
        pts = tp['geometry']['pointsXYZ']; run = math.dist(pts[0][:2], pts[1][:2]); rise = pts[1][2]-pts[0][2]
        t4.update(status='synthetic-ground-only', reason='independent synthetic ground assignment', horizontalDistanceM=run,
                  elevationDifferenceM=rise, slopeRatio=rise/run, pointsXYZ=pts, datumId='DATUM01',
                  B02ReferencePointDifferenceM=pts[1][2]-n['B02']['properties']['groundPointXYZ'][2])
    gate = n['I05']['geometry']; mid = [(gate['a'][j]+gate['b'][j])/2 for j in (0, 1)]
    eligible = surface.covers(Point(mid)) and st['properties']['surfaceState'] == 'known' and st['properties']['surfaceSource'] == 'synthetic_assignment'
    t4['thresholdToSamePointPavement'] = dict(status='synthetic' if eligible else 'unknown', pointXY=mid,
        differenceM=gate['z'][0]-sg['surfaceZM'] if eligible else None,
        reason='same-point surface supported' if eligible else 'I05轴线点不在路面范围或路面来源不可用；不投影替代同点')
    seq = [dict(id=e['target'], centerXM=_poly(n[e['target']]['properties']['footprintXY']).centroid.x,
                groundZM=n[e['target']]['properties']['groundZM'], eaveZM=n[e['target']]['properties']['eaveZM'],
                ridgeZM=n[e['target']]['properties']['ridgeZM']) for e in members]
    descending = c['sequenceOrder'] == 'center-X-descending-ties'
    seq.sort(key=lambda x: ((-1 if descending else 1)*x['centerXM'], x['id']))
    for s in seq:
        s['tieIds'] = sorted(x['id'] for x in seq if _eq(x['centerXM'], s['centerXM']))
    t5 = dict(mode=c['sequenceMode'], order=c['sequenceOrder'], sequence=seq,
              interpretation='沿X中心投影排序，同中心X并列；共同基准标高，不是自身檐高、剖切或视点可见轮廓')
    t6 = dict(status='present-synthetic-spatial-relations-only', relations=[dict(type=e['type'], source=e['source'], target=e['target'], properties={k: value for k, value in e['properties'].items() if k != 'segments'})
              for e in sorted(edges, key=lambda x: x['id']) if e['id'].startswith('D05-') and e['type'] in ('STREET_BOUNDARY_PARTICIPANT', 'REFERENCES_GROUND')],
              reusedObjects=['U01', 'B01', 'B02', 'W10', 'S05', 'S06', 'I05'],
              waterbody='not-declared', mountain='not-declared', historicalCause='not-analyzed-D07-suspended',
              culturalCause='not-supported', directAccess='not-inferred', adaptationMotive='not-inferred')
    return copy.deepcopy(dict(T01=t1, T02=dict(pairs=pairs), T03=t3, T04=t4, T05=t5, T06=t6))
