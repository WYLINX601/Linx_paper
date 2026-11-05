"""Run with python -B -m unittest -v test_d04 (no model/files written)."""
import copy
import json
from pathlib import Path
import unittest

import d04

ORIGINAL = Path(__file__).resolve().parents[2] / 'originals' / 'model.json'


def fixture():
    return json.loads(ORIGINAL.read_text(encoding='utf-8'))


def node(model, key):
    return next(n for n in model['nodes'] if n['id'] == key)


def record(model, key='W03'):
    return node(model, key)['properties']['facadeRecords'][0]


class D04Tests(unittest.TestCase):
    def setUp(self):
        self.original = fixture()
        self.m = d04.extend(copy.deepcopy(self.original))

    def reject(self, model=None):
        with self.assertRaises(ValueError):
            d04.validate(self.m if model is None else model)
        with self.assertRaises(ValueError):
            d04.analyze(self.m if model is None else model)

    def test_01_positive_actual_original(self):
        self.assertTrue(d04.validate(self.m))
        a = d04.analyze(self.m)
        self.assertEqual(list(a), ['T01', 'T02', 'T03', 'T04', 'T05', 'T06'])
        self.assertAlmostEqual(a['T01'][0]['grossAreaM2'], 34.56)
        self.assertAlmostEqual(a['T01'][1]['grossAreaM2'], 15.36)
        self.assertEqual([x['openingCount'] for x in a['T02']], [3, 1])
        self.assertAlmostEqual(a['T02'][0]['openingUnionAreaM2'], 3.6)
        self.assertAlmostEqual(a['T02'][1]['openingUnionAreaM2'], 2.56)
        self.assertAlmostEqual(a['T03'][0]['knownAreaM2'], 30.96)
        self.assertAlmostEqual(a['T03'][1]['knownAreaM2'], 6.4)
        self.assertAlmostEqual(a['T03'][1]['unknownAreaM2'], 6.4)
        self.assertEqual(a['T03'][0]['wholeDomainShares'], {'灰泥': 1.0})
        self.assertIsNone(a['T03'][1]['wholeDomainShares'])
        self.assertEqual(a['T04'][0]['state'], 'conditional-not-enabled')
        self.assertEqual(a['T05'][0]['state'], 'unknown')
        self.assertEqual([x['ownerId'] for x in a['T06']], ['B01', 'U01'])
        self.assertEqual(a['T01'][0]['heightM'], 3.6)  # not RF01 eaveZ
        self.assertAlmostEqual(a['T01'][0]['projection']['exteriorOriginXYZ'][1], 7.32)
        self.assertAlmostEqual(a['T01'][1]['projection']['exteriorOriginXYZ'][1], -4.92)

    def test_02_idempotent_preserves_old_objects_edges(self):
        before = copy.deepcopy(self.m)
        self.assertIs(d04.extend(self.m), self.m)
        self.assertEqual(before, self.m)
        for original_node in self.original['nodes']:
            current = copy.deepcopy(node(self.m, original_node['id']))
            current['properties'].pop('facadeRecords', None)
            self.assertEqual(current, original_node)
        self.assertEqual(self.m['relationships'][:len(self.original['relationships'])], self.original['relationships'])
        added = self.m['relationships'][len(self.original['relationships']):]
        self.assertEqual(len(added), 2)
        self.assertTrue(all(e['id'].startswith('D04-') and e['type'] == 'FACADE_PARTICIPANT' for e in added))
        self.assertEqual(sum(e['type'] == 'HAS_SOURCE' for e in self.m['relationships']),
                         sum(e['type'] == 'HAS_SOURCE' for e in self.original['relationships']))

    def test_03_missing_partition_is_unknown_not_absent(self):
        record(self.m)['surfaceRegions'] = []
        a = d04.analyze(self.m)['T03'][0]
        self.assertAlmostEqual(a['unknownAreaM2'], a['netDomainAreaM2'])
        self.assertEqual(a['knownCoverage'], 0)
        self.assertIsNone(a['knownDomainShares'])
        self.assertIsNone(a['wholeDomainShares'])

    def test_04_mixed_is_unallocated(self):
        s = record(self.m)['surfaceRegions'][0]
        s.update(state='mixed', material=None)
        self.assertEqual(d04.analyze(self.m)['T03'][0]['materialAreasM2'], {})
        s['material'] = '灰泥'
        self.reject()

    def test_05_overlap_rejected_even_same_material(self):
        s = copy.deepcopy(record(self.m)['surfaceRegions'][0])
        s['id'] += '-overlap'
        record(self.m)['surfaceRegions'].append(s)
        self.reject()

    def test_06_partition_out_of_bounds(self):
        record(self.m)['surfaceRegions'][0]['rectUZ'][2] = 10
        self.reject()

    def test_07_missing_host_link(self):
        self.m['relationships'] = [e for e in self.m['relationships'] if e['id'] != 'R053']
        self.reject()

    def test_08_wrong_host_or_duplicate_host(self):
        edge = next(e for e in self.m['relationships'] if e['id'] == 'R053')
        edge['target'] = 'W10'
        self.reject()
        edge['target'] = 'W03'
        extra = copy.deepcopy(edge)
        extra['id'] = 'TEST-DUP-HOST'
        self.m['relationships'].append(extra)
        self.reject()

    def test_09_opening_plane_and_bounds(self):
        geometry = node(self.m, 'I08')['geometry']
        geometry['a'][1] += .01
        self.reject()
        geometry['a'][1] -= .01
        geometry['z'][1] = 4
        self.reject()

    def test_10_old_opening_geometry_recomputed_not_cached(self):
        before = d04.analyze(self.m)
        node(self.m, 'I08')['geometry']['b'][0] = 2.4
        self.m['analysisResults'] = {'T02': {'openingUnionAreaM2': -12345}}
        after = d04.analyze(self.m)
        self.assertAlmostEqual(after['T02'][0]['openingUnionAreaM2'], 3.8)
        self.assertNotEqual(before['T02'], after['T02'])
        self.assertAlmostEqual(after['T03'][0]['knownAreaM2'], 30.76)

    def test_11_old_wall_change_requires_scope_refresh(self):
        node(self.m, 'W03')['geometry']['topProfile'][0][2] = 3.8
        self.reject()

    def test_12_duplicate_local_ids_global(self):
        record(self.m, 'W10')['id'] = record(self.m)['id']
        self.reject()

    def test_13_source_descriptor_changes_current_output(self):
        before = d04.analyze(self.m)
        node(self.m, 'EV01')['properties']['locator'] = 'EV01-updated-locator'
        after = d04.analyze(self.m)
        self.assertNotEqual(before['T01'][0]['sourceContext'], after['T01'][0]['sourceContext'])
        self.assertEqual(after['T01'][0]['sourceContext']['sourceProperties']['locator'], 'EV01-updated-locator')
        self.assertEqual(before['T01'][0]['grossAreaM2'], after['T01'][0]['grossAreaM2'])
        record(self.m)['evidence'] = ['EV02']
        self.reject()

    def test_14_order_reversal_stable(self):
        before = d04.analyze(self.m)
        self.m['nodes'].reverse()
        self.m['relationships'].reverse()
        for host in ('W03', 'W10'):
            record(self.m, host)['surfaceRegions'].reverse()
            record(self.m, host)['openingIds'].reverse()
        self.assertEqual(before, d04.analyze(self.m))
        for host in ('W03', 'W10'):
            g = node(self.m, host)['geometry']
            g['a'], g['b'] = g['b'], g['a']
            g['topProfile'].reverse()
        self.assertEqual(before, d04.analyze(self.m))

    def test_15_polygon_reverse_not_sort(self):
        before = d04.analyze(self.m)
        record(self.m)['outlineUZ'].reverse()
        after = d04.analyze(self.m)
        self.assertEqual(after['T01'][0]['outlineUZ'], list(reversed(before['T01'][0]['outlineUZ'])))
        self.assertEqual(before['T03'], after['T03'])

    def test_16_nonfinite_and_invalid_polygon(self):
        record(self.m)['outlineUZ'][0][0] = float('nan')
        self.reject()
        self.m = d04.extend(fixture())
        record(self.m)['outlineUZ'] = [[0, 0], [9.6, 3.6], [9.6, 0], [0, 3.6]]
        self.reject()

    def test_17_version_unit_scenario_frame(self):
        for field, bad in [('geometryVersion', 'stale'), ('unit', 'cm'),
                           ('scenario', 'V01-T1'), ('coordinateFrame', 'elsewhere')]:
            m = copy.deepcopy(self.m)
            record(m)[field] = bad
            self.reject(m)
        node(self.m, 'I08')['properties']['geometryVersion'] = 'stale'
        self.reject()

    def test_18_unknown_is_not_none_or_absent(self):
        record(self.m)['decorationState'] = 'absent'
        self.reject()
        self.m = d04.extend(fixture())
        region = record(self.m, 'W10')['surfaceRegions'][1]
        region['state'] = 'none'
        self.reject()

    def test_19_opening_union_deduplicates_overlap(self):
        node(self.m, 'I09')['geometry'] = copy.deepcopy(node(self.m, 'I08')['geometry'])
        a = d04.analyze(self.m)['T02'][0]
        self.assertEqual(a['openingCount'], 3)  # distinct interface UID, not window panes
        self.assertAlmostEqual(a['openingUnionAreaM2'], 2.4)

    def test_20_missing_opening_or_record(self):
        self.m['nodes'] = [n for n in self.m['nodes'] if n['id'] != 'I08']
        self.reject()
        self.m = d04.extend(fixture())
        del node(self.m, 'W03')['properties']['facadeRecords']
        self.reject()

    def test_21_new_version_inherited_without_migrating_input(self):
        m = fixture()
        def upgrade(x):
            if isinstance(x, dict):
                return {k: upgrade(v) for k, v in x.items()}
            if isinstance(x, list):
                return [upgrade(v) for v in x]
            return 'V01-unified-2.1' if x == 'V01-unified-2.0' else x
        m = upgrade(m)
        d04.extend(m)
        self.assertEqual(record(m)['geometryVersion'], 'V01-unified-2.1')
        self.assertTrue(d04.validate(m))
        self.assertEqual(fixture()['modelVersion'], 'V01-unified-2.0')

    def test_22_analyze_read_only_and_extend_atomic_failure(self):
        before = copy.deepcopy(self.m)
        d04.analyze(self.m)
        self.assertEqual(before, self.m)
        raw = fixture()
        raw['relationships'] = [e for e in raw['relationships'] if e['id'] != 'R053']
        before = copy.deepcopy(raw)
        with self.assertRaises(ValueError):
            d04.extend(raw)
        self.assertEqual(before, raw)

    def test_23_residuals_no_forced_classification(self):
        a = d04.analyze(self.m)['T02'][0]
        self.assertTrue(all(abs(x) < 1e-9 for x in a['equalSpacingResidualsM']))
        self.assertEqual(a['classification'], 'not-graded-unreviewed-tolerance')
        self.assertEqual(a['spatialSequence'], ['I08', 'I09', 'I10'])
        self.assertAlmostEqual(a['adjacentPairs'][0]['horizontalCenterDistanceM'], 3.2)
        self.assertAlmostEqual(a['adjacentPairs'][0]['netEdgeGapM'], 2.0)

    def test_24_bad_structures_return_valueerror(self):
        for bad in [None, {}, {'modelVersion': 'v', 'nodes': [], 'relationships': []}]:
            with self.assertRaises(ValueError):
                d04.validate(bad)
        record(self.m)['surfaceRegions'] = None
        self.reject()

    def test_25_source_version_and_synthetic_boundary(self):
        node(self.m, 'EV01')['properties']['sourceVersion'] = 'stale'
        self.reject()
        self.m = d04.extend(fixture())
        node(self.m, 'EV01')['properties']['isRealWorldEvidence'] = True
        self.reject()

    def test_26_source_links_refreshed_not_support_claim(self):
        before = d04.analyze(self.m)['T01'][0]['sourceContext']
        links = [e for e in self.m['relationships'] if e['type'] == 'HAS_SOURCE' and e['source'] == 'W03']
        self.assertTrue(links)
        links[0]['properties']['locator'] = '/updated-source-location'
        after = d04.analyze(self.m)['T01'][0]['sourceContext']
        self.assertNotEqual(before, after)
        self.assertIn('do not imply new-field support', after['newFieldSourcePublication'])

    def test_27_partition_metadata_and_missing_version(self):
        record(self.m)['surfaceRegions'][0]['unit'] = 'cm'
        self.reject()
        self.m = d04.extend(fixture())
        del node(self.m, 'I08')['properties']['geometryVersion']
        self.reject()

    def test_28_same_source_photos_do_not_inflate_count(self):
        before = d04.analyze(self.m)['T06']
        node(self.m, 'W03')['evidence'].extend(['EV02', 'EV04', 'EV04'])
        after = d04.analyze(self.m)['T06']
        self.assertEqual(before, after)
        self.assertEqual([x['observationCount'] for x in after], [1, 1])

    def test_29_tiny_positive_unknown_still_blocks_whole_share(self):
        region = record(self.m)['surfaceRegions'][0]
        region['rectUZ'][2] -= 1e-11
        a = d04.analyze(self.m)['T03'][0]
        self.assertGreater(a['unknownAreaM2'], 0)
        self.assertIsNone(a['wholeDomainShares'])

    def test_30_tiny_overlap_and_outside_are_rejected(self):
        record(self.m, 'W10')['surfaceRegions'][0]['rectUZ'][2] += 1e-11
        self.reject()
        self.m = d04.extend(fixture())
        record(self.m)['surfaceRegions'][0]['rectUZ'][2] += 1e-11
        self.reject()


if __name__ == '__main__':
    unittest.main(verbosity=2)
