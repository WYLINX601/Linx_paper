"""Regression cases for independent review F01-F04; no graph writes."""
from pathlib import Path
import copy,json,sys,unittest
W=Path(__file__).parent;sys.path.insert(0,str(W/'tools'))
import d04,d06
from compile_model import compile_model,validate_model
from analyze import analyze
from projection import rehydrate
M,P=compile_model(W/'candidate/model.json')
def node(m,id):return next(n for n in m['nodes'] if n['id']==id)
def pn(p,id):return next(n for n in p['nodes'] if n['properties']['uid']=='V01:'+id)
def material_case(unknown=False):
 q=copy.deepcopy(M);r=node(q,'W03')['properties']['facadeRecords'][0];t=r['surfaceRegions'][0]
 specs=[([0,0,9.6,1],'灰泥'),([0,1,1,2],'灰泥'),([2.2,1,9.6,2],'灰泥'),([0,2,9.6,3.6],'灰泥'),([1,1,2.2,2],'砖')]
 r['surfaceRegions']=[dict(copy.deepcopy(t),id=t['id']+'-'+str(i),rectUZ=b,material=mat) for i,(b,mat) in enumerate(specs)]
 if unknown:r['surfaceRegions'][-1].update(state='unknown',material=None)
 return q
class ReviewFixes(unittest.TestCase):
 def test_zero_net_material_not_counted(self):
  q=material_case();self.assertTrue(validate_model(q));s=d04.analyze(q)['T03'][0];a=d06.analyze(q)
  self.assertEqual(set(s['materialAreasM2']),{'灰泥'});self.assertEqual(len(s['zeroNetSurfaceRegions']),1)
  self.assertEqual(a['T01']['localFacadeMatrix'][0]['fields']['completeMaterialCount'],1)
  self.assertEqual(next(x for x in a['T03']['allocations'] if x['unitId']=='D04-W03-N' and x['schemeId']=='complete-surface-material')['matches'],['single-material-complete-domain'])
 def test_positive_net_second_material_counted(self):
  q=material_case();node(q,'W03')['properties']['facadeRecords'][0]['surfaceRegions'][0]['material']='砖'
  self.assertTrue(validate_model(q));self.assertEqual(d06.analyze(q)['T01']['localFacadeMatrix'][0]['fields']['completeMaterialCount'],2)
 def test_zero_net_unknown_not_unknown_net_wall(self):
  q=material_case(True);self.assertTrue(validate_model(q));self.assertEqual(d04.analyze(q)['T03'][0]['state'],'known')
 def test_missing_actual_geometry_rejected(self):
  p=copy.deepcopy(P);del pn(p,'C01')['properties']['geometryJson']
  with self.assertRaisesRegex(ValueError,'Missing actual geometry'):analyze(p)
 def test_changed_actual_geometry_rejects_stale_cache(self):
  p=copy.deepcopy(P);n=pn(p,'C01')['properties'];g=json.loads(n['geometryJson']);g['radius']=1.0;n['geometryJson']=json.dumps(g)
  with self.assertRaisesRegex(ValueError,'Boundary cache differs'):analyze(p)
 def test_extra_actual_relation_rejected(self):
  p=copy.deepcopy(P);r=copy.deepcopy(next(r for r in p['relationships'] if r['source']=='V01:I05' and r['target']=='V01:S05' and r['type']=='INTERFACE_OF'));r['properties'].update(id='EXTRA',uid='V01:EXTRA');p['relationships'].append(r)
  with self.assertRaisesRegex(ValueError,'Unexpected readback relationship set'):analyze(p)
 def test_duplicate_actual_relation_rejected(self):
  p=copy.deepcopy(P);p['relationships'].append(copy.deepcopy(p['relationships'][0]))
  with self.assertRaisesRegex(ValueError,'Duplicate readback identity'):analyze(p)
 def test_extra_actual_object_rejected(self):
  p=copy.deepcopy(P);n=copy.deepcopy(p['nodes'][0]);n['properties'].update(id='EXTRA',uid='V01:EXTRA');p['nodes'].append(n)
  with self.assertRaisesRegex(ValueError,'Unexpected readback object set'):analyze(p)
 def test_each_new_geometry_pointer_and_version_rejected(self):
  for id in ['B03','CG01','ST01','TP01']:
   for field,value in [('geometrySourceLocator','/nodes/9/geometry'),('geometrySourceVersion','stale-version')]:
    with self.subTest(id=id,field=field):
     q=copy.deepcopy(M);node(q,id)['properties'][field]=value
     with self.assertRaisesRegex(ValueError,'Invalid new-object geometry source'):validate_model(q)
 def test_actual_material_not_snapshot_recomputed(self):
  p=copy.deepcopy(P);n=pn(p,'W10')['properties'];r=json.loads(n['facadeRecordsJson']);r[0]['surfaceRegions'][1].update(state='known',material='灰泥');n['facadeRecordsJson']=json.dumps(r)
  self.assertEqual(analyze(p)['D04']['T03'][1]['state'],'known');self.assertEqual(pn(p,'SOURCE')['properties']['rawModelJson'],pn(P,'SOURCE')['properties']['rawModelJson'])
 def test_actual_relation_status_and_evidence_rehydrated(self):
  p=copy.deepcopy(P);r=p['relationships'][0];r['properties'].update(recordStatus='changed-status',evidenceIds=['EV08']);q=rehydrate(p);x=next(x for x in q['relationships'] if x['id']==r['id']);self.assertEqual(x['status'],'changed-status');self.assertEqual(x['evidence'],['EV08'])
if __name__=='__main__':unittest.main(verbosity=2)
