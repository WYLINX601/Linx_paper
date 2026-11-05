"""Integration and provenance tests; mutations stay in memory, never database."""
from pathlib import Path
import copy,json,math,sys,unittest
W=Path(__file__).parent;sys.path.insert(0,str(W/'tools'))
import d04,d05,d06
from compile_model import compile_model,validate_model
from analyze import analyze
from projection import rehydrate,validate_extension_sources
M,P=compile_model(W/'candidate/model.json');A=analyze(P)
def node(m,id):return next(x for x in m['nodes'] if x['id']==id)
def rel(m,id):return next(x for x in m['relationships'] if x['id']==id)
class ExtensionTests(unittest.TestCase):
 def test_scope_item_counts(self):self.assertEqual([len(A[k]) for k in ['D04','D05','D06']],[6,6,5])
 def test_no_facade_material_type_nodes(self):self.assertFalse(any(set(n['labels'])&{'Facade','Material','ClassificationScheme'} for n in M['nodes']))
 def test_only_distinct_new_identity(self):
  b=json.loads((W/'originals/model.json').read_text());self.assertEqual(set(x['id'] for x in M['nodes'])-set(x['id'] for x in b['nodes']),{'B03','CG01','ST01','TP01'})
 def test_old_geometry_preserved(self):
  b=json.loads((W/'originals/model.json').read_text());self.assertTrue(all(n['geometry']==node(M,n['id'])['geometry'] for n in b['nodes']))
 def test_old_relationship_identity_semantics(self):
  b=json.loads((W/'originals/model.json').read_text());self.assertTrue(all(all(r[k]==rel(M,r['id'])[k] for k in ['type','source','target']) for r in b['relationships']))
 def test_old_analysis_unchanged(self):
  b=json.loads((W/'tests/baseline-analysis.json').read_text())
  def norm(v):
   if isinstance(v,dict):return {k:norm(x) for k,x in v.items()}
   if isinstance(v,list):return [norm(x) for x in v]
   return 'V01-unified-2.0' if v in ['V01-unified-2.1','V01-unified-2.2'] else v
  for k in ['D01','D03']:self.assertEqual(norm(A[k]),b[k])
 def test_facade_opening_inventory(self):self.assertEqual([x['openingCount'] for x in A['D04']['T02']],[3,1])
 def test_facade_exact_area(self):
  x=A['D04']['T01'][0];self.assertAlmostEqual(x['grossAreaM2'],9.6*3.6);self.assertAlmostEqual(x['heightM'],node(M,'W03')['geometry']['topProfile'][0][2]);self.assertNotEqual(x['heightM'],node(M,'B01')['properties']['eaveZM'])
 def test_material_unknown_denominator(self):
  x=A['D04']['T03'][1];self.assertGreater(x['unknownAreaM2'],0);self.assertIsNone(x['wholeDomainShares']);self.assertAlmostEqual(x['knownCoverage'],0.5);self.assertEqual(x['knownDomainShares'],{'灰泥':1.0})
 def test_conditional_not_absent(self):self.assertTrue(all(x['state']=='conditional-not-enabled' for x in A['D04']['T04']));self.assertTrue(all(x['state']=='unknown' for x in A['D04']['T05']))
 def test_group_not_zone_or_three_dwellings(self):self.assertNotIn('Zone',node(M,'CG01')['labels']);self.assertEqual(A['D05']['T01']['buildingCount'],3);self.assertEqual(A['D05']['T01']['independentDwellingCount'],'not-established')
 def test_street_opening_union(self):
  x=A['D05']['T03'];self.assertAlmostEqual(x['pavementWidthM'],-4.92-(-8.8));self.assertAlmostEqual(x['sides']['left']['knownEntityLengthM'],9.6-(5.6-4));self.assertEqual(x['sides']['right']['sectionVerticalRangeZM'],[0,3])
 def test_same_point_gate_unknown(self):self.assertEqual(A['D05']['T04']['thresholdToSamePointPavement']['status'],'unknown')
 def test_slope_separate(self):x=A['D05']['T04'];self.assertAlmostEqual(x['slopeRatio'],3/math.hypot(10-9.6,-3-(-6.8)))
 def test_ground_unknown_stops(self):
  m=copy.deepcopy(M);node(m,'TP01')['properties']['groundState']='unknown';self.assertEqual(d05.analyze(m)['T04']['status'],'unknown')
 def test_street_unknown_not_open(self):
  m=copy.deepcopy(M);rel(m,'D05-RIGHT')['properties']['segments']=[{'rangeM':[0,9.6],'state':'unknown','basis':'unknown'}];x=d05.analyze(m)['T03']['sides']['right'];self.assertIsNone(x['completeEntityProportion']);self.assertEqual(x['ranges']['opening'],[])
 def test_pair_is_explicit(self):x=A['D06']['T02']['localPairs'];self.assertEqual(len(x),1);self.assertEqual(x[0]['viaInterfaceId'],'I05');self.assertIsNone(A['D06']['T02']['wholeBuildingCombinationFrequency'])
 def test_joint_not_union(self):self.assertEqual(A['D06']['T02']['jointValidUnitIds'],['D04-W03-N']);self.assertEqual(A['D06']['T02']['jointValidCount'],1)
 def test_groups_and_explanation_stop(self):self.assertEqual(A['D06']['T04']['status'],'not-estimable');self.assertIn('民族专属性',A['D06']['T05']['unsupported'])
 def test_type_unknown(self):self.assertEqual(d06.classify({'openingCount':None},d06.schemes()[0])['state'],'unknown')
 def test_type_known_unmatched(self):self.assertEqual(d06.classify({'openingCount':0},d06.schemes()[0])['state'],'known-unmatched')
 def test_type_overlap_conflict(self):
  s=d06.schemes()[0];s['rules'].append({'code':'overlap','when':{'openingCount':{'ge':1}}});self.assertEqual(d06.classify({'openingCount':1},s)['state'],'rule-conflict')
 def test_multilabel_preserved(self):
  s=d06.schemes()[0];s['mode']='multi-label';s['rules'].append({'code':'another','when':{'openingCount':{'ge':1}}});self.assertEqual(len(d06.classify({'openingCount':1},s)['matches']),2)
 def test_rule_version_content_lock(self):
  m=copy.deepcopy(M);m['analysisContract']['D06']['schemes'][0]['rules'][0]['when']['openingCount']['eq']=7
  with self.assertRaises(ValueError):validate_model(m)
 def test_forced_cartesian_rejected(self):
  m=copy.deepcopy(M);m['analysisContract']['D06']['localPairs'].append(copy.deepcopy(m['analysisContract']['D06']['localPairs'][0]))
  with self.assertRaises(ValueError):validate_model(m)
 def test_field_source_missing(self):
  m=copy.deepcopy(M);rel(m,'X-SRC-W03')['properties']['fields'].remove('facadeRecords')
  with self.assertRaisesRegex(ValueError,'Unsupported extension field'):validate_extension_sources(m)
 def test_field_pointer_wrong_object(self):
  m=copy.deepcopy(M);rel(m,'X-SRC-W03')['properties']['locator']='/nodes/0/properties'
  with self.assertRaises(ValueError):validate_extension_sources(m)
 def test_both_current_source_versions_upgrade_rejected(self):
  m=copy.deepcopy(M);node(m,'EV01')['properties']['sourceVersion']='future';rel(m,'X-SRC-W03')['properties']['sourceVersion']='future'
  with self.assertRaises(ValueError):validate_extension_sources(m)
 def test_relationship_assertion_pointer(self):
  m=copy.deepcopy(M);rel(m,'D04-FACADE-W03')['properties']['assertionLocator']='/relationships/0'
  with self.assertRaises(ValueError):validate_extension_sources(m)
 def test_nan_rejected(self):
  m=copy.deepcopy(M);node(m,'W03')['properties']['facadeRecords'][0]['outlineUZ'][0][0]=float('nan')
  with self.assertRaises(ValueError):validate_model(m)
 def test_actual_graph_values_not_raw_snapshot(self):
  p=copy.deepcopy(P);x=node(p,'W03')['properties'];records=json.loads(x['facadeRecordsJson']);records[0]['surfaceRegions'][0]['state']='unknown';records[0]['surfaceRegions'][0]['material']=None;x['facadeRecordsJson']=json.dumps(records)
  b=analyze(p);self.assertIsNone(b['D04']['T03'][0]['wholeDomainShares']);self.assertEqual(b['D06']['T02']['jointValidCount'],0)
 def test_readback_geometry_stale_rejected(self):
  p=copy.deepcopy(P);x=node(p,'W03')['properties'];g=json.loads(x['geometryJson']);g['topProfile'][0][2]+=1;x['geometryJson']=json.dumps(g)
  with self.assertRaises(ValueError):analyze(p)
 def test_readback_relation_change_rejected(self):
  p=copy.deepcopy(P);rel(p,'D04-FACADE-W03')['target']='V01:W10'
  with self.assertRaises(ValueError):analyze(p)
 def test_unordered_input_deterministic(self):
  p=copy.deepcopy(P);p['nodes'].reverse();p['relationships'].reverse();self.assertEqual(analyze(p),A)
 def test_no_new_access_or_internal_support(self):
  b=json.loads((W/'originals/model.json').read_text());types=['DIRECT_ACCESS_TO','SUPPORTS_SYSTEM'];self.assertEqual([r['id'] for r in b['relationships'] if r['type'] in types],[r['id'] for r in M['relationships'] if r['type'] in types])
 def test_actual_readback_if_available(self):
  if (W/'db/V01-readback.json').exists():self.assertEqual(analyze(json.loads((W/'db/V01-readback.json').read_text())),A)
  else:self.skipTest('Database commit not yet performed')
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExtensionTests));(W/'tests/extensions.json').write_text(json.dumps({'count':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'status':'passed' if r.wasSuccessful() else 'failed','scope':'in-memory positive/negative tests, not persisted corrupt data'},ensure_ascii=False,indent=2));sys.exit(not r.wasSuccessful())
