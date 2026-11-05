"""Rehydrate extension inputs from actual LPG values, not the embedded snapshot alone."""
import copy,json

def require(ok,message):
 if not ok:raise ValueError(message)

def rehydrate(graph):
 N={n['properties']['uid']:n for n in graph['nodes']};R={r['properties']['uid']:r for r in graph['relationships']}
 model=json.loads(N['V01:SOURCE']['properties']['rawModelJson'])
 require(len(N)==len(graph['nodes']) and len(R)==len(graph['relationships']),'Duplicate readback identity')
 require(set(N)=={'V01:'+n['id'] for n in model['nodes']}|{'V01:SOURCE'},'Unexpected readback object set')
 require(set(R)=={'V01:'+r['id'] for r in model['relationships']},'Unexpected readback relationship set')
 for n in model['nodes']:
  row=N.get('V01:'+n['id']);require(row is not None,'Missing readback object '+n['id']);p=row['properties']
  require(p.get('id')==n['id'] and p.get('caseId')=='V01' and p.get('datasetId')=='V01','Readback object identity')
  n['name']=p['name'];n['class']=p['class'];n['labels']=[x for x in row['labels'] if x not in ['KGItem','V01','Demo','Entity']]
  require(n.get('geometry') is None or 'geometryJson' in p,'Missing actual geometry '+n['id'])
  n['geometry']=json.loads(p['geometryJson']) if 'geometryJson' in p else None
  n['evidence']=copy.deepcopy(p.get('evidenceIds',[]))
  for k,v in list(n['properties'].items()):
   packed=isinstance(v,dict) or isinstance(v,list) and any(isinstance(x,(dict,list)) for x in v)
   key=k+'Json' if packed else k
   if key not in p:n['properties'].pop(k)
   else:n['properties'][k]=json.loads(p[key]) if packed else copy.deepcopy(p[key])
 for r in model['relationships']:
  row=R.get('V01:'+r['id']);require(row is not None,'Missing readback relation '+r['id']);p=row['properties']
  require(p.get('id')==r['id'] and p.get('caseId')=='V01' and p.get('datasetId')=='V01','Readback relationship identity')
  r['source']=row['source'].removeprefix('V01:');r['target']=row['target'].removeprefix('V01:');r['type']=row['type']
  r['status']=p.get('recordStatus');r['evidence']=copy.deepcopy(p.get('evidenceIds',[]))
  for k,v in list(r['properties'].items()):
   packed=isinstance(v,dict) or isinstance(v,list) and any(isinstance(x,(dict,list)) for x in v)
   key=k+'Json' if packed else k
   if key not in p:r['properties'].pop(k)
   else:r['properties'][k]=json.loads(p[key]) if packed else copy.deepcopy(p[key])
  if r['type']=='HAS_SOURCE':
   original={n['id']:n for n in model['nodes']}[r['source']]['properties']
   r['properties']['fields']=[f[:-4] if f.endswith('Json') and f[:-4] in original and isinstance(original[f[:-4]],(list,dict)) else f for f in r['properties'].get('fields',[])]
 return model

def validate_extension_sources(m):
 """Field, current source version, pointer and relation assertions must agree."""
 N={n['id']:n for n in m['nodes']};version=m['modelVersion'];contract=m['analysisContract'].get('extensionSourceFields',{})
 for id in ['W03','W10']:
  require('facadeRecords' in contract.get(id,[]),'Missing facade field-source contract')
 for id in ['B03','CG01','ST01','TP01']:
  require(id in N and set(N[id]['properties'])<=set(contract.get(id,[])),'Missing new-object field-source contract')
  p=N[id]['properties'];idx=next(i for i,n in enumerate(m['nodes']) if n['id']==id)
  require(N[id].get('geometry') is not None and p.get('geometrySourceLocator')=='/nodes/'+str(idx)+'/geometry','Invalid new-object geometry source pointer '+id)
  require(p.get('geometrySourceVersion')==version,'Invalid new-object geometry source version '+id)
 for id,fields in contract.items():
  require(id in N,'Extension source object absent')
  for f in fields:
   require(f in N[id]['properties'],'Missing extension field '+id+'.'+f)
   found=[]
   for r in m['relationships']:
    p=r['properties']
    if r['type']!='HAS_SOURCE' or r['source']!=id or f not in p.get('fields',[]):continue
    s=N.get(r['target']);loc=p.get('locator','').split('/')
    if s is None or not ('Source' in s['labels'] and 'SyntheticSource' in s['labels']):continue
    if p.get('sourceVersion')!=version or s['properties'].get('sourceVersion')!=version or p.get('sourceUid')!='V01:'+r['target']:continue
    if len(loc)!=4 or loc[1]!='nodes' or not loc[2].isdigit() or loc[3]!='properties':continue
    idx=int(loc[2])
    if idx>=len(m['nodes']) or m['nodes'][idx]['id']!=id:continue
    found.append(r)
   require(len(found)>=1,'Unsupported extension field '+id+'.'+f)
 for i,r in enumerate(m['relationships']):
  if not r['id'].startswith(('D04-','D05-','D06-','X-SRC-')):continue
  p=r['properties']
  require(p.get('assertionSourceUid')=='V01:EV01' and p.get('assertionSourceVersion')==version and p.get('assertionLocator')=='/relationships/'+str(i),'Extension relation assertion source')
 return True
