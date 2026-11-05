"""D06 five bounded synthesis tasks; derived views, never new building identities."""
import copy,math
import d04,d05
RULE_VERSION='D06-local-candidate-0.1'
EXCLUDED=['D02-internal-frame','D07-history','D08-perception']
def need(ok,msg):
 if not ok:raise ValueError(msg)
def schemes():
 return [
  {'id':'opening-cardinality','version':RULE_VERSION,'unit':'declared-exterior-wall-projection','mode':'exclusive','defining':['openingCount'],'auxiliary':['projectedOpeningAreaRatio','equalSpacingResidualsM'],'rules':[{'code':'single-opening-local','when':{'openingCount':{'eq':1}}},{'code':'multiple-openings-local','when':{'openingCount':{'ge':2}}}],'meaning':'洞口数量结构的描述性候选，不是地域立面型；连续残差不设等级阈值'},
  {'id':'complete-surface-material','version':RULE_VERSION,'unit':'declared-exterior-wall-projection','mode':'exclusive','defining':['completeMaterialCount'],'auxiliary':['knownCoverage'],'rules':[{'code':'single-material-complete-domain','when':{'completeMaterialCount':{'eq':1}}},{'code':'multiple-materials-complete-domain','when':{'completeMaterialCount':{'ge':2}}}],'meaning':'净域内完整已知的表层配置；关键未知不归混合或其他型，不推芯材'}]
def classify(features,scheme):
 need(scheme['mode'] in ['exclusive','multi-label'],'classification mode')
 if any(features.get(f) is None for f in scheme['defining']):return {'state':'unknown','matches':[],'reason':'关键定义性输入未知；不补值'}
 matched=[]
 for rule in scheme['rules']:
  ok=True
  for f,ops in rule['when'].items():
   need(f in scheme['defining'],'condition not declared as defining')
   x=features.get(f);need(type(x) in (int,float) and math.isfinite(x),'invalid feature')
   for op,v in ops.items():
    need(op in ['eq','ge'] and type(v) in (int,float) and math.isfinite(v),'invalid predicate')
    ok=ok and (x==v if op=='eq' else x>=v)
  if ok:matched.append(rule['code'])
 state='known-unmatched' if not matched else 'rule-conflict' if scheme['mode']=='exclusive' and len(matched)>1 else 'candidate-assigned'
 return {'state':state,'matches':sorted(matched),'reason':'本研究候选几何结构规则；不是经样本支持的建筑类型'}
def extend(model):
 c=model.setdefault('analysisContract',{})
 need('D06' not in c,'D06 contract already exists; do not overwrite')
 c['D06']={'version':RULE_VERSION,'sourceVersion':model['modelVersion'],'scenario':'V01-T0','excluded':EXCLUDED[:],'schemes':schemes(),
 'localPairs':[{'id':'D06-P01','facadeHostId':'W10','courtyardId':'S05','viaInterfaceId':'I05','meaning':'同一院门分别定位院墙外侧局部和前院边界；不配对主屋北墙与前院'}],
 'grouping':'same-dwelling-membership-only','sameDwellingOwner':'U01','groupComparison':'not-enabled-single-selected-synthetic-collection','buildingAggregation':'not-defined','evidenceIndependence':'all-current-values-share-EV01-synthetic-assignment','empiricalFrequency':'not-estimated'}
 return model
def validate(m):
 try:
  c=m['analysisContract']['D06'];need(c['version']==RULE_VERSION and c['sourceVersion']==m['modelVersion'] and c['scenario']=='V01-T0','D06 version/scenario')
  need(c['excluded']==EXCLUDED and c['schemes']==schemes(),'D06 scope/rule contents changed without implementation review')
  need(c['buildingAggregation']=='not-defined' and c['empiricalFrequency']=='not-estimated','Unreviewed aggregation/frequency')
  need(c['groupComparison']=='not-enabled-single-selected-synthetic-collection','Unreviewed group comparison')
  need(c['localPairs']==[{'id':'D06-P01','facadeHostId':'W10','courtyardId':'S05','viaInterfaceId':'I05','meaning':'同一院门分别定位院墙外侧局部和前院边界；不配对主屋北墙与前院'}],'Unreviewed local pairing')
  N={n['id']:n for n in m['nodes']};R=m['relationships']
  for x in c['localPairs']:
   need(all(x[f] in N for f in ['facadeHostId','courtyardId','viaInterfaceId']),'Pair object missing')
   for target,role in [(x['facadeHostId'],'opening-host'),(x['courtyardId'],'side-a')]:
    edges=[r for r in R if r['source']==x['viaInterfaceId'] and r['target']==target and r['type']=='INTERFACE_OF' and r['properties'].get('role')==role]
    need(len(edges)==1,'Pair must be supported by unique actual interface role')
   need(any(r['type']=='BOUNDARY_PARTICIPANT' and r['source']==x['courtyardId'] and r['target']==x['facadeHostId'] for r in R),'Pair lacks actual courtyard boundary participation')
  need(c['sameDwellingOwner']=='U01' and c['grouping']=='same-dwelling-membership-only','Grouping basis changed')
 except (KeyError,TypeError,IndexError) as e:raise ValueError('Invalid D06 structure: '+str(e)) from e
 return True

def analyze(m):
 validate(m);f=d04.analyze(m);g=d05.analyze(m);N={n['id']:n for n in m['nodes']};R=sorted(m['relationships'],key=lambda r:r['id']);c=m['analysisContract']['D06'];indices={n['id']:i for i,n in enumerate(m['nodes'])}
 def source_refs(id):
  return [{'relationshipId':r['id'],'sourceId':r['target'],'fields':r['properties']['fields'],'locator':r['properties']['locator'],'sourceVersion':r['properties']['sourceVersion']} for r in R if r['source']==id and r['type']=='HAS_SOURCE']
 buildings=[]
 for r in g['T01']['members']:
  id=r['id'];p=N[id]['properties'];owners=sorted(x['source'] for x in R if x['type']=='BOT_HAS_BUILDING' and x['target']==id)
  buildings.append({'objectId':id,'statisticalUnit':'building','ownerIds':owners,'independence':'同U01的B01/B02不作为独立宅院；B03邻宅身份为人工指定',
   'fields':{k:p[k] for k in ['groundZM','eaveZM','ridgeZM']},'commonDatum':'DATUM01','scenario':p['scenario'],'sourceRefs':source_refs(id),
   'excludedComparisons':['不同axis/outer口径的建筑净距','三维实体接触','无汇总规则的整栋立面类型'],'internalFrame':'excluded-from-current-analysis'})
 rows=[];alloc=[]
 for a,b,s in zip(f['T01'],f['T02'],f['T03']):
  need(a['regionId']==b['regionId']==s['regionId'],'Facade join mismatch')
  features={'openingCount':b['openingCount'],'completeMaterialCount':len(s['materialAreasM2']) if s['state']=='known' else None}
  row={'unitId':a['regionId'],'hostId':a['hostId'],'ownerId':a['ownerId'],'statisticalUnit':'declared-exterior-wall-projection','fields':features,
       'continuous':{'projectedOpeningAreaRatio':b['projectedOpeningAreaRatio'],'knownCoverage':s['knownCoverage']},'materialState':s['state'],'color':'conditional-not-enabled','decoration':'unknown',
       'sourceRefs':source_refs(a['hostId']),'locator':'/nodes/'+str(indices[a['hostId']])+'/properties/facadeRecords','buildingAggregation':'not-defined'}
  rows.append(row)
  for scheme in c['schemes']:
   alloc.append({'unitId':row['unitId'],'schemeId':scheme['id'],'ruleVersion':scheme['version'],'inputVersion':m['modelVersion'],**classify(features,scheme),'inputFields':{k:features[k] for k in scheme['defining']},'locator':row['locator']})
 distributions=[]
 for scheme in c['schemes']:
  selected=[x for x in alloc if x['schemeId']==scheme['id']];valid=[x for x in selected if x['state']=='candidate-assigned'];counts={}
  for x in valid:
   for code in x['matches']:counts.setdefault(code,[]).append(x['unitId'])
  distributions.append({'schemeId':scheme['id'],'countUnit':'local-wall-projection-record','declaredUnitIds':[x['unitId'] for x in selected],'validUnitIds':[x['unitId'] for x in valid],
     'excluded':[{'unitId':x['unitId'],'state':x['state']} for x in selected if x['state']!='candidate-assigned'],
     'counts':[{'code':k,'unitIds':sorted(v),'count':len(v),'shareInValidSyntheticRecords':len(v)/len(valid) if valid else None} for k,v in sorted(counts.items())]})
 joint=sorted(set.intersection(*(set(x['validUnitIds']) for x in distributions))) if distributions else []
 pairs=[]
 for x in c['localPairs']:
  fr=next(r for r in rows if r['hostId']==x['facadeHostId']);cp=N[x['courtyardId']]['properties'];refs=[r['id'] for r in R if r['source']==x['viaInterfaceId'] and r['type']=='INTERFACE_OF' and r['target'] in [x['facadeHostId'],x['courtyardId']]]
  pairs.append({'pairId':x['id'],'facadeUnitId':fr['unitId'],'facadeOwnerId':fr['ownerId'],'courtyardId':x['courtyardId'],'viaInterfaceId':x['viaInterfaceId'],'supportingRelationshipIds':refs,
      'facadeMaterialState':fr['materialState'],'courtyardCoverState':cp['coverState'],'combinationState':'partial-unknown','meaning':x['meaning'],'buildingFrequency':None,'noCartesianProduct':True})
 grouped={}
 for row in buildings:
  key='|'.join(row['ownerIds']) or 'standalone:'+row['objectId'];grouped.setdefault(key,[]).append(row['objectId'])
 return {
 'T01':{'status':'derived-synthetic-matrices','buildingElevationMatrix':buildings,'localFacadeMatrix':rows,'missingPolicy':'无、未知、不适用和体系排除分开；无补值；混口径字段不进入同一比较','sourceIndependence':'共同EV01来源，不是独立互证'},
 'T02':{'status':'synthetic-counting-demonstration-not-empirical-frequency','localDistributions':distributions,'jointValidUnitIds':joint,'jointValidCount':len(joint),'localPairs':pairs,'wholeBuildingCombinationFrequency':None,'meaning':'仅展示显式局部记录与配对的计数机制；不发布景宁或整栋组合频数'},
 'T03':{'status':'candidate-rule-demonstration','schemes':copy.deepcopy(c['schemes']),'allocations':alloc,'sensitivityStatus':'限定反例在执行测试中；未做真实样本稳定性或记录者一致性检验','noNewTypeEntities':True},
 'T04':{'status':'not-estimable','collectionId':'CG01','sameDwellingClusters':[{'cluster':k,'members':v} for k,v in sorted(grouped.items())],'reason':'仅一个人工选择的建筑组，无真实跨村／组团／地形分组及独立样本；不做显著性检验或时期演变'},
 'T05':{'status':'descriptive-synthetic-only','observations':[{'id':'D06-O01','statement':'同一院门关联院墙局部与前院，可以明确配对，但不能代表全部建筑立面。','objects':['W10','I05','S05'],'source':'EV01'},{'id':'D06-O02','statement':'共同基准檐口高差、自身檐高与街边界高度是不同量，不能互相替代。','objects':['B01','B02','W10','B03'],'source':'EV01'}],
 'candidateExplanations':[{'statement':'真实样本中若高度与地形对应，需检验取样、地坪口径与用途等竞争解释。','status':'untested-hypothesis-not-a-fact','independentEvidence':'absent'}],
 'unsupported':['历史成因','文化因果','民族专属性','地形适应动机','方法优越性'],'boundary':'几何与材料均为人工赋值；不以图边或同源设定证成因果。'}}
