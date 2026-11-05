"""真实 original model.json 输入，不伪造主会话模块。"""
import copy
import json
import math
from pathlib import Path
import unittest
from d05 import extend, analyze, validate, NEW_IDS

ORIGINAL = Path(__file__).resolve().parents[2] / 'originals' / 'model.json'


class D05Tests(unittest.TestCase):
    def setUp(self):
        self.original = json.loads(ORIGINAL.read_text())
        self.m = copy.deepcopy(self.original)
        self.assertIs(extend(self.m), self.m)

    def node(self, i):
        return next(n for n in self.m['nodes'] if n['id'] == i)

    def edge(self, i):
        return next(e for e in self.m['relationships'] if e['id'] == i)

    def rejected(self):
        with self.assertRaises(ValueError):
            validate(self.m)
        with self.assertRaises(ValueError):
            analyze(self.m)

    def test_01_api_and_idempotence(self):
        self.assertTrue(validate(self.m))
        before = copy.deepcopy(self.m)
        self.assertIs(extend(self.m), self.m)
        self.assertEqual(before, self.m)
        result = analyze(self.m)
        self.assertEqual(list(result), ['T01', 'T02', 'T03', 'T04', 'T05', 'T06'])
        self.assertEqual(before, self.m)
        self.assertEqual(self.original['modelVersion'], self.m['modelVersion'])

    def test_02_all_old_records_exactly_preserved(self):
        for key in ('nodes', 'relationships'):
            current = {x['id']: x for x in self.m[key]}
            for x in self.original[key]:
                self.assertEqual(x, current[x['id']])
        self.assertEqual({n['id'] for n in self.m['nodes']} - {n['id'] for n in self.original['nodes']}, set(NEW_IDS))

    def test_03_boundary_outside_rejected(self):
        self.node('CG01')['geometry']['max'][0] = 13
        self.rejected()

    def test_04_touching_and_larger_boundary_recomputed(self):
        self.node('CG01')['geometry']['max'][0] = 14
        members = analyze(self.m)['T01']['members']
        self.assertEqual(next(x for x in members if x['id'] == 'B02')['boundaryState'], 'touching')
        self.node('CG01')['geometry']['max'][0] = 16
        self.assertEqual(next(x for x in analyze(self.m)['T01']['members'] if x['id'] == 'B02')['boundaryState'], 'inside')

    def test_05_member_duplicate_rejected(self):
        self.edge('D05-MEM-B03')['target'] = 'B02'
        self.rejected()

    def test_06_member_omission_rejected(self):
        self.m['relationships'].remove(self.edge('D05-MEM-B03'))
        self.rejected()

    def test_07_mixed_units_frame_scenario_version(self):
        good = copy.deepcopy(self.m)
        for key, value in [('unit', 'cm'), ('coordinateFrame', 'other'), ('scenario', 'other'), ('geometryVersion', 'stale')]:
            with self.subTest(key=key):
                self.m = copy.deepcopy(good)
                self.node('B02')['properties'][key] = value
                self.rejected()

    def test_08_datum_and_role_version_rejected(self):
        good = copy.deepcopy(self.m)
        for id_, key, value in [('DATUM-B02', 'frameVersion', 'stale'), ('D05-MEM-B01', 'role', 'neighbor'),
                                ('D05-MEM-B01', 'boundaryVersion', 'stale'), ('D05-LEFT', 'geometryVersion', 'stale')]:
            with self.subTest(id_=id_, key=key):
                self.m = copy.deepcopy(good)
                self.edge(id_)['properties'][key] = value
                self.rejected()

    def test_09_unknown_not_open(self):
        seg = self.edge('D05-LEFT')['properties']['segments'][0]
        seg.update(state='unknown', basis='unknown')
        left = analyze(self.m)['T03']['sides']['left']
        self.assertIsNone(left['completeEntityProportion'])
        self.assertEqual(left['ranges']['unknown'], [[0, 4]])
        seg['state'] = 'open'
        self.rejected()

    def test_10_omitted_opening_rejected(self):
        self.edge('D05-LEFT')['properties']['segments'] = [dict(rangeM=[0, 9.6], state='entity', basis='W10')]
        self.rejected()

    def test_11_interval_union_not_double_counted(self):
        p = self.edge('D05-LEFT')['properties']
        p['segments'].append(dict(rangeM=[1, 3], state='entity', basis='W10'))
        self.assertAlmostEqual(analyze(self.m)['T03']['sides']['left']['knownEntityLengthM'], 8)
        p['segments'].append(dict(rangeM=[3, 5], state='entity', basis='W10'))
        self.rejected()

    def test_12_unknown_ground_and_missing_profile(self):
        self.node('TP01')['properties']['groundSource'] = 'unknown'
        self.assertEqual(analyze(self.m)['T04']['status'], 'unknown')
        self.m['nodes'].remove(self.node('TP01'))
        self.m['relationships'] = [e for e in self.m['relationships'] if 'TP01' not in (e['source'], e['target'])]
        self.assertTrue(validate(self.m))
        self.assertEqual(analyze(self.m)['T04']['status'], 'unknown')

    def test_13_ground_computation_and_threshold_unknown(self):
        r = analyze(self.m)['T04']
        self.assertAlmostEqual(r['horizontalDistanceM'], math.hypot(.4, 3.8))
        self.assertEqual(r['elevationDifferenceM'], 3)
        self.assertAlmostEqual(r['slopeRatio'], 3/math.hypot(.4, 3.8))
        self.assertEqual(r['B02ReferencePointDifferenceM'], 0)
        self.assertEqual(r['thresholdToSamePointPavement']['status'], 'unknown')
        self.assertIsNone(r['thresholdToSamePointPavement']['differenceM'])
        self.node('TP01')['geometry']['pointsXYZ'][0][2] = 1
        self.assertEqual(analyze(self.m)['T04']['elevationDifferenceM'], 2)

    def test_14_sets_stable_and_geometry_not_sorted(self):
        baseline = analyze(self.m)
        self.m['nodes'].reverse()
        self.m['relationships'].reverse()
        self.edge('D05-LEFT')['properties']['segments'].reverse()
        self.assertEqual(baseline, analyze(self.m))
        self.node('TP01')['geometry']['pointsXYZ'].reverse()
        self.rejected()

    def test_15_order_rule_and_ties(self):
        seq = analyze(self.m)['T05']['sequence']
        self.assertEqual([x['id'] for x in seq], ['B01', 'B03', 'B02'])
        self.assertEqual(seq[0]['tieIds'], ['B01', 'B03'])
        self.m['analysisContract']['D05']['sequenceOrder'] = 'center-X-descending-ties'
        self.assertEqual([x['id'] for x in analyze(self.m)['T05']['sequence']], ['B02', 'B01', 'B03'])

    def test_16_no_new_frame_access_source_edges(self):
        old = {e['id'] for e in self.original['relationships']}
        new = [e for e in self.m['relationships'] if e['id'] not in old]
        self.assertTrue(all(e['id'].startswith('D05-') for e in new))
        self.assertFalse({'DIRECT_ACCESS_TO', 'SUPPORTS_SYSTEM', 'HAS_SOURCE'} & {e['type'] for e in new})
        self.assertFalse(any('Element' in n['labels'] for n in self.m['nodes'] if n['id'] in NEW_IDS))
        self.edge('D05-GROUND')['type'] = 'DIRECT_ACCESS_TO'
        self.rejected()

    def test_17_same_dwelling_not_three_independent(self):
        t = analyze(self.m)['T01']
        self.assertEqual(t['buildingCount'], 3)
        self.assertEqual(t['sameDwelling'], ['B01', 'B02'])
        self.assertEqual(t['independentDwellingCount'], 'not-established')
        self.assertNotIn('legacyUid', self.node('B03')['properties'])
        self.assertEqual(self.node('B03')['evidence'], ['EV01'])

    def test_18_reference_box_distances_not_clearance(self):
        pairs = analyze(self.m)['T02']['pairs']
        self.assertAlmostEqual(pairs[0]['referenceBoxDistance2DM'], .4)
        self.assertAlmostEqual(pairs[1]['referenceBoxDistance2DM'], 8.8)
        self.assertTrue(all(p['buildingClearance']['status'] == 'refused' for p in pairs))
        self.assertAlmostEqual(pairs[0]['eaveDifferenceM'], 7-3.2666666666666666)
        self.assertEqual(pairs[0]['widthAxisAngleDeg'], 90)

    def test_19_street_width_height_not_roof(self):
        r = analyze(self.m)['T03']
        self.assertAlmostEqual(r['pavementWidthM'], 3.88)
        self.assertAlmostEqual(r['boundarySeparationM'], 3.88)
        self.assertAlmostEqual(r['sides']['left']['knownEntityProportion'], 8/9.6)
        self.assertEqual(r['sides']['left']['sectionVerticalRangeZM'], [0, 1.6])
        self.assertEqual(r['sides']['right']['sectionVerticalRangeZM'], [0, 3])
        self.assertEqual(r['sides']['right']['ranges']['opening'], [])

    def test_20_structure_errors(self):
        good = copy.deepcopy(self.m)
        mutations = [lambda: self.m['nodes'].append(copy.deepcopy(self.node('CG01'))),
                     lambda: self.edge('D05-LEFT').update(target='missing'),
                     lambda: self.node('B03')['properties'].update(depthM=3.2+1e-4),
                     lambda: self.node('B03')['properties'].update(eaveZM=float('nan')),
                     lambda: self.m['analysisContract']['D05'].update(excluded=[]),
                     lambda: self.node('CG01').update(labels=['Zone']),
                     lambda: self.node('TP01')['geometry'].update(pointsXYZ=[[0, 0, 0], [0, 0, 3]])]
        for i, change in enumerate(mutations):
            with self.subTest(i=i):
                self.m = copy.deepcopy(good)
                change()
                self.rejected()

    def test_21_full_upgrade_uses_input_version(self):
        old = self.original['modelVersion']
        fresh = json.loads(json.dumps(self.original).replace(old, 'V01-unified-2.1'))
        extend(fresh)
        self.assertTrue(validate(fresh))
        self.assertEqual(fresh['analysisContract']['D05']['version'], 'V01-unified-2.1')

    def test_22_ground_not_roof_or_false_reference(self):
        self.node('TP01')['geometry']['pointsXYZ'][1][2] = 8
        self.rejected()

    def test_23_exact_float_footprint_dimensions(self):
        p = self.node('B03')['properties']; g = self.node('B03')['geometry']
        self.assertEqual(p['depthM'], g['max'][1]-g['min'][1])
        self.assertEqual(p['footprintXY'], [0, -12, 9.6, -12, 9.6, -8.8, 0, -8.8])

    def test_24_reject_inconsistent_pavement_and_missing_coverage(self):
        self.node('ST01')['geometry']['surfaceXY'][1] = -9
        self.rejected()

    def test_25_interval_gaps_and_false_openings(self):
        p = self.edge('D05-RIGHT')['properties']
        p['segments'] = [dict(rangeM=[0, 9], state='entity', basis='B03')]
        self.rejected()
        p['segments'].append(dict(rangeM=[9, 9.6], state='unknown', basis='unknown'))
        self.assertIsNone(analyze(self.m)['T03']['sides']['right']['completeEntityProportion'])
        p['segments'][-1].update(state='opening', basis='I05')
        self.rejected()


if __name__ == '__main__':
    unittest.main(verbosity=2)
