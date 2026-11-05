(function () {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const byId = (id) => document.getElementById(id);
  const core = window.GraphCore;
  const staticSchema = window.ARCH_STYLE_SCHEMA;
  let currentData = window.ARCH_STYLE_DATA;
  let currentIndex = core.buildIndex(currentData);
  let currentEdges = core.buildEdges(currentData);
  let currentValidation = core.validateDataset(currentData);
  let selectedBuildingId = currentData.buildings[0]?.id || null;
  let selectedComponentId = currentData.components.find((item) => item.building_id === selectedBuildingId)?.id || null;
  let selectedSubjectId = selectedComponentId || selectedBuildingId;
  let frameworkSelection = { kind: 'class', id: 'object' };
  let detailSelection = initialDetailSelection();

  const classInfo = new Map((staticSchema.core_classes || []).map((item) => [item.id, item]));
  const classNames = {
    object: '对象实例',
    feature_definition: '特征定义',
    record: '特征与分类记录',
    type_definition: '类型定义',
    source: '证据来源',
    analysis: '分析结果'
  };
  const nodeKindNames = {
    place: '位置背景',
    building: '建筑',
    component: '构件',
    feature: '字段定义',
    type: '类型规则',
    record: '记录',
    source: '证据来源'
  };
  const componentKindNames = {
    roof: '屋顶', gable: '山墙', wall: '墙体', door: '门', window: '窗', decoration: '装饰', other: '其他构件'
  };
  const objectScaleNames = { place: '位置背景', building: '建筑', component: '构件', roof: '屋顶', gable: '山墙', wall: '墙体', door: '门', window: '窗', decoration: '装饰', other: '其他构件' };
  const recordKindNames = {
    observation: '观察', measurement: '量测', classification: '分类', interpretation: '解释', relation: '关系'
  };
  const featureKindNames = { type: '类型字段', number: '数值字段', text: '文本字段' };
  const preferredCompareFeatureIds = ['roof_form', 'roof_pitch', 'window_form', 'window_width', 'surface_material'];
  const statusNames = { candidate: '候选', draft: '草案', active: '使用中', retired: '停用' };
  const identityNames = { demo: '演示对象', research: '研究对象（待核）', real: '真实对象（待核）', candidate: '待确认' };
  const recordFieldNames = {
    id: '记录编号', subject_id: '主体对象', feature_id: '特征字段', kind: '记录类别', value: '取值', unit: '单位',
    observed_at: '观察日期', historical_period: '历史时期', method: '获取方法', observation_status: '观察状态',
    review_status: '复核状态', evidence: '证据来源与定位', notes: '备注', supersedes_record_id: '被修订记录', revision_reason: '修订理由'
  };

  function defaultSubjectForBuilding(buildingId) {
    if (!buildingId) return null;
    if (currentData.records.some((record) => record.subject_id === buildingId)) return buildingId;
    const components = currentData.components.filter((item) => item.building_id === buildingId);
    return components.find((component) => currentData.records.some((record) => record.subject_id === component.id))?.id || components[0]?.id || buildingId;
  }

  function initialDetailSelection() {
    if (selectedSubjectId && currentIndex.objects.has(selectedSubjectId)) return { kind: 'object', id: selectedSubjectId };
    if (selectedSubjectId) return { kind: 'object', id: selectedSubjectId };
    const building = currentData.buildings[0];
    if (building) return { kind: 'object', id: building.id };
    const place = currentData.places[0];
    return place ? { kind: 'object', id: place.id } : null;
  }

  function nodeLabel(kind, id) {
    if (!id) return '未命名';
    const maps = { object: currentIndex.objects, feature: currentIndex.features, type: currentIndex.types, source: currentIndex.sources, record: currentIndex.records };
    const value = maps[kind]?.get(id);
    if (!value) return String(id);
    if (kind === 'record') {
      const feature = currentIndex.features.get(value.feature_id);
      return (feature?.label || '特征') + '记录';
    }
    return value.label || String(id);
  }

  function objectNodeKind(id) {
    return currentIndex.objects.get(id)?.node_kind || 'object';
  }

  function fieldLabel(id) {
    return currentIndex.features.get(id)?.label || id;
  }

  function scopeLabel(scope) {
    return objectScaleNames[scope] || scope || '未记录';
  }

  function statusName(status) {
    return statusNames[status] || (status ? '待核对' : '未记录');
  }

  function identityName(status) {
    return identityNames[status] || (status ? '待核对' : '未记录');
  }

  function endpointLabel(value) {
    const labels = {
      place: '位置背景', building: '建筑', component: '构件', 'building/component': '建筑或构件',
      record: '记录', classification_record: '分类记录', feature_definition: '字段定义',
      type_definition: '类型定义', source: '证据来源', analysis: '分析结果', object: '对象实例'
    };
    return labels[value] || value || '未记录';
  }

  function displayValue(value) {
    if (value === null || value === undefined || value === '') return '未记录';
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
    try { return JSON.stringify(value); } catch (_error) { return '未记录'; }
  }

  function typeLabel(id) {
    return currentIndex.types.get(id)?.label || id;
  }

  function sourceKindName(kind) {
    const names = { image: '影像', model: '三维模型', point_cloud: '点云', measurement: '量测', field_note: '调查记录', literature: '文献', other: '其他来源' };
    return names[kind] || kind || '未填写';
  }

  function clear(element) {
    element.replaceChildren();
  }

  function make(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined && text !== null) element.textContent = String(text);
    return element;
  }

  function makeNodeButton(kind, id, label, extraClass) {
    const button = make('button', `node-button${extraClass ? ` ${extraClass}` : ''}`, label || nodeLabel(kind, id));
    button.type = 'button';
    button.dataset.nodeKind = kind;
    button.dataset.nodeId = id;
    return button;
  }

  function appendDefinitionList(parent, pairs, className = 'detail-list') {
    const dl = make('dl', className);
    for (const [term, value] of pairs) {
      dl.append(make('dt', '', term), make('dd', '', value === null || value === undefined || value === '' ? '未记录' : String(value)));
    }
    parent.append(dl);
    return dl;
  }

  function addDetailSection(parent, title) {
    const section = make('section', 'detail-section');
    section.append(make('h4', '', title));
    parent.append(section);
    return section;
  }

  function statusLabel(status) {
    return core.observedLabels[status] || '未填写';
  }

  function reviewLabel(status) {
    return core.reviewLabels[status] || '未复核';
  }

  function recordValue(record) {
    if (record.observation_status !== 'observed') return statusLabel(record.observation_status);
    if (record.value && typeof record.value === 'object' && record.value.type_id) {
      return typeLabel(record.value.type_id);
    }
    return record.value === null || record.value === undefined ? '未记录' : String(record.value);
  }

  function safeSourceHref(uri) {
    if (typeof uri !== 'string' || !uri.trim()) return null;
    const value = uri.trim();
    if (/^(https?:|file:|zotero:)/i.test(value)) {
      try {
        const parsed = new URL(value, window.location.href);
        return ['http:', 'https:', 'file:', 'zotero:'].includes(parsed.protocol) ? value : null;
      } catch (_error) {
        return null;
      }
    }
    if (/^[a-z][a-z0-9+.-]*:/i.test(value) || value.startsWith('//') || /[\u0000-\u001f]/.test(value)) return null;
    return value;
  }

  function appendSourceLink(parent, source) {
    if (!source) {
      parent.append(make('span', '', '来源未找到'));
      return;
    }
    const href = safeSourceHref(source.uri);
    if (href) {
      const link = make('a', 'source-link', source.label || source.id);
      link.href = href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      parent.append(link);
      return;
    }
    parent.append(make('span', '', source.label || source.id));
    parent.append(make('span', 'source-hint', source.uri ? ' · 地址协议不允许，未生成链接' : ' · 待关联真实文件'));
  }

  function appendRecordDetail(parent, record) {
    const feature = currentIndex.features.get(record.feature_id);
    const typeValue = record.value && typeof record.value === 'object' && record.value.type_id ? currentIndex.types.get(record.value.type_id) : null;
    const detail = make('div', 'record-detail-body');
    appendDefinitionList(detail, [
      ['记录类别', recordKindNames[record.kind] || record.kind],
      ['对应对象', nodeLabel('object', record.subject_id)],
      ['对象编号', record.subject_id],
      ['字段', feature?.label || record.feature_id],
      ['取值', recordValue(record)],
      ['单位', record.unit || feature?.unit || '无 / 未记录'],
      ['观察状态', statusLabel(record.observation_status)],
      ['复核状态', reviewLabel(record.review_status)],
      ['观察日期', record.observed_at || '未记录'],
      ['历史时期', record.historical_period || '未记录'],
      ['获取方法', record.method?.label || '未记录'],
      ['工具 / 版本', [record.method?.tool, record.method?.version].filter(Boolean).join(' / ') || '未记录'],
      ['记录编号', record.id]
    ]);

    if (typeValue) {
      const typeSection = addDetailSection(detail, '分类规则');
      typeSection.append(make('p', 'detail-description', `${typeValue.label} · ${typeValue.criterion}`));
      appendDefinitionList(typeSection, [['适用尺度', scopeLabel(typeValue.scope)], ['规则版本', typeValue.version], ['规则状态', statusName(typeValue.status)]]);
    }

    const evidenceSection = addDetailSection(detail, '证据来源与定位');
    if (!Array.isArray(record.evidence) || record.evidence.length === 0) {
      evidenceSection.append(make('p', 'detail-description', '尚无关联证据。'));
    } else {
      for (const evidence of record.evidence) {
        const source = currentIndex.sources.get(evidence.source_id);
        const block = make('div', 'evidence-block');
        const heading = make('div', 'evidence-heading');
        if (source) appendSourceLink(heading, source);
        else heading.append(make('span', '', '来源未找到'));
        if (source) heading.append(make('span', 'kind-chip', sourceKindName(source.kind)));
        block.append(heading);
        const locator = evidence.locator || {};
        block.append(make('p', 'evidence-location', locator.description || '未记录定位'));
        const locationParts = [];
        if (locator.page) locationParts.push(`页码 ${locator.page}`);
        if (locator.figure) locationParts.push(`图 ${locator.figure}`);
        if (locator.region) locationParts.push(`区域 ${locator.region}`);
        if (locator.model_part) locationParts.push(`模型部位 ${locator.model_part}`);
        if (locationParts.length) block.append(make('p', 'evidence-location', locationParts.join(' · ')));
        evidenceSection.append(block);
      }
    }
    const notes = make('section', 'detail-section');
    notes.append(make('h4', '', '备注'));
    notes.append(make('p', 'note-text', record.notes || '未记录'));
    detail.append(notes);
    parent.append(detail);
  }

  function appendFeatureDetail(parent, feature) {
    parent.append(make('p', 'detail-description', feature.definition || '尚未填写定义。'));
    appendDefinitionList(parent, [
      ['字段编号', feature.id],
      ['适用尺度', Array.isArray(feature.applicable_to) ? feature.applicable_to.map(scopeLabel).join('、') : '未记录'],
      ['取值方式', featureKindNames[feature.value_kind] || feature.value_kind],
      ['单位', feature.unit || '无'],
      ['版本', feature.version || '未记录'],
      ['字段状态', statusName(feature.status)],
      ['必需内容', '编号、名称、定义、适用尺度、取值方式、单位、版本和状态']
    ]);
  }

  function appendTypeDetail(parent, type) {
    parent.append(make('p', 'detail-description', type.criterion || '尚未填写判别规则。'));
    appendDefinitionList(parent, [
      ['适用尺度', scopeLabel(type.scope)],
      ['规则版本', type.version || '未记录'],
      ['规则状态', statusName(type.status)]
    ]);
    const records = currentData.records.filter((record) => record.value?.type_id === type.id);
    if (records.length) {
      const section = addDetailSection(parent, '引用此类型的记录');
      const list = make('ul', 'linked-list');
      for (const record of records) {
        const item = make('li');
        item.append(makeNodeButton('record', record.id, `${nodeLabel('record', record.id)} · ${core.formatRecord(record, currentIndex)}`));
        list.append(item);
      }
      section.append(list);
    }
  }

  function appendSourceDetail(parent, source) {
    appendDefinitionList(parent, [
      ['来源类别', sourceKindName(source.kind)],
      ['来源文件', source.uri ? (safeSourceHref(source.uri) ? source.uri : '地址协议不允许，未显示') : '待关联真实文件'],
      ['版本', source.version || '未记录'],
      ['记录时间', source.captured_at || '未记录'],
      ['来源身份', source.is_demo ? '演示占位' : '非演示来源（仍需回查）']
    ]);
    if (source.uri && safeSourceHref(source.uri)) {
      const section = addDetailSection(parent, '打开来源');
      appendSourceLink(section, source);
    }
    const notes = addDetailSection(parent, '来源备注');
    notes.append(make('p', 'note-text', source.notes || '未记录'));
  }

  function appendObjectDetail(parent, object) {
    const kind = object.node_kind;
    const pairs = [['对象类别', nodeKindNames[kind] || kind], ['对象编号', object.id]];
    if (kind === 'building') {
      const place = currentIndex.objects.get(object.place_id);
      pairs.push(['位置背景', place?.label || '未关联']);
      pairs.push(['对象身份', identityName(object.identity_status)]);
    } else if (kind === 'component') {
      const building = currentIndex.objects.get(object.building_id);
      pairs.push(['构件类别', componentKindNames[object.kind] || object.kind]);
      pairs.push(['所属建筑', building?.label || '未关联']);
      pairs.push(['部位', object.position || '未记录']);
      pairs.push(['对象身份', identityName(object.identity_status)]);
    } else {
      pairs.push(['对象身份', identityName(object.identity_status)]);
    }
    appendDefinitionList(parent, pairs);
    const notes = addDetailSection(parent, '备注');
    notes.append(make('p', 'note-text', object.notes || '未记录'));
  }

  function renderEntityDetail(container, selection, mode = 'detail') {
    clear(container);
    if (!selection) {
      const placeholder = make('div', 'detail-placeholder');
      placeholder.append(make('span', 'detail-kicker', '节点详情'), make('h3', '', '尚无可显示的节点'), make('p', '', '导入数据后，选择一个节点查看字段和证据。'));
      container.append(placeholder);
      return;
    }
    const { kind, id } = selection;
    const map = { object: currentIndex.objects, feature: currentIndex.features, type: currentIndex.types, record: currentIndex.records, source: currentIndex.sources };
    const item = map[kind]?.get(id);
    if (!item) {
      const placeholder = make('div', 'detail-placeholder');
      placeholder.append(make('span', 'detail-kicker', '节点详情'), make('h3', '', nodeLabel(kind, id)), make('p', '', '该节点在当前数据中没有可显示的详细信息。'));
      container.append(placeholder);
      return;
    }

    const titleRow = make('div', 'detail-title-row');
    const titleBlock = make('div');
    titleBlock.append(make('span', 'detail-kicker', mode === 'framework' ? '框架条目' : '节点详情'), make('h3', '', nodeLabel(kind, id)));
    titleRow.append(titleBlock, make('span', 'kind-chip', nodeKindNames[kind] || kind));
    container.append(titleRow);

    if (kind === 'record') appendRecordDetail(container, item);
    else if (kind === 'feature') appendFeatureDetail(container, item);
    else if (kind === 'type') appendTypeDetail(container, item);
    else if (kind === 'source') appendSourceDetail(container, item);
    else appendObjectDetail(container, item);
  }

  function renderFrameworkSelection() {
    const selected = frameworkSelection;
    if (selected.kind === 'class') {
      const info = classInfo.get(selected.id);
      const container = byId('framework-detail');
      clear(container);
      const header = make('div', 'detail-title-row');
      const title = make('div');
      title.append(make('span', 'detail-kicker', '核心信息类别'), make('h3', '', info?.label || classNames[selected.id] || selected.id));
      header.append(title, make('span', 'kind-chip', '候选框架'));
      container.append(header, make('p', 'detail-description', info?.description || '尚未填写说明。'));

      if (selected.id === 'object') {
        appendDefinitionList(container, [
          ['包含', '位置背景、建筑及有编号的构件'],
          ['建筑字段', '编号、名称、位置关联、对象标识状态、备注'],
          ['构件字段', '编号、所属建筑、构件类别、部位、对象标识状态、备注']
        ]);
      } else if (selected.id === 'feature_definition') {
        const section = addDetailSection(container, '当前字段定义');
        appendSelectableItems(section, currentData.feature_definitions, 'feature');
      } else if (selected.id === 'record') {
        const contract = staticSchema.record_contract || {};
        appendDefinitionList(container, [
          ['必需内容', Array.isArray(contract.required) ? contract.required.map((key) => recordFieldNames[key] || key).join('、') : '按记录模板填写'],
          ['取值规则', '分类引用类型编号；数值保留单位；文本保留描述；未知留空，缺失不可填 0。'],
          ['证据规则', contract.evidence_rule || '来源与定位随记录保存。'],
          ['时间规则', '观察或调查日期与资料所指的历史时期分别记录，不能互相替代。']
        ]);
        const states = addDetailSection(container, '状态含义');
        appendDefinitionList(states, [['观察状态', '已观察、确认不存在、未观察、无法判断'], ['复核状态', '待复核、已复核、有分歧']]);
      } else if (selected.id === 'type_definition') {
        const section = addDetailSection(container, '当前候选类型规则');
        appendSelectableItems(section, currentData.type_definitions, 'type');
        const note = addDetailSection(container, '尺度边界');
        note.append(make('p', 'detail-description', '类型规则对应特定尺度。窗型只描述窗构件，不能替代建筑整体类型。'));
      } else if (selected.id === 'source') {
        appendDefinitionList(container, [['来源字段', '编号、名称、来源类别、文件地址、版本、记录时间、备注'], ['当前状态', currentData.sources.length ? '按导入数据逐条关联' : '尚无来源记录']]);
        const note = addDetailSection(container, '证据边界');
        note.append(make('p', 'detail-description', '照片、三维模型、点云、量测、调查记录和文献应区分来源类别，并为每条记录保留具体定位。演示占位不是实测证据。'));
      } else if (selected.id === 'analysis') {
        appendDefinitionList(container, [['结果字段', '分析范围、方法、对象编号、记录编号'], ['当前状态', currentData.analyses.length ? '已有分析记录；仍需按范围与依据复核' : '当前没有分析结果']]);
        const note = addDetailSection(container, '分析边界');
        note.append(make('p', 'detail-description', '分析结果应保留对象范围、有效记录、缺失和反例；本页不自动生成频次或统计结论。'));
        if (currentData.analyses.length) {
          const analysesSection = addDetailSection(container, '导入的分析结果');
          appendAnalysisEntries(analysesSection, currentData.analyses);
        }
      }
      return;
    }

    if (selected.kind === 'relation') {
      const relation = (staticSchema.relations || []).find((item) => item.id === selected.id);
      const container = byId('framework-detail');
      clear(container);
      const title = make('div', 'detail-title-row');
      const titleBlock = make('div');
      titleBlock.append(make('span', 'detail-kicker', '带方向的关系'), make('h3', '', relation?.label || selected.id));
      title.append(titleBlock, make('span', 'kind-chip', '关系定义'));
      container.append(title, make('p', 'detail-description', relation?.definition || '尚未填写关系定义。'));
      appendDefinitionList(container, [['关系编号', relation?.id || selected.id], ['起点', endpointLabel(relation?.from)], ['终点', endpointLabel(relation?.to)]]);
      return;
    }
    renderEntityDetail(byId('framework-detail'), selected, 'framework');
  }

  function appendSelectableItems(parent, items, kind) {
    if (!items.length) {
      parent.append(make('p', 'detail-description', '当前没有此类定义。'));
      return;
    }
    const list = make('ul', 'linked-list');
    for (const item of items) {
      const listItem = make('li');
      const extra = kind === 'feature' ? `${featureKindNames[item.value_kind] || item.value_kind} · ${item.unit || '无单位'} · ${statusName(item.status)}` : `${scopeLabel(item.scope)} · ${statusName(item.status)}`;
      listItem.append(makeNodeButton(kind, item.id, `${item.label} · ${extra}`));
      list.append(listItem);
    }
    parent.append(list);
  }

  function appendAnalysisEntries(parent, analyses) {
    for (const analysis of analyses) {
      const disclosure = make('details', 'record-disclosure');
      const summary = make('summary', '', analysis.label || analysis.id || '未命名分析');
      disclosure.append(summary);
      const body = make('div', 'record-disclosure-body');
      appendDefinitionList(body, [
        ['分析编号', analysis.id],
        ['范围', displayValue(analysis.scope)],
        ['方法', displayValue(analysis.method)]
      ]);

      const objectsSection = addDetailSection(body, '关联对象');
      if (Array.isArray(analysis.object_ids) && analysis.object_ids.length) {
        const objects = make('ul', 'linked-list');
        for (const id of analysis.object_ids) {
          const item = make('li');
          item.append(makeNodeButton('object', id, nodeLabel('object', id)));
          objects.append(item);
        }
        objectsSection.append(objects);
      } else objectsSection.append(make('p', 'detail-description', '未关联对象。'));

      const recordsSection = addDetailSection(body, '依据记录');
      if (Array.isArray(analysis.record_ids) && analysis.record_ids.length) {
        const records = make('ul', 'linked-list');
        for (const id of analysis.record_ids) {
          const item = make('li');
          const record = currentIndex.records.get(id);
          item.append(makeNodeButton('record', id, record ? `${nodeLabel('record', id)} · ${core.formatRecord(record, currentIndex)}` : id));
          records.append(item);
        }
        recordsSection.append(records);
      } else recordsSection.append(make('p', 'detail-description', '未关联记录。'));
      disclosure.append(body);
      parent.append(disclosure);
    }
  }

  function renderOverview() {
    const grid = byId('class-grid');
    clear(grid);
    for (const info of staticSchema.core_classes || []) {
      const button = make('button', `class-card${frameworkSelection.kind === 'class' && frameworkSelection.id === info.id ? ' is-selected' : ''}`);
      button.type = 'button';
      button.dataset.classId = info.id;
      button.append(make('strong', '', info.label), make('span', '', info.description));
      if (info.includes?.length) button.append(make('span', 'class-includes', `包含：${info.includes.map(endpointLabel).join('、')}`));
      grid.append(button);
    }

    const relationList = byId('relation-list');
    clear(relationList);
    for (const relation of staticSchema.relations || []) {
      const button = make('button', `relation-card${frameworkSelection.kind === 'relation' && frameworkSelection.id === relation.id ? ' is-selected' : ''}`);
      button.type = 'button';
      button.dataset.relationId = relation.id;
      button.append(make('span', 'relation-label', relation.label));
      const path = make('span', 'relation-path');
      path.append(make('span', '', endpointLabel(relation.from)), make('span', 'arrow-label', `${relation.label} →`), make('span', '', endpointLabel(relation.to)));
      button.append(path);
      relationList.append(button);
    }
    renderFrameworkSelection();
  }

  function buildRelationEdges() {
    currentEdges = core.buildEdges(currentData);
    const byRecord = new Map();
    for (const edge of currentEdges) {
      if (!edge.record_id || !currentIndex.records.has(edge.record_id)) continue;
      if (!byRecord.has(edge.record_id)) byRecord.set(edge.record_id, []);
      byRecord.get(edge.record_id).push(edge);
    }
    return byRecord;
  }

  function renderBuildingOptions() {
    const select = byId('building-select');
    clear(select);
    if (!currentData.buildings.length) {
      const option = make('option', '', '尚未录入建筑');
      option.value = '';
      select.append(option);
      select.disabled = true;
      return;
    }
    select.disabled = false;
    for (const building of currentData.buildings) {
      const option = make('option', '', building.label || building.id);
      option.value = building.id;
      select.append(option);
    }
    if (!currentData.buildings.some((building) => building.id === selectedBuildingId)) selectedBuildingId = currentData.buildings[0].id;
    select.value = selectedBuildingId;
  }

  function renderInstance() {
    const noBuildings = byId('no-buildings');
    const layout = byId('instance-layout');
    if (!currentData.buildings.length) {
      noBuildings.hidden = false;
      layout.hidden = true;
      return;
    }
    noBuildings.hidden = true;
    layout.hidden = false;
    renderBuildingOptions();
    const building = currentData.buildings.find((item) => item.id === selectedBuildingId) || currentData.buildings[0];
    selectedBuildingId = building.id;
    const place = currentIndex.objects.get(building.place_id);
    const path = byId('building-path');
    clear(path);
    const buildingNode = make('div', 'path-node');
    buildingNode.append(makeNodeButton('object', building.id, building.label, selectedSubjectId === building.id ? 'is-selected' : ''));
    path.append(buildingNode);
    if (place) {
      const relation = make('span', 'path-arrow', '位于 →');
      const placeNode = make('div', 'path-node');
      placeNode.append(relation, makeNodeButton('object', place.id, place.label));
      path.append(placeNode);
    }

    const components = currentData.components.filter((item) => item.building_id === building.id);
    const componentList = byId('component-list');
    clear(componentList);
    if (selectedSubjectId !== building.id && !components.some((item) => item.id === selectedSubjectId)) selectedSubjectId = defaultSubjectForBuilding(building.id);
    selectedComponentId = components.some((item) => item.id === selectedSubjectId) ? selectedSubjectId : null;
    if (!components.length) {
      componentList.append(make('p', 'detail-description', '该建筑尚未录入构件。'));
    } else {
      for (const component of components) {
        const item = make('div', 'component-item');
        item.append(make('span', 'path-arrow', '包含 →'));
        const button = make('button', `component-choice${component.id === selectedSubjectId ? ' is-selected' : ''}`);
        button.type = 'button';
        button.dataset.nodeKind = 'object';
        button.dataset.nodeId = component.id;
        button.append(make('span', '', component.label || component.id), make('span', 'component-kind', componentKindNames[component.kind] || component.kind));
        item.append(button);
        componentList.append(item);
      }
    }

    const selectedSubject = currentIndex.objects.get(selectedSubjectId) || null;
    byId('record-graph-title').textContent = selectedSubject?.node_kind === 'component' ? `${selectedSubject.label}的记录关系` : `${building.label}本身的记录`;
    renderRecordGraph(selectedSubject);
    renderSpatialRelations(building, components);
    renderEntityDetail(byId('instance-detail'), detailSelection || (selectedSubject ? { kind: 'object', id: selectedSubject.id } : { kind: 'object', id: building.id }));
  }

  function renderRecordGraph(subject) {
    const graph = byId('record-graph');
    clear(graph);
    if (!subject) {
      graph.append(make('p', 'detail-description', '选择一个建筑或构件后，这里会显示以该对象为主体的记录。'));
      return;
    }
    const records = currentData.records.filter((record) => record.subject_id === subject.id);
    if (!records.length) {
      graph.append(make('p', 'detail-description', subject.node_kind === 'building' ? '该建筑本身尚未录入特征或分类记录。点击下方构件可查看构件记录。' : '该构件尚未录入特征或分类记录。未知值会保留为空，不会显示为 0。'));
      return;
    }
    const edgesByRecord = buildRelationEdges();
    for (const record of records) {
      const card = make('article', 'record-relationship');
      const heading = make('div', 'record-node-heading');
      heading.append(makeNodeButton('record', record.id, nodeLabel('record', record.id)));
      heading.append(make('span', `status-chip${record.review_status === 'disputed' ? ' is-disputed' : record.review_status === 'checked' ? ' is-checked' : ''}`, `${statusLabel(record.observation_status)} · ${reviewLabel(record.review_status)}`));
      card.append(heading);
      const edgeList = make('div', 'edge-list');
      const recordEdges = edgesByRecord.get(record.id) || [];
      for (const edge of recordEdges) {
        if (edge.source !== record.id) continue;
        let targetKind = null;
        if (currentIndex.objects.has(edge.target)) targetKind = 'object';
        else if (currentIndex.features.has(edge.target)) targetKind = 'feature';
        else if (currentIndex.types.has(edge.target)) targetKind = 'type';
        else if (currentIndex.sources.has(edge.target)) targetKind = 'source';
        if (!targetKind) continue;
        const line = make('div', 'connection-line');
        line.append(makeNodeButton('record', record.id, nodeLabel('record', record.id)));
        line.append(make('span', 'edge-label', `${edge.label} →`));
        line.append(makeNodeButton(targetKind, edge.target, nodeLabel(targetKind, edge.target)));
        edgeList.append(line);
      }
      card.append(edgeList);
      graph.append(card);
    }
  }

  function renderSpatialRelations(building, components) {
    const section = byId('spatial-relation-section');
    const container = byId('spatial-relations');
    clear(container);
    const localIds = new Set([building.id, ...components.map((component) => component.id)]);
    const relations = currentData.relations.filter((relation) => localIds.has(relation.source_id) && localIds.has(relation.target_id));
    section.hidden = relations.length === 0;
    for (const relation of relations) {
      const row = make('div', 'spatial-relation-row');
      row.append(makeNodeButton('object', relation.source_id, nodeLabel('object', relation.source_id)));
      row.append(make('span', 'edge-label', `${relation.label} →`));
      row.append(makeNodeButton('object', relation.target_id, nodeLabel('object', relation.target_id)));
      if (Array.isArray(relation.evidence_record_ids) && relation.evidence_record_ids.length) {
        const evidence = make('div', 'spatial-relation-evidence');
        evidence.append(make('span', 'spatial-relation-evidence-label', '依据记录'));
        for (const id of relation.evidence_record_ids) {
          const record = currentIndex.records.get(id);
          evidence.append(makeNodeButton('record', id, record ? `${nodeLabel('record', id)} · ${core.formatRecord(record, currentIndex)}` : id));
        }
        row.append(evidence);
      }
      container.append(row);
    }
  }

  function renderComparison() {
    const empty = byId('compare-empty');
    const table = byId('comparison-table');
    const head = $('thead', table);
    const body = $('tbody', table);
    clear(head);
    clear(body);
    empty.hidden = currentData.buildings.length > 0;

    const headerRow = make('tr');
    headerRow.append(make('th', '', '特征字段'));
    for (const building of currentData.buildings) headerRow.append(make('th', '', building.label || building.id));
    head.append(headerRow);

    const index = currentIndex;
    const featureIds = getComparisonFeatureIds();
    for (const featureId of featureIds) {
      const feature = index.features.get(featureId);
      const row = make('tr');
      row.append(make('th', '', feature?.label || featureId));
      for (const building of currentData.buildings) {
        const cell = core.comparisonCell(currentData, building.id, featureId, index);
        const td = make('td');
        const button = make('button', 'cell-button', cell.text);
        button.type = 'button';
        button.dataset.cellBuilding = building.id;
        button.dataset.cellFeature = featureId;
        button.dataset.status = cell.status;
        button.setAttribute('aria-label', `${building.label || building.id}，${feature?.label || featureId}：${cell.text}。点击查看相关记录`);
        td.append(button);
        row.append(td);
      }
      body.append(row);
    }
  }

  function getComparisonFeatureIds() {
    const defined = new Set(currentData.feature_definitions.map((feature) => feature.id));
    const recorded = new Set(currentData.records.map((record) => record.feature_id));
    const preferred = preferredCompareFeatureIds.filter((id) => defined.has(id));
    const additional = currentData.feature_definitions
      .filter((feature) => !preferred.includes(feature.id) && recorded.has(feature.id))
      .map((feature) => feature.id);
    return [...preferred, ...additional];
  }

  function resetComparisonDetails() {
    const panel = byId('comparison-details');
    clear(panel);
    const placeholder = make('div', 'detail-placeholder');
    placeholder.append(make('span', 'detail-kicker', '记录详情'), make('h3', '', '选择一个单元格'), make('p', '', '相关记录会在这里逐条列出，分歧不会自动合并。'));
    panel.append(placeholder);
  }

  function showComparisonCell(buildingId, featureId) {
    const building = currentIndex.objects.get(buildingId);
    const feature = currentIndex.features.get(featureId);
    const result = core.comparisonCell(currentData, buildingId, featureId, currentIndex);
    const panel = byId('comparison-details');
    clear(panel);
    const title = make('div', 'detail-title-row');
    const titleBlock = make('div');
    titleBlock.append(make('span', 'detail-kicker', '该单元格的全部相关记录'), make('h3', '', `${building?.label || buildingId} · ${feature?.label || featureId}`));
    title.append(titleBlock, make('span', `status-chip${result.status === 'disputed' ? ' is-disputed' : ''}`, result.status === 'empty' ? '未录入' : result.status === 'disputed' ? '有分歧' : result.status === 'multiple' ? '多条记录' : '记录'));
    panel.append(title);
    if (!result.records.length) {
      panel.append(make('p', 'detail-description', '当前建筑尚未录入此字段的记录。'));
      return;
    }
    panel.append(make('p', 'detail-description', '以下记录均保留在当前数据中。若结果有分歧，请逐条查看来源和复核状态。'));
    for (const record of result.records) {
      const disclosure = make('details', 'record-disclosure');
      disclosure.open = result.records.length === 1 || record.review_status === 'disputed';
      const summary = make('summary', '', `${core.formatRecord(record, currentIndex)} · ${record.id}`);
      disclosure.append(summary);
      const body = make('div', 'record-disclosure-body');
      appendRecordDetail(body, record);
      disclosure.append(body);
      panel.append(disclosure);
    }
  }

  function renderDatasetNotice() {
    const notice = byId('dataset-notice');
    clear(notice);
    const isDemo = currentData.meta.mode === 'demo';
    notice.className = `dataset-notice${isDemo ? '' : ' is-research'}`;
    notice.append(make('span', 'notice-label', isDemo ? '演示数据' : '研究数据'));
    const copy = make('span', 'notice-copy');
    if (isDemo) {
      copy.textContent = `当前包含 ${currentData.buildings.length} 个虚构建筑；所有数值和分类仅供演示，不是研究发现。真实照片与三维模型尚未提供，证据来源均为占位。`;
    } else {
      copy.textContent = '当前显示导入的研究数据。未录入建筑会保持空白，不会自动补入演示对象；记录仍需依据原始来源核对。';
    }
    notice.append(copy);
  }

  function renderImportMessage(title, messages, state) {
    const box = byId('import-message');
    clear(box);
    if (!title) {
      box.hidden = true;
      box.className = 'import-message';
      return;
    }
    box.hidden = false;
    box.className = `import-message${state === 'error' ? ' is-error' : state === 'warning' ? ' is-warning' : ''}`;
    box.append(make('div', 'message-title', title));
    if (messages?.length) {
      const list = make('ul', 'message-list');
      for (const message of messages) list.append(make('li', '', message));
      box.append(list);
    }
  }

  function renderAll() {
    renderDatasetNotice();
    renderOverview();
    renderBuildingOptions();
    renderInstance();
    renderComparison();
  }

  function switchView(view) {
    for (const button of document.querySelectorAll('[data-view]')) {
      const active = button.dataset.view === view;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
      button.tabIndex = active ? 0 : -1;
    }
    for (const panel of document.querySelectorAll('.view-panel')) {
      panel.hidden = panel.id !== `panel-${view}`;
    }
  }

  function handleNodeSelection(kind, id) {
    if (kind === 'object') {
      const nodeType = objectNodeKind(id);
      if (nodeType === 'building') {
        selectedBuildingId = id;
        selectedComponentId = null;
        selectedSubjectId = id;
      } else if (nodeType === 'component') {
        selectedComponentId = id;
        selectedSubjectId = id;
        const component = currentIndex.objects.get(id);
        if (component) selectedBuildingId = component.building_id;
      }
    }
    detailSelection = { kind, id };
    renderInstance();
  }

  function handleImport(file) {
    if (!file) return;
    file.text().then((text) => {
      let imported;
      try {
        imported = JSON.parse(text);
      } catch (_error) {
        renderImportMessage('未导入：文件不是有效 JSON', ['请检查文件内容后再试。'], 'error');
        return;
      }
      const validation = core.validateDataset(imported);
      if (validation.errors.length) {
        renderImportMessage('未导入：数据结构存在错误，当前数据已保留', validation.errors, 'error');
        return;
      }
      currentData = imported;
      currentIndex = core.buildIndex(currentData);
      currentEdges = core.buildEdges(currentData);
      currentValidation = validation;
      selectedBuildingId = currentData.buildings[0]?.id || null;
      selectedSubjectId = defaultSubjectForBuilding(selectedBuildingId);
      selectedComponentId = currentData.components.some((item) => item.id === selectedSubjectId) ? selectedSubjectId : null;
      detailSelection = selectedSubjectId ? { kind: 'object', id: selectedSubjectId } : initialDetailSelection();
      frameworkSelection = { kind: 'class', id: 'object' };
      resetComparisonDetails();
      if (validation.warnings.length) {
        renderImportMessage('文件已载入，以下内容仍待补', validation.warnings, 'warning');
      } else {
        renderImportMessage('文件已载入；请按原始来源逐条核对记录。', [], '');
      }
      renderAll();
    }).catch(() => {
      renderImportMessage('未导入：无法读取此文件', ['当前数据已保留。请确认所选文件可读取。'], 'error');
    });
  }

  function exportCurrentData() {
    const blob = new Blob([JSON.stringify(currentData, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = make('a');
    anchor.href = url;
    anchor.download = `建筑风貌知识图谱-${currentData.meta.mode}.json`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  document.addEventListener('click', (event) => {
    const viewButton = event.target.closest('[data-view]');
    if (viewButton) {
      switchView(viewButton.dataset.view);
      return;
    }

    const classButton = event.target.closest('[data-class-id]');
    if (classButton) {
      frameworkSelection = { kind: 'class', id: classButton.dataset.classId };
      renderOverview();
      return;
    }
    const relationButton = event.target.closest('[data-relation-id]');
    if (relationButton) {
      frameworkSelection = { kind: 'relation', id: relationButton.dataset.relationId };
      renderOverview();
      return;
    }
    const nodeButton = event.target.closest('[data-node-kind][data-node-id]');
    if (nodeButton) {
      const { nodeKind, nodeId } = nodeButton.dataset;
      if (nodeButton.closest('#framework-detail')) {
        frameworkSelection = { kind: nodeKind, id: nodeId };
        renderOverview();
        return;
      }
      if (nodeKind === 'record' || nodeKind === 'feature' || nodeKind === 'type' || nodeKind === 'source' || nodeKind === 'object') {
        handleNodeSelection(nodeKind, nodeId);
      }
      return;
    }
    const cellButton = event.target.closest('[data-cell-building][data-cell-feature]');
    if (cellButton) {
      showComparisonCell(cellButton.dataset.cellBuilding, cellButton.dataset.cellFeature);
    }
  });

  byId('building-select').addEventListener('change', (event) => {
    selectedBuildingId = event.target.value || null;
    selectedSubjectId = defaultSubjectForBuilding(selectedBuildingId);
    selectedComponentId = currentData.components.some((item) => item.id === selectedSubjectId) ? selectedSubjectId : null;
    const building = currentData.buildings.find((item) => item.id === selectedBuildingId);
    detailSelection = selectedSubjectId ? { kind: 'object', id: selectedSubjectId } : (building ? { kind: 'object', id: building.id } : null);
    renderInstance();
  });

  document.addEventListener('keydown', (event) => {
    const currentTab = event.target.closest?.('[role="tab"][data-view]');
    if (!currentTab) return;
    const tabs = [...document.querySelectorAll('[role="tab"][data-view]')];
    const currentIndexInTabs = tabs.indexOf(currentTab);
    let nextIndex = currentIndexInTabs;
    if (event.key === 'ArrowRight') nextIndex = (currentIndexInTabs + 1) % tabs.length;
    else if (event.key === 'ArrowLeft') nextIndex = (currentIndexInTabs - 1 + tabs.length) % tabs.length;
    else if (event.key === 'Home') nextIndex = 0;
    else if (event.key === 'End') nextIndex = tabs.length - 1;
    else return;
    event.preventDefault();
    const nextTab = tabs[nextIndex];
    switchView(nextTab.dataset.view);
    nextTab.focus();
  });

  byId('import-trigger').addEventListener('click', () => byId('data-file').click());
  byId('data-file').addEventListener('change', (event) => {
    handleImport(event.target.files?.[0]);
    event.target.value = '';
  });
  byId('export-data').addEventListener('click', exportCurrentData);

  for (const button of document.querySelectorAll('[role="tab"][data-view]')) {
    button.tabIndex = button.dataset.view === 'overview' ? 0 : -1;
  }

  if (currentValidation.errors.length) {
    renderImportMessage('当前预置数据存在结构问题', currentValidation.errors, 'error');
  } else if (currentValidation.warnings.length) {
    renderImportMessage('当前数据仍有待补信息', currentValidation.warnings, 'warning');
  }
  renderAll();
})();
