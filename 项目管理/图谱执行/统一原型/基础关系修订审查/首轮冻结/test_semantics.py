"""Basic-relation positive/negative tests; no mutation reaches Neo4j."""
from pathlib import Path
import copy,json,sys,unittest
W=Path(__file__).parent;sys.path.insert(0,str(W/'tools'))
from compile_model import compile_model,validate_model
from analyze import analyze
import semantics as S
M,P=compile_model(W/'candidate/model.json');A=analyze(P)['basicRelations']
def n(m,id):return next(x for x in m['nodes'] if x['id']==id)
def r(m,id):return next(x for x in m['relationships'] if x['id']==id)
class BasicRelationsTests(unittest.TestCase):
 def test_no_new_objects(self):self.assertEqual({x['id'] for x in M['nodes']},{x['id'] for x in json.loads((W/'baseline/model-2.1.json').read_text())['nodes']})
 def test_only_five_new_edges(self):
  old=json.loads((W/'baseline/model-2.1.json').read_text());ids={x['id'] for x in old['relationships']};self.assertEqual({x['id'] for x in M['relationships'] if x['id'] not in ids},{'BOUND-'+a+'-'+b for a,b in S.REQUIRED_NEW})
 def test_localized_count(self):self.assertEqual(len(S.qualified_boundaries(M)),28)
 def test_four_veranda_columns(self):
  vals=[S.local_ranges(M,r(M,'BOUND-S04-C0'+str(i)))[0]['netLengthM'] for i in range(1,5)]
  for a,b in zip(vals,[.14,.28,.28,.14]):self.assertAlmostEqual(a,b)
  self.assertAlmostEqual(sum(vals),.84)
 def test_other_side_not_copied(self):self.assertAlmostEqual(S.local_ranges(M,r(M,'BOUND-S05-C01'))[0]['netLengthM'],.02);self.assertAlmostEqual(S.local_ranges(M,r(M,'BOUND-S04-C01'))[0]['netLengthM'],.14)
 def test_gate_outer_two_local_parts(self):
  x=S.local_ranges(M,r(M,'BOUND-S06-W10'))[0];self.assertEqual(x['deductedOpeningIds'],['I05']);self.assertEqual(len(x['intervalsM']),2);self.assertAlmostEqual(x['netLengthM'],.4)
 def test_gate_not_full_wall(self):self.assertLess(S.local_ranges(M,r(M,'BOUND-S06-W10'))[0]['netLengthM'],n(M,'W10')['properties']['lengthM'])
 def test_fifteen_original_relations_localized(self):
  for i in range(59,74):self.assertTrue(S.local_ranges(M,r(M,f'R{i:03}')))
 def test_no_wall_end_candidate_edges(self):self.assertFalse(any(r['source']=='S04' and r['target'] in ['W04','W05','W08','W09'] and r['type']=='BOUNDARY_PARTICIPANT' for r in M['relationships']))
 def test_wall_end_candidates_exposed(self):
  x=next(x for x in A['localizedBoundaries'] if x['spaceUid']=='V01:S04');ids={r['uid'] for seg in x['segments'] for r in seg['geometryCandidates']};self.assertEqual(ids,{'V01:W04','V01:W05','V01:W08','V01:W09'})
 def test_overlap_union(self):
  x=next(x for x in A['localizedBoundaries'] if x['spaceUid']=='V01:S04');self.assertGreater(sum(s['overlapDeductedM'] for s in x['segments']),0.)
 def test_roof_six_spaces(self):self.assertEqual(len(A['roofCoverage']),6)
 def test_roof_first_four_full(self):self.assertTrue(all(x['state']=='full-projection' for x in A['roofCoverage'][:4]))
 def test_court_partial_roof(self):
  x=next(x for x in A['roofCoverage'] if x['spaceUid']=='V01:S05');self.assertAlmostEqual(x['coveredAreaM2'],5.616);self.assertAlmostEqual(x['coverageRatio'],5.616/43.8048);self.assertEqual(x['overallCoverType'],'open-air-space-character')
 def test_no_roof_provider_not_universal_absence(self):self.assertEqual(A['roofCoverage'][-1]['state'],'none-from-this-provider')
 def test_roof_update_recomputes(self):
  m=copy.deepcopy(M);n(m,'RF01')['geometry']['y'][0]=-.3;self.assertAlmostEqual(S.roof_coverage(m)[4]['coveredAreaM2'],2.808)
 def test_unreconciled_roof_geometry_rejected(self):
  m=copy.deepcopy(M);n(m,'RF01')['geometry']['y'][0]=-.3
  with self.assertRaisesRegex(ValueError,'projections disagree'):S.validate(m)
 def test_interface_three_plan_gaps(self):
  x=A['interfaceOccupation'];self.assertEqual(len(x['planOpenLengthsM']),3)
  for v in x['planOpenLengthsM']:self.assertAlmostEqual(v,2.92)
 def test_interface_not_passage(self):self.assertFalse(A['interfaceOccupation']['clearanceValidated']);self.assertEqual(A['interfaceOccupation']['passageConclusion'],'not-established')
 def test_interface_endpoint_columns(self):self.assertEqual([x['uid'] for x in A['interfaceOccupation']['participants'] if x['role']=='endpoint-limit-no-positive-occupation'],['V01:C01','V01:C04'])
 def test_no_fake_interface_host(self):self.assertFalse(any(x['source']=='I04' and x['target'].startswith('C') for x in M['relationships']))
 def test_street_plan_level(self):x=A['streetReference'];self.assertAlmostEqual(x['intersectionAreaM2'],2.76);self.assertTrue(x['fullyWithinPlanProjection'] and x['sameDeclaredLevel']);self.assertFalse(x['semanticRelationPersisted'])
 def test_street_level_change_is_not_same(self):m=copy.deepcopy(M);n(m,'ST01')['geometry']['surfaceZM']=.1;self.assertFalse(S.street_reference(m)['sameDeclaredLevel'])
 def test_street_not_added_access(self):self.assertFalse(any(x['source']=='S06' and x['target']=='ST01' for x in M['relationships']))
 def test_all_objects_covered(self):self.assertEqual(len(A['objectCoverage']),56);self.assertEqual(len({r['uid'] for r in A['objectCoverage']}),56)
 def test_every_coverage_has_four_modes(self):self.assertTrue(all({'mandatory','optional','notApplicable','unknown'}<=set(x) for x in A['objectCoverage']))
 def test_missing_column_rejected(self):
  m=copy.deepcopy(M);m['relationships']=[x for x in m['relationships'] if x['id']!='BOUND-S04-C02']
  with self.assertRaisesRegex(ValueError,'required local boundary'):S.validate(m)
 def test_zero_cover_claim_rejected(self):
  m=copy.deepcopy(M);n(m,'S05')['properties']['coverStateMeaning']='zero-projection'
  with self.assertRaisesRegex(ValueError,'cover meaning'):S.validate(m)
 def test_wrong_source_field_rejected(self):
  m=copy.deepcopy(M);r(m,'SRC-S04')['properties']['fields'].remove('boundarySegments')
  with self.assertRaisesRegex(ValueError,'field provenance'):S.validate(m)
 def test_changed_local_cache_rejected(self):
  p=copy.deepcopy(P);r(p,'BOUND-S04-C01')['properties']['localNetLengthM']=99
  with self.assertRaisesRegex(ValueError,'Local boundary cache'):analyze(p)
 def test_missing_actual_local_field_rejected(self):
  p=copy.deepcopy(P);n(p,'S04')['properties'].pop('boundaryBasis')
  with self.assertRaises(ValueError):analyze(p)
 def test_bad_membership_rejected(self):
  m=copy.deepcopy(M);m['relationships']=[x for x in m['relationships'] if not (x['source']=='C01' and x['type']=='MEMBER_OF_ZONE')]
  with self.assertRaises(ValueError):S.validate(m)
 def test_unknown_windows_not_errors(self):self.assertTrue(S.validate(M));self.assertTrue(all('未实例化外侧空间' in next(x for x in A['objectCoverage'] if x['uid']=='V01:'+id)['unknown'] for id in ['I08','I09','I10']))
 def test_legacy_source_version_preserved(self):self.assertEqual(n(M,'EV09')['properties']['sourceVersion'],'1.1')
 def test_reversed_graph_order(self):p=copy.deepcopy(P);p['nodes'].reverse();p['relationships'].reverse();self.assertEqual(analyze(p)['basicRelations'],A)
 def test_no_paused_branches_reintroduced(self):
  old=json.loads((W/'baseline/model-2.1.json').read_text())
  for t in ['SUPPORTS_SYSTEM','DIRECT_ACCESS_TO']:self.assertEqual([r['id'] for r in old['relationships'] if r['type']==t],[r['id'] for r in M['relationships'] if r['type']==t])
if __name__=='__main__':unittest.main()
