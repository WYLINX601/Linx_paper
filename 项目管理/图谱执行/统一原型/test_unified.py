"""Local semantic and rejection tests; none modify the database."""
import copy,json,math,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'tools'))
from compile_model import compile_model,validate_model,boundary_qualification,interface_qualification,merge_intervals
from analyze import analyze
W=Path(__file__).resolve().parent
M,P=compile_model(W/'candidate/model.json');A=analyze(P)
def node(g,id):return next(n for n in g['nodes'] if n['id']==id)
def rel(g,type):return next(r for r in g['relationships'] if r['type']==type)
def analyze_mutation(fn):
 # Legacy D01/D03 invalid-input diagnostics remain tested independently.
 # Full D04-D06 publication additionally rejects invalid shared inputs.
 p=copy.deepcopy(P);fn(p);return analyze(p,extensions=False)
class UnifiedTests(unittest.TestCase):
 def test_identity(self):
  old=json.loads((W/'originals/v01.json').read_text());self.assertTrue({n['id'] for n in old['nodes']}<=set(n['id'] for n in M['nodes']));self.assertTrue({r['id'] for r in old['relationships']}<=set(r['id'] for r in M['relationships']))
 def test_original_geometry(self):
  old=json.loads((W/'originals/v01.json').read_text());self.assertTrue(all(n['geometry']==node(M,n['id'])['geometry'] for n in old['nodes']))
 def test_no_duplicate_house_court(self):
  self.assertFalse(A['identityReuse']['legacyDuplicateNodes']);self.assertEqual(sum('Courtyard' in n['labels'] for n in P['nodes']),1);self.assertEqual(node(M,'S01')['name'],'堂屋')
 def test_source_distinction(self):self.assertEqual(node(M,'EV09')['properties']['legacyUid'],'D01V01:EV01');self.assertNotEqual(node(M,'EV09')['properties']['sourcePath'],node(M,'EV01')['properties']['sourcePath'])
 def test_no_measurement_nodes(self):self.assertTrue(A['identityReuse']['noMeasurementRecordNodes'])
 def test_eave(self):self.assertAlmostEqual(node(M,'B01')['properties']['eaveZM'],node(M,'RF01')['geometry']['eaveZ']);self.assertNotEqual(node(M,'B01')['properties']['eaveZM'],node(M,'B01')['properties']['wallSupportHeightM'])
 def test_comparison(self):self.assertAlmostEqual(A['D01']['comparison']['valueM'],3.7333333333333334);self.assertNotEqual(A['D01']['comparison']['valueM'],2.)
 def test_membership_not_geometric_containment(self):self.assertTrue(any(r['type']=='MEMBER_OF_ZONE' and r['source']=='W10' and r['target']=='U01' for r in M['relationships']));self.assertFalse(any(r['type']=='BOT_CONTAINS_ELEMENT' for r in M['relationships']))
 def test_roof_surface(self):self.assertTrue(all('Element' not in node(M,id)['labels'] for id in ['RS01','RS02']))
 def test_old_hosts_unified(self):
  old=json.loads((W/'originals/v01.json').read_text());hosts=[r for r in old['relationships'] if r['type']=='REALIZED_IN'];self.assertEqual(len(hosts),8)
  for r in hosts:
   n=next(x for x in M['relationships'] if x['id']==r['id']);self.assertEqual(n['type'],'INTERFACE_OF');self.assertEqual(n['properties']['role'],'opening-host');self.assertEqual(n['target'],r['target'])
 def test_localized_boundaries(self):self.assertTrue(all(r['properties']['rangeState']=='localized-by-existing-geometry' and r['properties']['localBoundaryIds'] for r in M['relationships'] if r['type']=='BOUNDARY_PARTICIPANT'))
 def test_perimeter(self):self.assertAlmostEqual(A['D03']['T02']['perimeterM'],28.08);self.assertAlmostEqual(A['D03']['T02']['netSolidBoundaryM'],17.72)
 def test_columns_counted(self):b=next(b for b in A['D03']['T02']['segments'] if b['id']=='N');self.assertAlmostEqual(b['solidLengthM'],.6);self.assertEqual(len([p for p in b['participants'] if p['role']=='column-section']),4)
 def test_opening_subtracted(self):b=next(b for b in A['D03']['T02']['segments'] if b['id']=='S');self.assertAlmostEqual(b['solidLengthM'],7.76)
 def test_cover_not_solid(self):r=next(r for r in P['relationships'] if r['id']=='BOUND-S05-S04');self.assertEqual(r['properties']['netContributionM'],0)
 def test_intervals_union(self):self.assertEqual(merge_intervals([[0,1],[.5,2],[2,3]],4),[[0.,3.]])
 def test_no_forced_type(self):self.assertEqual(A['D03']['T02']['classifiedState'],'out-of-scope-for-legacy-four-side-rule')
 def test_gate_two_sides(self):q=next(x for x in A['D03']['T03'] if x['uid']=='V01:I05');self.assertEqual([round(x['offsetYM'],2) for x in q['sideBoundaryMappings']],[.12,-.12]);self.assertAlmostEqual(q['relativePosition'],.5)
 def test_open_boundary_partial(self):p=node(M,'I04')['properties'];self.assertEqual(p['startChainageM'],.02);self.assertEqual(p['endChainageM'],9.34);self.assertNotEqual(p['widthM'],p['referenceLengthM']);self.assertEqual(p['clearWidthState'],'not-established')
 def test_context_and_bidirection(self):self.assertEqual([r['path']['crossings'] for r in A['D03']['T04']['paths']],[2,2]);self.assertEqual(A['D03']['T04']['paths'][0]['path']['nodes'],['V01:S06','V01:S05','V01:S04'])
 def test_no_legacy_support_in_current_analysis(self):self.assertFalse(any(x.startswith('V01:R0') and next(r for r in P['relationships'] if r['properties']['uid']==x)['type']=='SUPPORTS_SYSTEM' for x in A['D03']['T04']['relationships']))
 def test_local_area(self):a=A['D03']['T05'];self.assertAlmostEqual(a['scopeAreaM2'],115.2);self.assertAlmostEqual(a['spaceUnionAreaM2'],58.2048);self.assertIsNone(a['wholeDwellingRatio']);self.assertEqual(a['excludedBuildings'],['V01:B02']);self.assertEqual(a['excludedSpaces'],['V01:S06'])
 def test_use_not_transplanted(self):self.assertFalse(any('晾晒' in x['use'] for x in A['D03']['T06']['byUse']));self.assertEqual(A['D03']['T06']['knownSpaceCount'],3)
 def test_source_upgrade_invalidates(self):
  def f(p):
   node(p,'EV09')['properties']['sourceVersion']='2.0'
   for r in p['relationships']:
    if r['id']=='SRC-B02':r['properties']['sourceVersion']='2.0'
  a=analyze_mutation(f);self.assertIn('pinned-source-version-mismatch',a['D01']['comparison']['issues'])
 def test_units_invalid(self):a=analyze_mutation(lambda p:node(p,'B02')['properties'].__setitem__('unit','cm'));self.assertEqual(a['D01']['comparison']['status'],'invalid-input')
 def test_missing_value_invalid(self):a=analyze_mutation(lambda p:node(p,'B02')['properties'].pop('eaveZM'));self.assertEqual(a['D01']['comparison']['status'],'invalid-input')
 def test_geometry_version_invalid(self):a=analyze_mutation(lambda p:node(p,'B02')['properties'].__setitem__('geometryVersion','new'));self.assertEqual(a['D01']['comparison']['status'],'invalid-input')
 def test_scenario_invalid(self):a=analyze_mutation(lambda p:node(p,'B02')['properties'].__setitem__('scenario','different'));self.assertEqual(a['D01']['comparison']['status'],'invalid-input')
 def test_cache_invalid(self):a=analyze_mutation(lambda p:node(p,'CMP01')['properties'].__setitem__('valueM',2.));self.assertIn('comparison-cache-mismatch',a['D01']['comparison']['issues'])
 def test_missing_field_support(self):
  def f(p):
   for r in p['relationships']:
    if r['id']=='SRC-B02':r['properties']['fields'].remove('eaveZM')
  self.assertEqual(analyze_mutation(f)['D01']['comparison']['status'],'invalid-input')
 def test_changed_geometry_same_id_stale_dimensions_rejected(self):
  m=copy.deepcopy(M);node(m,'S01')['geometry']['max'][0]+=.2
  with self.assertRaisesRegex(ValueError,'Stale dimensions'):validate_model(m)
 def test_updated_attribute_same_id_allowed(self):
  m=copy.deepcopy(M);n=node(m,'S01');n['properties']['measurementBoundaryBasis']+='；同对象补充口径说明';self.assertTrue(validate_model(m));self.assertEqual(n['id'],'S01');self.assertEqual(len(m['nodes']),len(M['nodes']))
 def test_boundary_gap_rejected(self):
  m=copy.deepcopy(M);node(m,'S05')['properties']['boundarySegments'][0]['polyline'][0][0]=.14
  with self.assertRaises(ValueError):boundary_qualification(m)
 def test_wrong_slice_rejected(self):
  m=copy.deepcopy(M);node(m,'S05')['properties']['analysisSliceZM']=3
  with self.assertRaises(ValueError):boundary_qualification(m)
 def test_gate_reference_mismatch_rejected(self):
  m=copy.deepcopy(M);node(m,'I05')['properties']['startChainageM']=3.88
  with self.assertRaises(ValueError):interface_qualification(m)
 def test_bad_actor_rejected(self):
  def f(p):
   for r in p['relationships']:
    if r['type']=='DIRECT_ACCESS_TO':r['properties']['actor']='unqualified'
  with self.assertRaises(ValueError):analyze_mutation(f)
 def test_mixed_floor_rejected(self):
  with self.assertRaises(ValueError):analyze_mutation(lambda p:node(p,'S04')['properties'].__setitem__('groundZM',3.))
 def test_wrong_units_or_source_datum(self):
  def f(p):
   for r in p['relationships']:
    if r['id']=='DATUM-B02':r['target']='V01:DIM-R01'
  self.assertIn('different-datum',analyze_mutation(f)['D01']['comparison']['issues'])
 def test_manifest_all_old_nodes(self):
  m=json.loads((W/'candidate/fix-map.json').read_text());old=json.loads((W/'db/before/graph.json').read_text());self.assertEqual({n['key'] for n in old['nodes']},{'V01:'+id for id in m['preservedNodeIds']}|{'V01:SOURCE'});self.assertEqual(len(m['preservedNodeIds'])+1,len(old['nodes']))
 def test_relation_assertion_source(self):
  for r in M['relationships']:
   p=r['properties'];self.assertEqual(p['assertionSourceVersion'],node(M,'EV01')['properties']['sourceVersion']);self.assertEqual(M['relationships'][int(p['assertionLocator'].split('/')[-1])]['id'],r['id'])
   if r['type']=='HAS_SOURCE':self.assertEqual(p['sourceUid'],'V01:'+r['target'])
   else:self.assertEqual(p['sourceVersion'],node(M,'EV01')['properties']['sourceVersion'])
 def test_input_version_distinct_from_assertion(self):
  r=rel(M,'COMPARES_SUBJECT')['properties'];self.assertEqual(r['expectedSourceVersion'],'1.1');self.assertNotEqual(r['expectedSourceVersion'],r['sourceVersion'])
 def test_eave_width_ratio(self):
  d={x['uid']:x for x in A['D01']['dimensions']};self.assertAlmostEqual(d['V01:B01']['ownEaveHeightWidthRatio'],3.2666666666666666/9.6);self.assertAlmostEqual(d['V01:B02']['ownEaveHeightWidthRatio'],4/6)
 def test_building_dimension_mismatch_rejected(self):
  for id in ['B01','B02']:
   m=copy.deepcopy(M);node(m,id)['properties']['widthM']=999
   with self.assertRaisesRegex(ValueError,'Stale building dimensions'):validate_model(m)
 def test_building_footprint_mismatch_rejected(self):
  m=copy.deepcopy(M);node(m,'B02')['properties']['footprintXY'][0]=9
  with self.assertRaisesRegex(ValueError,'Stale building footprint'):validate_model(m)
 def test_comparison_own_scenario_rejected(self):self.assertIn('comparison-scenario-mismatch',analyze_mutation(lambda p:node(p,'CMP01')['properties'].__setitem__('scenario','OTHER'))['D01']['comparison']['issues'])
 def test_use_source_upgrade_rejected(self):self.assertEqual(analyze_mutation(lambda p:node(p,'EV01')['properties'].__setitem__('sourceVersion','NEW'))['D03']['T06']['knownSpaceCount'],0)
 def test_changed_boundary_cache_rejected(self):
  def f(p):next(r for r in p['relationships'] if r['id']=='BOUND-S05-C02')['properties']['solidIntervalBoundsM']=[]
  with self.assertRaisesRegex(ValueError,'Boundary cache differs'):analyze_mutation(f)
 def test_migration_after_is_final_record(self):
  before=json.loads((W/'originals/model.json').read_text());mapping=json.loads((W/'candidate/extension-map.json').read_text());self.assertEqual(mapping['preservedRelationshipIds'],[r['id'] for r in before['relationships']])
  for r in before['relationships']:
   current=next(x for x in M['relationships'] if x['id']==r['id']);self.assertEqual([r[k] for k in ['source','target','type']],[current[k] for k in ['source','target','type']])
 def test_analysis_independent_of_record_order(self):
  p=copy.deepcopy(P);p['nodes'].reverse();p['relationships'].reverse();self.assertEqual(analyze(p),A)
 def test_analysis_matches_saved_actual_readback(self):
  f=W/'db/V01-readback.json'
  if f.exists():self.assertEqual(analyze(json.loads(f.read_text())),A)
  else:self.skipTest('Actual readback not yet available')
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(UnifiedTests);r=unittest.TextTestRunner(verbosity=2).run(suite);out=W/'tests/results.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'count':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'status':'passed' if r.wasSuccessful() else 'failed','scope':'local source/payload and negative parameters; no persisted bad data'},ensure_ascii=False,indent=2)+'\n');sys.exit(not r.wasSuccessful())
