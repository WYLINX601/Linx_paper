"""D04 V01 bounded candidate; no IO, database, cache, or provenance publication."""
import math
from copy import deepcopy
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely.errors import ShapelyError

RULE_VERSION = 'D04-candidate-0.1'
FRAME = 'V01-local-XYZ'
SCENARIO = 'V01-T0'
EPS = 1e-9  # numerical roundoff only, NOT a reviewed classification tolerance
SPECS = (
    ('W03', 'B01', 'D04-W03-N', 'north', ('I08', 'I09', 'I10')),
    ('W10', 'U01', 'D04-W10-S', 'south', ('I05',)),
)
ITEMS = ['D04-T01', 'D04-T02', 'D04-T03', 'D04-T04', 'D04-T05', 'D04-T06']


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _finite(value):
    if isinstance(value, float):
        _require(math.isfinite(value), 'non-finite number')
    elif isinstance(value, dict):
        for item in value.values():
            _finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _finite(item)


def _number(value):
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), 'number required')
    _require(math.isfinite(value), 'finite number required')
    return float(value)


def _vector(value, size):
    _require(isinstance(value, (list, tuple)) and len(value) == size, 'coordinate dimension')
    return [_number(x) for x in value]


def _close(a, b):
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    return abs(_number(a) - _number(b)) <= EPS


def _index(model):
    _require(isinstance(model, dict), 'model must be dict')
    _finite(model)
    _require(isinstance(model.get('modelVersion'), str) and model['modelVersion'], 'modelVersion required')
    _require(isinstance(model.get('nodes'), list), 'nodes must be list')
    _require(isinstance(model.get('relationships'), list), 'relationships must be list')
    nodes = {}
    for node in model['nodes']:
        _require(isinstance(node, dict) and isinstance(node.get('id'), str), 'node id required')
        _require(node['id'] not in nodes, 'duplicate node id')
        nodes[node['id']] = node
    ids = set()
    for edge in model['relationships']:
        _require(isinstance(edge, dict) and isinstance(edge.get('id'), str), 'edge id required')
        _require(edge['id'] not in ids, 'duplicate edge id')
        ids.add(edge['id'])
    _require('EV01' in nodes, 'EV01 source missing')
    source = nodes['EV01'].get('properties', {})
    _require(source.get('sourceKind') == 'synthetic_assignment'
             and source.get('isRealWorldEvidence') is False, 'EV01 must remain synthetic, not real evidence')
    _check_metadata(source, model)
    _require(source.get('sourceVersion') == model['modelVersion'], 'incompatible EV01 sourceVersion')
    return nodes


def _metadata(model):
    return dict(geometryVersion=model['modelVersion'], coordinateFrame=FRAME,
                unit='m', scenario=SCENARIO)


def _check_metadata(value, model, required=False):
    _require(isinstance(value, dict), 'properties must be dict')
    for key, expected in _metadata(model).items():
        if required or key in value:
            _require(value.get(key) == expected, 'incompatible ' + key)


def _wall_geometry(node, side):
    g = node['geometry']
    _require(g['kind'] == 'wall', 'wall geometry required')
    a, b = sorted((_vector(g['a'], 2), _vector(g['b'], 2)))
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    _require(length > EPS, 'zero wall axis')
    ux, uy = dx / length, dy / length
    normal = [0.0, 1.0 if side == 'north' else -1.0, 0.0]
    _require(abs(uy) <= EPS, 'bounded V01 candidate requires east-west wall')
    thickness = _number(g['thickness'])
    _require(thickness > 0, 'wall thickness must be positive')
    profile = [_vector(p, 3) for p in g['topProfile']]
    _require(len(profile) >= 2, 'topProfile required')
    top = []
    for x, y, z in profile:
        _require(abs((x - a[0]) * uy - (y - a[1]) * ux) <= EPS, 'top off wall axis')
        _require(z > 0, 'wall top must be above declared ground')
        top.append([(x - a[0]) * ux + (y - a[1]) * uy, z])
    if top[0][0] > top[-1][0]:
        top.reverse()  # reverse the sequence; never sort polygon vertices
    _require(_close(top[0][0], 0) and _close(top[-1][0], length), 'topProfile endpoints')
    _require(all(q[0] > p[0] for p, q in zip(top, top[1:])), 'topProfile order')
    outline = [[0.0, 0.0], [length, 0.0]] + list(reversed(top))
    gross = _polygon(outline)
    projection = dict(mode='orthographic-axis-to-parallel-exterior',
                      axisOriginXYZ=[a[0], a[1], 0.0],
                      exteriorOriginXYZ=[a[0], a[1] + normal[1] * thickness / 2, 0.0],
                      uAxisXYZ=[ux, uy, 0.0], outwardNormalXYZ=normal,
                      offsetM=thickness / 2,
                      offsetBasis='墙轴平行偏移半墙厚；当前0.24/2=0.12m，非轴线即实体外表面',
                      heightBasis='geometry.topProfile逐点墙顶投影；不是RF01檐口')
    return gross, outline, projection


def _polygon(points):
    _require(isinstance(points, list) and len(points) >= 3, 'polygon coordinates missing')
    coords = [_vector(p, 2) for p in points]
    p = Polygon(coords)
    _require(p.is_valid and not p.is_empty and p.area > EPS, 'invalid or nonpositive polygon')
    return p


def _rect(bounds):
    a, b, c, d = _vector(bounds, 4)
    _require(c > a and d > b, 'invalid rectangle bounds [umin,zmin,umax,zmax]')
    return box(a, b, c, d)


def _inside(outer, inner):
    _require(outer.covers(inner), 'region/opening out of gross domain')


def _opening(node, wall, projection):
    g = node['geometry']
    _require(g['kind'] == 'interface', 'opening interface geometry required')
    origin = projection['axisOriginXYZ']
    u = projection['uAxisXYZ']
    values = []
    for xy in (g['a'], g['b']):
        x, y = _vector(xy, 2)
        dx, dy = x - origin[0], y - origin[1]
        _require(abs(dx * u[1] - dy * u[0]) <= EPS, 'opening not on host axis/same plane')
        values.append(dx * u[0] + dy * u[1])
    z0, z1 = _vector(g['z'], 2)
    _require(z1 > z0, 'invalid opening height')
    lo, hi = min(values), max(values)
    _require(hi > lo, 'invalid opening width')
    return box(lo, z0, hi, z1)


def _record_template(model, wall, owner, rid, side, opening_ids):
    gross, outline, projection = _wall_geometry(wall, side)
    width, height = gross.bounds[2], gross.bounds[3]
    common = _metadata(model)
    regions = []
    ranges = [(0.0, width, 'known', '灰泥')] if side == 'north' else [
        (0.0, width / 2, 'known', '灰泥'), (width / 2, width, 'unknown', None)]
    for index, (start, end, state, material) in enumerate(ranges, 1):
        regions.append(dict(common, id=rid + '-surface-' + str(index),
                            rectUZ=[start, 0.0, end, height], layer='surface',
                            state=state, material=material, status='synthetic_assignment',
                            evidence=['EV01'], scopeBasis='明确人工指定的u-z矩形表层条带；不推墙芯'))
    return dict(common, id=rid, ownerId=owner, hostId=wall['id'], exteriorSide=side,
                projection=projection, outlineUZ=outline,
                projectionRangeUZ=list(gross.bounds), openingIds=list(opening_ids),
                surfaceRegions=regions, scopeBasis='仅本墙完整轴长在指定外侧的正投影；不代表全部建筑立面',
                status='synthetic_assignment', evidence=['EV01'], analysisItems=list(ITEMS),
                candidateRuleVersion=RULE_VERSION,
                colorState='conditional-not-enabled', decorationState='unknown')


def extend(model):
    """Add local records and two participant edges in place; preserve old identities."""
    nodes = _index(model)
    # Preflight on an isolated copy: failure must not leave a partially extended input.
    candidate = deepcopy(model)
    cn = {n['id']: n for n in candidate['nodes']}
    for host, owner, rid, side, openings in SPECS:
        _require(host in nodes and owner in nodes, 'facade host/owner missing')
        properties = cn[host].setdefault('properties', {})
        if 'facadeRecords' not in properties:
            properties['facadeRecords'] = [_record_template(candidate, cn[host], owner, rid, side, openings)]
        eid = 'D04-FACADE-' + host
        existing = [e for e in candidate['relationships'] if e['id'] == eid]
        if not existing:
            candidate['relationships'].append(dict(
                id=eid, type='FACADE_PARTICIPANT', source=owner, target=host,
                properties=dict(_metadata(candidate), role='specified-exterior-projection',
                                regionId=rid, analysisItems=list(ITEMS),
                                status='synthetic_assignment', evidence=['EV01'],
                                candidateRuleVersion=RULE_VERSION,
                                scopeBasis='本记录指定墙面；B01与U01不是同栋频数单位'),
                status='synthetic_assignment', evidence=['EV01']))
    if not any(v.get('type') == 'FACADE_PARTICIPANT' for v in candidate.get('relationVocabulary', [])):
        candidate.setdefault('relationVocabulary', []).append(dict(
            type='FACADE_PARTICIPANT', origin='research-extension',
            definition='区域→复用墙；regionId限定局部外侧投影，不是BOT核心或contains-opening'))
    validate(candidate)
    # Only authorized new fields/edges/vocabulary are published; old objects remain intact.
    for host, _, _, _, _ in SPECS:
        if 'facadeRecords' not in nodes[host]['properties']:
            nodes[host]['properties']['facadeRecords'] = cn[host]['properties']['facadeRecords']
    old_ids = {e['id'] for e in model['relationships']}
    model['relationships'].extend(e for e in candidate['relationships'] if e['id'] not in old_ids)
    if not any(v.get('type') == 'FACADE_PARTICIPANT' for v in model.get('relationVocabulary', [])):
        model.setdefault('relationVocabulary', []).append(candidate['relationVocabulary'][-1])
    return model


def _collect(model):
    nodes = _index(model)
    global_ids = set()
    # All local IDs across all hosts (including an accidental record copied to another wall).
    for node in nodes.values():
        for record in node.get('properties', {}).get('facadeRecords', []):
            _require(isinstance(record, dict), 'facade record must be dict')
            local = [record] + record.get('surfaceRegions', [])
            for item in local:
                key = item.get('id')
                _require(isinstance(key, str) and key and key not in global_ids, 'duplicate/missing local id')
                global_ids.add(key)
    result = []
    for host, owner, rid, side, opening_ids in SPECS:
        _require(host in nodes and owner in nodes, 'host/owner missing')
        wall = nodes[host]
        _check_metadata(wall['properties'], model)
        _require(wall['properties'].get('geometryVersion') == model['modelVersion'], 'wall geometryVersion missing/stale')
        _check_metadata(wall['geometry'], model)
        _check_metadata(nodes[owner]['properties'], model)
        records = wall['properties'].get('facadeRecords')
        _require(isinstance(records, list) and len(records) == 1, 'exactly one bounded facade record required')
        record = records[0]
        _require(record['id'] == rid and record['hostId'] == host and record['ownerId'] == owner,
                 'facade identity/host mismatch')
        _check_metadata(record, model, True)
        _require(record['exteriorSide'] == side and record.get('scopeBasis'), 'exterior side/scope')
        _require(record.get('candidateRuleVersion') == RULE_VERSION, 'unsupported candidate rule')
        _require(record.get('status') == 'synthetic_assignment' and record.get('evidence') == ['EV01'], 'record source boundary')
        _require(record.get('colorState') == 'conditional-not-enabled', 'color calibration/image unavailable')
        _require(record.get('decorationState') == 'unknown', 'unknown decoration is not absent')
        gross, _, projection = _wall_geometry(wall, side)
        saved = _polygon(record['outlineUZ'])
        _require(gross.symmetric_difference(saved).area <= EPS, 'stale facade outline vs current wall topProfile')
        _require(_close(record['projectionRangeUZ'], list(gross.bounds)), 'stale projection range')
        for key in ('axisOriginXYZ', 'exteriorOriginXYZ', 'uAxisXYZ', 'outwardNormalXYZ', 'offsetM'):
            _require(_close(record['projection'][key], projection[key]), 'stale projection ' + key)
        for key in ('mode', 'heightBasis', 'offsetBasis'):
            _require(record['projection'].get(key) == projection[key], 'projection basis mismatch')
        edges = [e for e in model['relationships'] if e.get('type') == 'FACADE_PARTICIPANT'
                 and e.get('properties', {}).get('regionId') == rid]
        _require(len(edges) == 1, 'unique facade participant required')
        edge = edges[0]
        _require(edge['id'] == 'D04-FACADE-' + host and edge['source'] == owner and edge['target'] == host,
                 'facade participant endpoints/id')
        ep = edge['properties']
        _check_metadata(ep, model, True)
        _require(ep.get('role') == 'specified-exterior-projection' and ep.get('analysisItems') == ITEMS,
                 'participant scope/analysisItems')
        _require(edge.get('status') == ep.get('status') == 'synthetic_assignment'
                 and edge.get('evidence') == ep.get('evidence') == ['EV01'], 'participant source boundary')
        _require(sorted(record['openingIds']) == sorted(opening_ids), 'bounded opening inventory incomplete/duplicate')
        openings = []
        for iid in sorted(record['openingIds']):
            _require(iid in nodes, 'opening missing ' + iid)
            opening = nodes[iid]
            _check_metadata(opening['properties'], model)
            _require(opening['properties'].get('geometryVersion') == model['modelVersion'], 'opening geometryVersion missing/stale')
            _check_metadata(opening['geometry'], model)
            hosts = [e['target'] for e in model['relationships'] if e.get('type') == 'INTERFACE_OF'
                     and e.get('source') == iid and e.get('properties', {}).get('role') == 'opening-host']
            _require(hosts == [host], 'opening host missing/ambiguous/mismatched ' + iid)
            _require(opening.get('class') == 'Interface', 'opening identity must be Interface')
            polygon = _opening(opening, wall, projection)
            _inside(gross, polygon)
            openings.append((iid, polygon))
        union = unary_union([p for _, p in openings])
        net = gross.difference(union)
        _require(net.area > EPS, 'no positive net facade domain')
        regions = record.get('surfaceRegions', [])
        _require(isinstance(regions, list), 'surfaceRegions must be list')
        parts = []
        for region in sorted(regions, key=lambda x: x['id']):
            _check_metadata(region, model, True)
            _require(region.get('layer') == 'surface', 'surface layer only')
            _require(region.get('status') == 'synthetic_assignment' and region.get('evidence') == ['EV01'], 'surface source boundary')
            state = region.get('state')
            _require(state in ('known', 'unknown', 'mixed'), 'unknown must not become absent')
            material = region.get('material')
            if state == 'known':
                _require(isinstance(material, str) and material.strip()
                         and material.strip().lower() not in ('unknown', 'mixed', 'none', '无', '未知', '混合', '不明'), 'known material required')
            else:
                _require(material is None, 'unknown/mixed material may not be allocated')
            polygon = _rect(region['rectUZ'])
            _inside(gross, polygon)
            for _, other in parts:
                _require(polygon.intersection(other).area == 0.0, 'surface regions overlap')
            parts.append((region, polygon))
        result.append((record, gross, openings, union, net, parts))
    return sorted(result, key=lambda row: row[0]['id'])


def validate(model):
    """Validate this bounded D04 structure, not all modules or HAS_SOURCE publication."""
    try:
        _collect(model)
    except ValueError:
        raise
    except (KeyError, TypeError, IndexError, AttributeError, OverflowError, ShapelyError) as exc:
        raise ValueError('invalid D04 structure: ' + str(exc)) from exc
    return True


def _source_context(model, record):
    """Trace current source descriptors, without claiming they support new fields."""
    source = next(n for n in model['nodes'] if n['id'] == 'EV01')
    links = [deepcopy(e) for e in model['relationships'] if e.get('type') == 'HAS_SOURCE'
             and e.get('source') == record['hostId']]
    return dict(evidence=list(record['evidence']), sourceId='EV01',
                sourceProperties=deepcopy(source.get('properties', {})),
                existingHostSourceLinks=sorted(links, key=lambda e: e['id']),
                newFieldSourcePublication=('explicit-facadeRecords-link-present; full source validation belongs to unified compiler' if any('facadeRecords' in e['properties'].get('fields',[]) for e in links) else 'deferred-to-main-session; existing links do not imply new-field support'))


def analyze(model):
    """Fresh computation from the supplied model; never use analysisResults caches."""
    validate(model)
    rows = _collect(model)
    out = {key: [] for key in ('T01', 'T02', 'T03', 'T04', 'T05', 'T06')}
    for r, gross, openings, union, net, parts in rows:
        base = dict(regionId=r['id'], hostId=r['hostId'], ownerId=r['ownerId'],
                    geometryVersion=model['modelVersion'], scenario=SCENARIO,
                    candidateRuleVersion=RULE_VERSION, status='synthetic-derived',
                    coordinateFrame=FRAME, sourceContext=_source_context(model, r))
        u0, z0, u1, z1 = gross.bounds
        width, height = u1 - u0, z1 - z0
        out['T01'].append(dict(base, widthM=width, heightM=height, grossAreaM2=gross.area,
                              heightWidthRatio=height / width, widthHeightRatio=width / height,
                              outlineUZ=deepcopy(r['outlineUZ']), projection=deepcopy(r['projection']),
                              geometryClass='rectangular-profile' if abs(gross.area - width * height) <= EPS else 'profile-polygon',
                              scopeBasis=r['scopeBasis']))
        positions = []
        for iid, p in openings:
            a, b, c, d = p.bounds
            positions.append(dict(interfaceId=iid, interfaceUid='V01:' + iid,
                                  boundsUZ=[a, b, c, d], centerUZ=[p.centroid.x, p.centroid.y],
                                  relativeCenterUZ=[(p.centroid.x-u0)/width, (p.centroid.y-z0)/height],
                                  marginsM=dict(left=a-u0, right=u1-c, bottom=b-z0, top=z1-d),
                                  areaM2=p.area))
        spatial = sorted(positions, key=lambda p: (p['centerUZ'][0], p['interfaceId']))
        pairs = []
        for a, b in zip(spatial, spatial[1:]):
            pairs.append(dict(leftId=a['interfaceId'], rightId=b['interfaceId'],
                              centerDistanceM=math.dist(a['centerUZ'], b['centerUZ']),
                              horizontalCenterDistanceM=b['centerUZ'][0]-a['centerUZ'][0],
                              netEdgeGapM=b['boundsUZ'][0]-a['boundsUZ'][2]))
        gaps = [p['horizontalCenterDistanceM'] for p in pairs]
        mean = sum(gaps)/len(gaps) if len(gaps) >= 2 else None
        spacing = [g-mean for g in gaps] if mean is not None else []
        symmetry = []
        for a, b in zip(spatial, reversed(spatial)):
            if a['interfaceId'] > b['interfaceId']:
                continue
            symmetry.append(dict(firstId=a['interfaceId'], secondId=b['interfaceId'],
                                 horizontalReflectionResidualM=a['centerUZ'][0]+b['centerUZ'][0]-u0-u1,
                                 verticalAlignmentResidualM=a['centerUZ'][1]-b['centerUZ'][1],
                                 widthResidualM=(a['boundsUZ'][2]-a['boundsUZ'][0])-(b['boundsUZ'][2]-b['boundsUZ'][0]),
                                 heightResidualM=(a['boundsUZ'][3]-a['boundsUZ'][1])-(b['boundsUZ'][3]-b['boundsUZ'][1])))
        out['T02'].append(dict(base, openingCount=len(openings), openings=positions,
                              spatialSequence=[p['interfaceId'] for p in spatial],
                              adjacentPairs=sorted(pairs, key=lambda p: (p['leftId'], p['rightId'])),
                              openingUnionAreaM2=union.area, netDomainAreaM2=net.area,
                              projectedOpeningAreaRatio=union.area/gross.area,
                              denominator='指定合成墙面毛正投影面积；非通风率/通行率',
                              equalSpacingResidualsM=spacing, equalSpacingState='continuous-only' if mean is not None else 'insufficient-pairs',
                              symmetryResiduals=sorted(symmetry, key=lambda p: (p['firstId'], p['secondId'])),
                              classification='not-graded-unreviewed-tolerance'))
        materials = {}
        known_polygons = []
        unresolved_parts = []
        zero_net_regions = []
        for region, polygon in parts:
            clipped = net.intersection(polygon)
            area = clipped.area
            if area == 0:
                zero_net_regions.append(dict(regionId=region['id'], state=region['state'], areaM2=0.0))
                continue
            if region['state'] == 'known':
                materials.setdefault(region['material'], []).append(clipped)
                known_polygons.append(clipped)
            else:
                unresolved_parts.append(dict(regionId=region['id'], state=region['state'], areaM2=area))
        known_union = unary_union(known_polygons)
        known_area = known_union.area
        unknown_geometry = net.difference(known_union)
        unknown_area = unknown_geometry.area
        material_areas = {k: unary_union(v).area for k, v in sorted(materials.items())}
        shares = {k: v/known_area for k, v in material_areas.items()} if known_area > 0 else None
        whole = {k: v/net.area for k, v in material_areas.items()} if unknown_area == 0 else None
        declared_union = unary_union([p for _, p in parts])
        out['T03'].append(dict(base, layer='surface', areaMode='same-orthographic-projection-minus-opening-union',
                              netDomainAreaM2=net.area, knownAreaM2=known_area, unknownAreaM2=unknown_area,
                              uncoveredAreaM2=net.difference(declared_union).area,
                              unresolvedParts=unresolved_parts, zeroNetSurfaceRegions=zero_net_regions, materialAreasM2=material_areas,
                              knownDomainShares=shares, knownDomainDenominatorM2=known_area,
                              knownCoverage=known_area/net.area, wholeDomainShares=whole,
                              wholeDomainSharesState='enabled' if whole is not None else 'prohibited-unknown-area',
                              state='known' if unknown_area == 0 else 'unknown',
                              materialBoundary='仅表层；unknown包含未分配mixed与未登记面域；不推芯材，不否定含灰泥标签'))
        out['T04'].append(dict(base, state='conditional-not-enabled', reason='没有校准/影像依据；不虚构RGB或花纹'))
        out['T05'].append(dict(base, state='unknown', reason='细部证据缺失不等于无装饰'))
        out['T06'].append(dict(base, countUnit='owner-host-region-scenario', observationCount=1,
                              combination=dict(profile=out['T01'][-1]['geometryClass'],
                                               openingStructure='single-opening' if len(openings) == 1 else 'multiple-openings',
                                               openingIds=[iid for iid, _ in openings],
                                               surfaceState=out['T03'][-1]['state'],
                                               materials=sorted(material_areas), color='conditional-not-enabled', decoration='unknown'),
                              aggregation='local-only; B01主屋与U01院墙不合并为同栋频数',
                              interpretation='分部位当前合成组合；不作年代/文化解释；同ID多照片不增计数'))
    return out
