(function (root) {
  'use strict';
  const collectionNames = ['places','buildings','components','feature_definitions','type_definitions','sources','records','relations','analyses'];
  const requiredRecordFields = ['id','subject_id','feature_id','kind','value','unit','observed_at','method','observation_status','review_status','evidence','notes'];
  const observedLabels = {observed:'已观察',confirmed_absent:'确认不存在',not_observed:'未观察',uncertain:'无法判断'};
  const reviewLabels = {pending:'待复核',checked:'已复核',disputed:'有分歧'};
  function buildIndex(data) {
    const index = {objects:new Map(),features:new Map(),types:new Map(),sources:new Map(),records:new Map()};
    for (const [group,kind] of [['places','place'],['buildings','building'],['components','component']]) {
      for (const item of data[group]) index.objects.set(item.id,{...item,node_kind:kind});
    }
    for (const [group,key] of [['feature_definitions','features'],['type_definitions','types'],['sources','sources'],['records','records']]) {
      for (const item of data[group]) index[key].set(item.id,item);
    }
    return index;
  }
  function validateDataset(data) {
    const errors=[],warnings=[];
    if (!data || typeof data!=='object' || Array.isArray(data)) return {errors:['数据必须是一个完整对象。'],warnings};
    if (!data.meta || data.meta.schema_version!=='0.1') errors.push('需要版本为0.1的数据说明。');
    if (!data.meta || !['demo','research'].includes(data.meta.mode)) errors.push('数据模式应为演示或研究。');
    for (const name of collectionNames) if (!Array.isArray(data[name])) errors.push('缺少数据列表：'+name);
    if (errors.length) return {errors,warnings};
    const ids=new Set();
    for (const name of collectionNames) {
      for (const item of data[name]) {
        if (!item || typeof item!=='object' || typeof item.id!=='string' || !item.id.trim()) {errors.push(name+'存在没有编号的记录。');continue;}
        if (ids.has(item.id)) errors.push('编号重复：'+item.id);
        ids.add(item.id);
      }
    }
    if (errors.length) return {errors,warnings};
    const i=buildIndex(data);
    const places=new Set(data.places.map(x=>x.id));
    const buildings=new Set(data.buildings.map(x=>x.id));
    const componentKinds=['roof','gable','wall','door','window','decoration','other'];
    for (const o of [...data.places,...data.buildings,...data.components]) if (typeof o.label!=='string' || !o.label.trim()) errors.push('对象名称缺失：'+o.id);
    for (const b of data.buildings) if (b.place_id && !places.has(b.place_id)) errors.push('建筑位置编号未找到：'+b.id);
    for (const c of data.components) {
      if (!buildings.has(c.building_id)) errors.push('构件所属建筑未找到：'+c.id);
      if (!componentKinds.includes(c.kind)) errors.push('构件类别不支持：'+c.id);
    }
    for (const f of data.feature_definitions) {
      if (!f.label || !Array.isArray(f.applicable_to) || !f.applicable_to.length || !['type','number','text'].includes(f.value_kind) || !f.definition || !f.version) errors.push('特征定义不完整：'+f.id);
    }
    for (const t of data.type_definitions) if (!t.label || !t.scope || !t.criterion || !t.version) errors.push('类型名称、尺度、规则或版本缺失：'+t.id);
    for (const s of data.sources) {
      if (!s.label || !s.kind) errors.push('来源名称或类别缺失：'+s.id);
      if (s.uri!==null && s.uri!==undefined && typeof s.uri!=='string') errors.push('来源地址格式错误：'+s.id);
    }
    for (const r of data.records) {
      const missingFields=requiredRecordFields.filter(key=>!Object.prototype.hasOwnProperty.call(r,key));
      if (missingFields.length) errors.push('记录缺少必需字段：'+r.id+'（'+missingFields.join('、')+'）');
      const obj=i.objects.get(r.subject_id), f=i.features.get(r.feature_id);
      if (!obj) errors.push('记录对象未找到：'+r.id);
      if (!f) errors.push('记录字段未找到：'+r.id);
      if (!['observation','measurement','classification','interpretation','relation'].includes(r.kind)) errors.push('记录方法类别不支持：'+r.id);
      if (!Object.prototype.hasOwnProperty.call(observedLabels,r.observation_status)) errors.push('观察状态不支持：'+r.id);
      if (!Object.prototype.hasOwnProperty.call(reviewLabels,r.review_status)) errors.push('复核状态不支持：'+r.id);
      if (!Array.isArray(r.evidence)) {errors.push('记录证据必须是列表：'+r.id);continue;}
      if (!r.method || !r.method.label) errors.push('获取方法未填写：'+r.id);
      if (obj && f) {
        const scope=obj.node_kind==='component'?obj.kind:obj.node_kind;
        if (!Array.isArray(f.applicable_to) || !f.applicable_to.includes(scope)) errors.push('字段与对象尺度不符：'+r.id);
        if (r.observation_status==='observed') {
          if (r.value===null || r.value===undefined) errors.push('已观察记录需要取值：'+r.id);
          if (f.value_kind==='number' && (typeof r.value!=='number' || !Number.isFinite(r.value))) errors.push('数值字段取值错误：'+r.id);
          if (f.value_kind==='number' && r.unit!==f.unit) errors.push('量测单位与字段定义不一致：'+r.id);
          if (f.value_kind==='text' && typeof r.value!=='string') errors.push('文本字段取值错误：'+r.id);
          if (f.value_kind==='type') {
            const type=r.value && i.types.get(r.value.type_id);
            if (!type) errors.push('类型编号未找到：'+r.id);
            else if (type.scope!==scope) errors.push('类型尺度与记录对象不符：'+r.id);
          }
          if (!r.evidence.length) errors.push('已观察记录缺少证据：'+r.id);
        } else if (r.value!==null) errors.push('未知或确认不存在的记录应留空取值：'+r.id);
      }
      if (r.observation_status==='confirmed_absent' && !r.evidence.length) errors.push('确认不存在需要检查范围及证据：'+r.id);
      for (const e of r.evidence) {
        if (!e || !i.sources.has(e.source_id)) errors.push('证据来源未找到：'+r.id);
        if (!e || !e.locator || typeof e.locator.description!=='string' || !e.locator.description.trim()) errors.push('证据定位未填写：'+r.id);
      }
      if (data.meta.mode==='research' && r.observation_status==='observed' && !r.observed_at) warnings.push('观察日期未填写：'+r.id);
      if (data.meta.mode==='research') for (const e of r.evidence) {
        const s=e && i.sources.get(e.source_id);
        if (s && (s.is_demo || !s.uri)) warnings.push('证据尚无可回查文件或仍为占位：'+r.id);
      }
      if (r.supersedes_record_id && !i.records.has(r.supersedes_record_id)) errors.push('被修订记录未找到：'+r.id);
      if (r.supersedes_record_id && !r.revision_reason) errors.push('修订理由缺失：'+r.id);
    }
    for (const relation of data.relations) {
      if (!i.objects.has(relation.source_id) || !i.objects.has(relation.target_id)) errors.push('位置或组合关系对象未找到：'+relation.id);
      if (!relation.label || !Array.isArray(relation.evidence_record_ids) || !relation.evidence_record_ids.length) errors.push('位置或组合关系缺少名称和证据记录：'+relation.id);
      else for (const id of relation.evidence_record_ids) if (!i.records.has(id)) errors.push('关系依据记录未找到：'+relation.id);
    }
    for (const a of data.analyses) {
      if (!a.label || !a.scope || !a.method || !Array.isArray(a.record_ids) || !Array.isArray(a.object_ids)) errors.push('分析范围、方法或依据缺失：'+a.id);
      else {
        for (const id of a.record_ids) if (!i.records.has(id)) errors.push('分析依据记录未找到：'+a.id);
        for (const id of a.object_ids) if (!i.objects.has(id)) errors.push('分析对象未找到：'+a.id);
      }
    }
    if (data.meta.mode==='research') {
      const demoItems=[...data.places,...data.buildings,...data.components].some(x=>x.identity_status==='demo') || data.sources.some(x=>x.is_demo);
      if (demoItems) errors.push('研究数据含演示对象或演示来源；请分开录入。');
    }
    return {errors,warnings:[...new Set(warnings)]};
  }
  function valueLabel(r,index) {
    if (r.observation_status!=='observed') return observedLabels[r.observation_status] || '未填写';
    if (r.value && typeof r.value==='object' && r.value.type_id) return index.types.get(r.value.type_id)?.label || '类型未找到';
    return String(r.value)+(r.unit ? ' '+r.unit : '');
  }
  function formatRecord(r,index) { return valueLabel(r,index)+' · '+(reviewLabels[r.review_status] || '未复核'); }
  function recordsForBuilding(data,bid) {
    const subjects=new Set([bid,...data.components.filter(c=>c.building_id===bid).map(c=>c.id)]);
    return data.records.filter(r=>subjects.has(r.subject_id));
  }
  function comparisonCell(data,bid,featureId,index) {
    const records=recordsForBuilding(data,bid).filter(r=>r.feature_id===featureId);
    if (!records.length) return {text:'未录入',records:[],status:'empty'};
    const texts=[...new Set(records.map(r=>valueLabel(r,index)))];
    // Multiple instances may legitimately vary. Preserve every record; never choose a first value.
    const status=records.some(r=>r.review_status==='disputed')?'disputed':texts.length>1?'multiple':records.every(r=>r.review_status==='checked')?'checked':'pending';
    const suffix=status==='disputed'?'有分歧':status==='multiple'?'多个实例／记录':reviewLabels[status] || '';
    return {text:texts.join(' / ')+(suffix?'（'+suffix+'）':''),records,status};
  }
  function buildEdges(data) {
    const edges=[];
    const add=(source,target,label,recordId)=>edges.push({source,target,label,record_id:recordId||null});
    for (const b of data.buildings) if (b.place_id) add(b.id,b.place_id,'位于');
    for (const c of data.components) add(c.building_id,c.id,'包含');
    for (const r of data.records) {
      add(r.id,r.subject_id,'针对',r.id); add(r.id,r.feature_id,'记录字段',r.id);
      if (r.value?.type_id) add(r.id,r.value.type_id,'判读为',r.id);
      for (const e of r.evidence) add(r.id,e.source_id,'依据',r.id);
    }
    for (const r of data.relations) add(r.source_id,r.target_id,r.label,r.evidence_record_ids?.[0]);
    for (const a of data.analyses) for (const rid of a.record_ids) add(a.id,rid,'汇总');
    return edges;
  }
  const api={buildIndex,validateDataset,valueLabel,formatRecord,recordsForBuilding,comparisonCell,buildEdges,observedLabels,reviewLabels};
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  if (root) root.GraphCore=api;
})(typeof window!=='undefined'?window:null);
