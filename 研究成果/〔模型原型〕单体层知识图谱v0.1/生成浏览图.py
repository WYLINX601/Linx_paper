#!/usr/bin/env python3
"""Build a self-contained offline SVG viewer from model and case JSON files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_DIR = Path(__file__).resolve().parent

HTML = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>单体层知识图谱 v0.1 · 讨论稿</title>
<style>
:root {
  --ink:#202b36; --muted:#607080; --line:#d7e0e7; --paper:#fff;
  --wash:#f4f7f9; --blue:#256a9b; --teal:#267a72; --orange:#b65b20;
  --purple:#7854a0; --red:#a24545; --gold:#9b741a;
}
* { box-sizing:border-box; }
body { margin:0; color:var(--ink); background:var(--wash); font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
header { padding:16px clamp(14px,3vw,32px) 12px; background:var(--paper); border-bottom:1px solid var(--line); }
h1 { margin:0; font-size:clamp(20px,3vw,27px); font-weight:700; letter-spacing:.01em; }
.subhead { margin:5px 0 0; color:var(--muted); font-size:13px; }
main { max-width:1500px; margin:0 auto; padding:14px clamp(10px,2vw,24px) 28px; }
.toolbar { display:flex; gap:9px; align-items:center; flex-wrap:wrap; padding:10px; background:var(--paper); border:1px solid var(--line); border-radius:9px; }
button, select { min-height:38px; padding:7px 11px; border:1px solid #b9c8d3; border-radius:6px; background:#fff; color:var(--ink); font:inherit; }
button { cursor:pointer; }
button[aria-pressed="true"] { color:white; background:#295b7b; border-color:#295b7b; }
button:focus-visible, select:focus-visible, summary:focus-visible { outline:3px solid #82bce0; outline-offset:2px; }
.control-label { color:var(--muted); font-size:13px; }
.spacer { flex:1; }
.statusline { margin:10px 0; padding:9px 12px; background:#eef5f8; border-left:4px solid var(--blue); border-radius:4px; color:#314c5e; }
.statusline.empty { background:#fff8e9; border-left-color:var(--gold); color:#69521b; }
.stats { display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }
.stat { padding:5px 10px; border:1px solid var(--line); border-radius:999px; background:#fff; color:#425363; font-size:13px; }
.legend { display:flex; align-items:center; flex-wrap:wrap; gap:7px 14px; padding:8px 2px 11px; color:#465767; font-size:12px; }
.legend-item { display:inline-flex; align-items:center; gap:6px; }
.swatch { width:12px; height:12px; border-radius:50%; display:inline-block; border:1px solid #8093a2; }
.line-swatch { width:23px; border-top:3px solid var(--blue); display:inline-block; }
.line-swatch.reader { border-top-color:var(--orange); border-top-style:dashed; }
.workspace { display:grid; grid-template-columns:minmax(0,1fr) minmax(285px,370px); gap:12px; align-items:stretch; }
.panel { min-width:0; background:var(--paper); border:1px solid var(--line); border-radius:9px; }
.graph-panel { overflow:hidden; }
.panel-head { padding:10px 13px; border-bottom:1px solid var(--line); font-weight:650; }
.panel-head small { color:var(--muted); font-weight:400; }
.graph-scroll { overflow:auto; }
svg#graph { width:100%; min-width:960px; height:650px; min-height:650px; display:block; background:linear-gradient(#fff,#fbfdfe); }
.detail-panel { max-height: min(68vh,700px); overflow:auto; }
#detail { padding:12px; }
#detail h2 { font-size:18px; margin:0 0 5px; line-height:1.35; overflow-wrap:anywhere; }
#detail h3 { font-size:14px; margin:16px 0 6px; }
#detail p { margin:5px 0; }
.muted { color:var(--muted); }
.kv { display:grid; grid-template-columns:100px minmax(0,1fr); gap:4px 8px; margin:8px 0; }
.kv dt { color:var(--muted); }
.kv dd { margin:0; overflow-wrap:anywhere; }
.card { margin:8px 0; padding:9px 10px; border:1px solid var(--line); border-radius:7px; background:#fcfdfe; overflow-wrap:anywhere; }
.card p { margin:4px 0; }
.badge { display:inline-block; margin:2px 4px 2px 0; padding:2px 7px; border-radius:999px; background:#edf2f5; color:#344b5d; font-size:12px; }
.badge.fact { background:#e6f1f8; color:#205f89; }
.badge.interpretation { background:#e5f3ef; color:#206c62; }
.badge.reader { background:#fff0df; color:#995019; }
.badge.status-disputed { background:#fae8e8; color:#963f3f; }
.badge.status-tentative { background:#fff4dc; color:#86630e; }
.empty-note { padding:22px 14px; text-align:center; color:var(--muted); }
.table-panel { margin-top:12px; overflow:hidden; }
.table-scroll { max-height:68vh; overflow:auto; }
table { width:100%; border-collapse:collapse; font-size:14px; }
th, td { padding:8px 9px; border-bottom:1px solid #e5ebef; text-align:left; vertical-align:top; overflow-wrap:anywhere; }
th { position:sticky; top:0; z-index:1; background:#f2f6f8; font-weight:650; }
td small { color:var(--muted); }
details { margin:12px 0; padding:0 12px; background:#fff; border:1px solid var(--line); border-radius:8px; }
summary { cursor:pointer; padding:11px 0; font-weight:650; }
details .inside { padding:0 0 12px; }
.subsection { margin:12px 0 0; }
.subsection h2 { font-size:16px; margin:0 0 7px; }
.node { cursor:pointer; }
.node circle { stroke:#3e5669; stroke-width:1.6; fill:#e7f0f5; }
.node text { pointer-events:none; font-size:13px; fill:#1e2a33; }
.node .node-label-bg { fill:#fff; opacity:.88; }
.node.selected circle { stroke:#102f47; stroke-width:3.5; filter:drop-shadow(0 2px 3px #8aa0af); }
.node.value circle { fill:#fff7dc; stroke:#9b741a; }
.node.disputed circle { fill:#fff1f1; stroke:#a24545; stroke-dasharray:4 3; stroke-width:2.4; }
.node.missing circle { fill:#fff1f1; stroke:#a24545; stroke-dasharray:4 3; }
.node.record circle { fill:#f1ecf8; stroke:#7854a0; }
.node.class-Dwelling circle { fill:#dcecf5; }
.node.class-Space circle { fill:#dff0ed; }
.node.class-Element circle { fill:#f4ead9; }
.node.class-Representation circle { fill:#e7f3e2; }
.node.class-TypeConcept circle,.node.class-TypeScheme circle { fill:#ede5f7; }
.edge path { fill:none; stroke:#66869a; stroke-width:1.7; marker-end:url(#arrow); }
.edge.reader path { stroke:var(--orange); stroke-dasharray:6 4; }
.edge.interpretation path { stroke:var(--teal); }
.edge.classification:not(.reader):not(.interpretation) path { stroke:var(--purple); }
.edge.nonaffirmative path { stroke:#9d6e50; stroke-dasharray:4 4; }
.edge-label { font-size:13px; fill:#233744; text-anchor:middle; dominant-baseline:middle; }
.edge-label-bg { fill:#fff; stroke:#e2e8ec; opacity:.94; }
.edge.reader .edge-label-bg { stroke:#edc7a7; }
.edge.interpretation .edge-label-bg { stroke:#b9ded6; }
.edge.classification .edge-label-bg { stroke:#d2c4e4; }
.edge:focus path { stroke-width:3.3; }
#tablePanel[hidden], #graphWorkspace[hidden] { display:none; }
@media (max-width:1200px) {
  .workspace { grid-template-columns:1fr; }
  .detail-panel { max-height:none; }
}
@media (max-width:850px) {
  .workspace { grid-template-columns:1fr; }
  .detail-panel { max-height:none; }
  svg#graph { height:650px; min-height:650px; }
}
@media (max-width:520px) {
  body { font-size:14px; }
  main { padding-left:8px; padding-right:8px; }
  .toolbar { gap:6px; }
  select { max-width:100%; }
  svg#graph { min-width:960px; height:650px; min-height:650px; }
  .kv { grid-template-columns:85px minmax(0,1fr); }
  th,td { padding:7px; }
}
</style>
</head>
<body>
<header>
  <h1>单体层知识图谱 v0.1 · 讨论稿</h1>
  <p class="subhead">按证据追溯对象、关系、属性与分类判断。文献记录、作者解释和读者判断分别标示；空缺按原记录展示。</p>
</header>
<main>
  <div class="toolbar" role="toolbar" aria-label="图谱浏览控件">
    <button id="conceptTab" type="button" aria-pressed="true">概念关系</button>
    <button id="caseTab" type="button" aria-pressed="false">文献案例</button>
    <span class="control-label">节点</span>
    <select id="nodeSelect" aria-label="选择节点"><option value="">全部节点</option></select>
    <button id="focusButton" type="button" aria-pressed="false">聚焦一跳</button>
    <span class="spacer"></span>
    <button id="graphButton" type="button" aria-pressed="true">图谱</button>
    <button id="tableButton" type="button" aria-pressed="false">关系表</button>
  </div>
  <div id="statusline" class="statusline"></div>
  <div id="stats" class="stats" aria-label="数据统计"></div>
  <div class="legend" id="legend"></div>
  <div id="graphWorkspace" class="workspace">
    <section class="panel graph-panel" aria-label="有向网络图">
      <div class="panel-head">节点与有向关系 <small id="graphHint">点击节点查看证据和属性</small></div>
      <div class="graph-scroll"><svg id="graph" viewBox="0 0 1000 650" role="img" aria-label="可交互有向知识图谱"></svg></div>
    </section>
    <aside class="panel detail-panel" aria-label="选中节点详情">
      <div class="panel-head">节点详情</div>
      <div id="detail"></div>
    </aside>
  </div>
  <section id="tablePanel" class="panel table-panel" hidden>
    <div class="panel-head">关系与判据文字表 <small>与网络图表达相同的有向关系</small></div>
    <div class="table-scroll" id="tableContent"></div>
  </section>
  <div id="caseSupplements"></div>
</main>
<script>
"use strict";
const DATA = __DATA__;
const $ = (id) => document.getElementById(id);
const CLASS_LABELS = Object.fromEntries((DATA.model.classes || []).map(x => [x.id, x.label || x.id]));
const RELATIONS = Object.fromEntries((DATA.model.relations || []).map(x => [x.id, x]));
const FEATURES = Object.fromEntries((DATA.model.features || []).map(x => [x.id, x]));
const ATTR = {
  author_report: {label:"文献记载", cls:"fact"},
  author_interpretation: {label:"作者解释", cls:"interpretation"},
  reader_diagram_observation: {label:"读者读图观察", cls:"reader"},
  reader_modeling_inference: {label:"读者建模推断", cls:"reader"}
};
const STATUS = {documented:"有记录", tentative:"暂定", disputed:"有争议"};
const DECISION = {
  author_assigned:"作者归类", criteria_match:"读者判据匹配",
  criteria_not_match:"读者判据未匹配（判断）", insufficient_evidence:"证据不足（判断）"
};
const RESULT = {satisfied:"满足", not_satisfied:"不满足", unknown:"未知"};
const CASE = DATA.case || {};
let activeTab = "concept";
let activeView = "graph";
let selectedId = "Dwelling";
let focusOneHop = true;
let currentNodes = [];
let currentEdges = [];
let caseMaps = null;

function textValue(value) {
  if (value === null || value === undefined || value === "") return "未记录";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (Array.isArray(value)) return value.length ? value.map(textValue).join("、") : "未记录";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
function labelForClass(id) { return CLASS_LABELS[id] || id || "未注明类型"; }
function predicateLabel(id) {
  const item = RELATIONS[id] || FEATURES[id];
  return item ? item.label : (id || "未命名关系");
}
function attribution(value) { return ATTR[value] || {label: value || "归属未注明", cls:""}; }
function evidenceIds(value) { return Array.isArray(value) ? value : (value ? [value] : []); }
function add(parent, tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (className) node.className = className;
  parent.appendChild(node);
  return node;
}
function badge(parent, label, className) {
  return add(parent, "span", label, "badge" + (className ? " " + className : ""));
}
function makePill(parent, label, value) {
  const span = add(parent, "span", "", "stat");
  span.textContent = label + " " + value;
}
function buildConcept() {
  const nodes = (DATA.model.classes || []).map(c => ({
    id:c.id, label:c.label || c.id, class:c.id, note:c.definition || "",
    kind:"concept", tier:c.tier || "core", source:c
  }));
  const edges = [];
  for (const r of (DATA.model.relations || [])) {
    for (const source of (r.domain || [])) for (const target of (r.range || [])) {
      edges.push({
        id:"concept:" + r.id + ":" + source + ":" + target,
        source, target, predicate:r.id, label:r.label || r.id,
        definition:r.definition || "", attribution:"model_definition",
        kind:"concept", record:r
      });
    }
  }
  return {nodes, edges};
}
function buildCase() {
  const nodes = (CASE.nodes || []).map(n => ({...n, kind:"case", source:n}));
  const nodeIds = new Set(nodes.map(n => String(n.id)));
  const extra = new Map();
  const edges = [];
  const ensureTarget = (raw, assertionId, isValue, status) => {
    if (isValue) {
      const id = "@value:" + assertionId;
      const disputed = status === "disputed";
      const node = {id, label:textValue(raw) + (disputed ? " · 有争议" : ""), class:"Value", kind:"value", value:raw, status, note:disputed ? "原文值保留；存在冲突证据，未确认为定值。" : ""};
      extra.set(id, node); return id;
    }
    const id = String(raw);
    if (nodeIds.has(id)) return id;
    if (!extra.has(id)) extra.set(id, {
      id, label:"未建节点 · " + id, class:"Missing", kind:"missing",
      note:"该断言引用的目标节点未出现在 nodes 中。"
    });
    return id;
  };
  for (const a of (CASE.assertions || [])) {
    const hasObject = Object.prototype.hasOwnProperty.call(a, "object");
    const target = hasObject ? ensureTarget(a.object, a.id, false) : ensureTarget(a.value, a.id, true, a.status);
    const subject = nodeIds.has(String(a.subject)) ? String(a.subject) : ensureTarget(a.subject, a.id + ":subject", false);
    edges.push({
      id:"assertion:" + a.id, source:subject, target,
      predicate:a.predicate || "", label:predicateLabel(a.predicate),
      attribution:a.attribution, status:a.status, evidence:a.evidence || [],
      temporalScope:a.temporalScope, kind:"assertion", record:a,
      value:!hasObject ? a.value : undefined, conflictingEvidence:a.conflictingEvidence || []
    });
  }
  for (const c of (CASE.classifications || [])) {
    const decision = c.decision || "insufficient_evidence";
    const target = ensureTarget(c.type, c.id, false);
    const subject = nodeIds.has(String(c.subject)) ? String(c.subject) : ensureTarget(c.subject, c.id + ":subject", false);
    const label = DECISION[decision] || decision;
    edges.push({
      id:"classification:" + c.id, source:subject, target,
      predicate:(decision === "author_assigned" || decision === "criteria_match") ? "has_type" : "classification_result",
      label, attribution:c.attribution, status:c.status,
      evidence:c.evidence || [], temporalScope:c.temporalScope,
      kind:"classification", record:c, decision
    });
  }
  return {nodes:[...nodes, ...extra.values()], edges};
}
function visibleGraph() {
  if (activeTab === "concept") return buildConcept();
  return buildCase();
}
function nodeName(node) { return node ? (node.label || node.id) : "未建节点"; }
function nodeById(id) { return currentNodes.find(n => String(n.id) === String(id)); }
function relatedEdges(id) {
  return currentEdges.filter(e => String(e.source) === String(id) || String(e.target) === String(id));
}
function visibleSelection() {
  let nodes = currentNodes.slice();
  let edges = currentEdges.slice();
  if (selectedId && focusOneHop) {
    edges = edges.filter(e => String(e.source) === selectedId || String(e.target) === selectedId);
    const ids = new Set([selectedId]);
    edges.forEach(e => { ids.add(String(e.source)); ids.add(String(e.target)); });
    nodes = nodes.filter(n => ids.has(String(n.id)));
  }
  return {nodes, edges};
}
function refresh() {
  const graph = visibleGraph();
  currentNodes = graph.nodes;
  currentEdges = graph.edges;
  const exists = selectedId && currentNodes.some(n => String(n.id) === selectedId);
  if (selectedId && !exists) selectedId = "";
  fillNodeSelect();
  updateToolbar();
  renderStats();
  renderLegend();
  const subset = visibleSelection();
  if (activeView === "graph") {
    $("graphWorkspace").hidden = false;
    $("tablePanel").hidden = true;
    renderGraph(subset.nodes, subset.edges);
  } else {
    $("graphWorkspace").hidden = true;
    $("tablePanel").hidden = false;
    renderTable(subset.nodes, subset.edges);
  }
  renderDetail();
  renderSupplements();
  renderStatus();
}
function fillNodeSelect() {
  const select = $("nodeSelect");
  select.replaceChildren();
  select.add(new Option("全部节点", ""));
  const sorted = currentNodes.slice().sort((a,b) => nodeName(a).localeCompare(nodeName(b), "zh-CN"));
  for (const n of sorted) select.add(new Option(nodeName(n) + " · " + labelForClass(n.class), String(n.id)));
  select.value = selectedId;
}
function updateToolbar() {
  $("conceptTab").setAttribute("aria-pressed", String(activeTab === "concept"));
  $("caseTab").setAttribute("aria-pressed", String(activeTab === "case"));
  $("graphButton").setAttribute("aria-pressed", String(activeView === "graph"));
  $("tableButton").setAttribute("aria-pressed", String(activeView === "table"));
  $("focusButton").setAttribute("aria-pressed", String(focusOneHop));
  $("focusButton").textContent = focusOneHop ? "显示全部" : "聚焦一跳";
  $("graphHint").textContent = selectedId ? (focusOneHop ? "仅显示选中节点及一跳关系" : "点击节点查看证据和属性") : "点击节点查看证据和属性";
}
function renderStatus() {
  const el = $("statusline");
  if (activeTab === "concept") {
    el.className = "statusline";
    el.textContent = "概念关系来自模型定义；关系边的方向按 domain → range 展示。属性词条列在关系表中。";
    return;
  }
  const hasData = (CASE.nodes || []).length > 0 || (CASE.assertions || []).length > 0 || (CASE.classifications || []).length > 0;
  el.className = "statusline" + (hasData ? "" : " empty");
  el.textContent = hasData
    ? "案例内容按输入 JSON 展示。争议值与冲突证据并列保留，不作为确定结论；未匹配或证据不足只显示判断连线，不投影为 has_type。"
    : "案例图谱.json 当前为空或尚未提供；案例网络保持空白，未补造案例节点。";
}
function renderStats() {
  const el = $("stats"); el.replaceChildren();
  if (activeTab === "concept") {
    makePill(el, "概念", (DATA.model.classes || []).length);
    makePill(el, "关系定义", (DATA.model.relations || []).length);
    makePill(el, "特征定义", (DATA.model.features || []).length);
  } else {
    makePill(el, "案例节点", (CASE.nodes || []).length);
    makePill(el, "断言", (CASE.assertions || []).length);
    makePill(el, "分类判断", (CASE.classifications || []).length);
    makePill(el, "证据", (CASE.evidence || []).length);
    makePill(el, "明确空缺", (CASE.gaps || []).length);
  }
}
function renderLegend() {
  const el = $("legend"); el.replaceChildren();
  const addItem = (label, style, line=false) => {
    const item = add(el, "span", "", "legend-item");
    const sw = add(item, "span", "", line ? "line-swatch " + style : "swatch");
    if (!line) {
      const colors = {Dwelling:"#dcecf5",Space:"#dff0ed",Element:"#f4ead9",Representation:"#e7f3e2",TypeConcept:"#ede5f7",TypeScheme:"#ede5f7"};
      sw.style.background = colors[style] || "#e7f0f5";
    } else if (style === "reader") sw.classList.add("reader");
    add(item, "span", label);
  };
  if (activeTab === "concept") {
    for (const c of (DATA.model.classes || [])) addItem(c.label || c.id, c.id);
    addItem("类型定义之间的有向关系", "literature", true);
  } else {
    addItem("文献记载", "literature", true);
    addItem("作者解释", "interpretation", true);
    addItem("读者观察 / 推断", "reader", true);
    addItem("属性值", "Value");
    addItem("未建目标节点", "Missing");
  }
}
function svgEl(tag, attrs={}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k,v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  return el;
}
function nodeRadius(n) { return n.kind === "value" ? 23 : (n.kind === "record" ? 25 : 27); }
function layout(nodes, edges) {
  const W=1000, H=650, cx=W/2, cy=H/2;
  const n=nodes.length;
  const pos=new Map();
  if (!n) return pos;
  const angleStep=Math.PI*(3-Math.sqrt(5));
  const ring=Math.min(W,H)*0.36;
  nodes.forEach((node,i) => {
    const angle=i*angleStep;
    const radius=ring*Math.sqrt((i+1)/n);
    pos.set(String(node.id), {x:cx+Math.cos(angle)*radius, y:cy+Math.sin(angle)*radius});
  });
  if (n < 2) { const p=pos.get(String(nodes[0].id)); p.x=cx; p.y=cy; return pos; }
  const area=(W-100)*(H-100), k=Math.sqrt(area/n);
  let temp=52;
  for (let it=0; it<90; it++) {
    const disp=new Map(nodes.map(node => [String(node.id), {x:0,y:0}]));
    for (let i=0;i<n;i++) for(let j=i+1;j<n;j++) {
      const a=pos.get(String(nodes[i].id)), b=pos.get(String(nodes[j].id));
      let dx=a.x-b.x, dy=a.y-b.y, d=Math.hypot(dx,dy)||0.01;
      const f=(k*k)/d, fx=dx/d*f, fy=dy/d*f;
      disp.get(String(nodes[i].id)).x+=fx; disp.get(String(nodes[i].id)).y+=fy;
      disp.get(String(nodes[j].id)).x-=fx; disp.get(String(nodes[j].id)).y-=fy;
    }
    for (const e of edges) {
      const a=pos.get(String(e.source)), b=pos.get(String(e.target));
      if (!a || !b || a===b) continue;
      let dx=a.x-b.x, dy=a.y-b.y, d=Math.hypot(dx,dy)||0.01;
      const f=(d*d)/k, fx=dx/d*f, fy=dy/d*f;
      disp.get(String(e.source)).x-=fx; disp.get(String(e.source)).y-=fy;
      disp.get(String(e.target)).x+=fx; disp.get(String(e.target)).y+=fy;
    }
    for (const node of nodes) {
      const id=String(node.id), p=pos.get(id), d=disp.get(id);
      d.x+=(cx-p.x)*0.018; d.y+=(cy-p.y)*0.018;
      const mag=Math.hypot(d.x,d.y)||1;
      p.x=Math.max(88,Math.min(W-88,p.x+d.x/mag*Math.min(mag,temp)));
      p.y=Math.max(74,Math.min(H-74,p.y+d.y/mag*Math.min(mag,temp)));
    }
    temp*=0.94;
  }
  return pos;
}
function attributionClass(value) {
  if (value === "reader_diagram_observation" || value === "reader_modeling_inference") return "reader";
  if (value === "author_interpretation") return "interpretation";
  return "";
}
function edgeClass(e) {
  const classes=["edge"];
  const a=attributionClass(e.attribution);
  if (a) classes.push(a);
  if (e.kind === "classification") classes.push("classification");
  if (e.kind === "classification" && e.decision !== "author_assigned" && e.decision !== "criteria_match") classes.push("nonaffirmative");
  return classes.join(" ");
}
function renderGraph(nodes, edges) {
  const svg=$("graph"); svg.replaceChildren();
  const defs=svgEl("defs");
  const marker=svgEl("marker",{id:"arrow",viewBox:"0 0 10 10",refX:"8.5",refY:"5",markerWidth:"6",markerHeight:"6",orient:"auto-start-reverse"});
  marker.appendChild(svgEl("path",{d:"M 0 0 L 10 5 L 0 10 z",fill:"#536e80"}));
  defs.appendChild(marker); svg.appendChild(defs);
  if (!nodes.length) {
    const t=svgEl("text",{x:500,y:325,"text-anchor":"middle",fill:"#687987","font-size":16});
    t.textContent=activeTab === "case" ? "暂无案例节点或关系" : "模型中没有概念节点";
    svg.appendChild(t); return;
  }
  const positions=layout(nodes,edges);
  const seenPair=new Map();
  for (const e of edges) {
    const s=positions.get(String(e.source)), t=positions.get(String(e.target));
    if (!s || !t) continue;
    const pair=[String(e.source),String(e.target)].sort().join("||");
    const offset=seenPair.get(pair)||0; seenPair.set(pair,offset+1);
    const dx=t.x-s.x, dy=t.y-s.y, dist=Math.hypot(dx,dy)||1;
    const rs=nodeRadius(nodeById(e.source)||{}), rt=nodeRadius(nodeById(e.target)||{});
    const sx=s.x+dx/dist*rs, sy=s.y+dy/dist*rs;
    const ex=t.x-dx/dist*(rt+5), ey=t.y-dy/dist*(rt+5);
    const nx=-dy/dist, ny=dx/dist, curve=(offset%2 ? 1 : -1)*(9+Math.floor(offset/2)*9);
    const qx=(sx+ex)/2+nx*curve, qy=(sy+ey)/2+ny*curve;
    const g=svgEl("g",{class:edgeClass(e),tabindex:"0",role:"group"});
    const path=svgEl("path",{d:"M "+sx+" "+sy+" Q "+qx+" "+qy+" "+ex+" "+ey});
    const title=svgEl("title");
    title.textContent=(e.label||predicateLabel(e.predicate))+" · "+attribution(e.attribution).label+" · 证据 "+evidenceIds(e.evidence).join("、");
    g.appendChild(title); g.appendChild(path);
    const label=e.label || predicateLabel(e.predicate);
    const short=label.length>23 ? label.slice(0,22)+"…" : label;
    const tx=(sx+2*qx+ex)/4, ty=(sy+2*qy+ey)/4-4;
    const width=Math.min(280,Math.max(64,short.length*14+14));
    g.appendChild(svgEl("rect",{x:tx-width/2,y:ty-10,width,height:20,rx:4,class:"edge-label-bg"}));
    const text=svgEl("text",{x:tx,y:ty,class:"edge-label"}); text.textContent=short; g.appendChild(text);
    svg.appendChild(g);
  }
  for (const n of nodes) {
    const p=positions.get(String(n.id)); if (!p) continue;
    const classes=["node"];
    if (n.status==="disputed") classes.push("disputed");
    if (String(n.id)===selectedId) classes.push("selected");
    if (n.kind==="value") classes.push("value");
    if (n.kind==="missing") classes.push("missing");
    if (n.kind==="record") classes.push("record");
    if (n.class) classes.push("class-"+String(n.class).replace(/[^A-Za-z0-9_-]/g,""));
    const g=svgEl("g",{class:classes.join(" "),transform:"translate("+p.x+" "+p.y+")",tabindex:"0",role:"button","aria-label":nodeName(n)});
    const title=svgEl("title"); title.textContent=nodeName(n)+" · "+labelForClass(n.class); g.appendChild(title);
    g.appendChild(svgEl("circle",{r:nodeRadius(n)}));
    const label=nodeName(n), lines=[];
    for(let i=0;i<label.length;i+=9) lines.push(label.slice(i,i+9));
    const shown=lines.slice(0,3);
    const widest=Math.max(...shown.map(s=>s.length),2);
    const bg=svgEl("rect",{x:-widest*6.5-6,y:-shown.length*8-3,width:widest*13+12,height:shown.length*16+6,rx:3,class:"node-label-bg"});
    g.appendChild(bg);
    const text=svgEl("text",{x:0,y:-(shown.length-1)*8+4,"text-anchor":"middle"});
    shown.forEach((line,i)=>{const tspan=svgEl("tspan",{x:0,dy:i===0?0:16}); tspan.textContent=line; text.appendChild(tspan);});
    g.appendChild(text);
    g.addEventListener("click",()=>{selectedId=String(n.id); fillNodeSelect(); refresh();});
    g.addEventListener("keydown",ev=>{if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();selectedId=String(n.id);fillNodeSelect();refresh();}});
    svg.appendChild(g);
  }
}
function sourceMap() { return new Map((CASE.sources || []).map(s => [String(s.id),s])); }
function evidenceMap() { return new Map((CASE.evidence || []).map(e => [String(e.id),e])); }
function pageText(value) { return value === undefined || value === null || value === "" ? "未记录" : textValue(value); }
function renderEvidence(parent, ids) {
  const eMap=evidenceMap(), sMap=sourceMap();
  if (!ids.length) { add(parent,"p","未关联证据记录。","muted"); return; }
  for (const rawId of ids) {
    const id=String(rawId), ev=eMap.get(id);
    if (!ev) { add(parent,"p","证据记录缺失："+id,"muted"); continue; }
    const card=add(parent,"div","","card");
    add(card,"strong",ev.id || id);
    const src=sMap.get(String(ev.source));
    add(card,"p",src ? (src.title || src.id) : ("来源记录缺失："+textValue(ev.source)));
    const dl=add(card,"dl","","kv");
    const fields=[
      ["PDF页序",pageText(ev.pdfPages)],["印刷页码",pageText(ev.printedPages)],
      ["图表/位置",pageText(ev.locator)],["证据摘要",pageText(ev.summary)],
      ["证据归属",attribution(ev.attribution).label]
    ];
    if (src) {
      fields.push(["Zotero Key",pageText(src.zoteroKey)]);
      fields.push(["附件 Key",pageText(src.attachmentKey)]);
      fields.push(["本地路径",pageText(src.path)]);
    }
    for(const [k,v] of fields){add(dl,"dt",k);add(dl,"dd",v);}
  }
}
function assertionCard(parent,a,relatedTo) {
  const card=add(parent,"div","","card");
  const fact=attribution(a.attribution);
  add(card,"strong",predicateLabel(a.predicate));
  badge(card,fact.label,fact.cls);
  if (a.status) badge(card,STATUS[a.status]||a.status,a.status==="disputed"?"status-disputed":(a.status==="tentative"?"status-tentative":""));
  const subject=nodeById(a.subject);
  const isSubject=String(a.subject)===String(relatedTo);
  const hasObject=Object.prototype.hasOwnProperty.call(a,"object");
  const target=hasObject ? textValue(a.object) : textValue(a.value);
  const targetNode=hasObject ? nodeById(a.object) : null;
  const uncertainty=a.status==="disputed"?"（原文表值，存在冲突；未确认为定值）":"";
  add(card,"p",(isSubject?"→ ":"← ")+(subject?nodeName(subject):textValue(a.subject))+" · "+predicateLabel(a.predicate)+" · "+(targetNode?nodeName(targetNode):target)+uncertainty);
  if (a.scope !== undefined) add(card,"p","范围："+textValue(a.scope));
  add(card,"p","时点："+pageText(a.temporalScope));
  if (a.note) add(card,"p","备注："+textValue(a.note));
  add(card,"h3","原始证据");
  renderEvidence(card,evidenceIds(a.evidence));
  if(evidenceIds(a.conflictingEvidence).length){
    add(card,"h3","冲突证据（并列保留，不作裁决）");
    renderEvidence(card,evidenceIds(a.conflictingEvidence));
  }
}
function classificationCard(parent,c) {
  const card=add(parent,"div","","card");
  add(card,"strong","分类判断");
  const fact=attribution(c.attribution); badge(card,fact.label,fact.cls);
  badge(card,DECISION[c.decision]||c.decision||"判断未注明",
    c.decision==="insufficient_evidence"?"status-tentative":"");
  add(card,"p","分类体系："+textValue(c.scheme));
  const type=nodeById(c.type);
  add(card,"p","判断指向："+(type?nodeName(type):textValue(c.type)));
  add(card,"p","时点："+pageText(c.temporalScope));
  if(c.note)add(card,"p","备注："+textValue(c.note));
  if(Array.isArray(c.criteriaResults)&&c.criteriaResults.length){
    add(card,"h3","判据结果");
    const table=add(card,"table");
    const thead=add(table,"thead"), tr=add(thead,"tr");
    ["判据","特征","预期","实际记录","输入断言","结果","说明"].forEach(x=>add(tr,"th",x));
    const tbody=add(table,"tbody");
    for(const cr of c.criteriaResults){
      const row=add(tbody,"tr");
      add(row,"td",textValue(cr.criterion));
      const feature=FEATURES[cr.feature];
      add(row,"td",feature?(feature.label||feature.id)+" · "+feature.id:pageText(cr.feature));
      const pretty=v=>typeof v==="boolean"?(v?"是":"否"):textValue(v);
      add(row,"td",pretty(cr.expected));
      const actualCell=add(row,"td",pretty(cr.actual));
      const assertion=(CASE.assertions||[]).find(a=>String(a.id)===String(cr.assertion));
      if(assertion && assertion.status==="disputed") badge(actualCell,"值有争议","status-disputed");
      const assertedValue=assertion ? (Object.prototype.hasOwnProperty.call(assertion,"value")?assertion.value:assertion.object) : cr.assertion;
      const assertedNode=assertion && Object.prototype.hasOwnProperty.call(assertion,"object") ? nodeById(assertion.object) : null;
      add(row,"td",assertion ? predicateLabel(assertion.predicate)+"："+(assertedNode?nodeName(assertedNode):pretty(assertedValue)) : pageText(cr.assertion));
      add(row,"td",RESULT[cr.result]||cr.result||"未记录");
      add(row,"td",pageText(cr.reason));
    }
  }
  add(card,"h3","判断证据");
  renderEvidence(card,evidenceIds(c.evidence));
}
function renderDetail() {
  const box=$("detail"); box.replaceChildren();
  if (!selectedId) {
    add(box,"p","选择图中的一个节点，查看它的关系、属性断言、证据页码和判断归属。","muted");
    if (activeTab==="concept") {
      add(box,"h3","如何读图");
      add(box,"p","圆点代表模型中的类；箭头从允许的起点类别指向目标类别。选中类可查看其定义、适用特征和出入关系。");
    }
    return;
  }
  const n=nodeById(selectedId);
  if (!n) { add(box,"p","当前节点未找到。","muted"); return; }
  add(box,"h2",nodeName(n));
  badge(box,labelForClass(n.class));
  if(n.identityStatus) badge(box,"身份状态："+textValue(n.identityStatus));
  if(n.tier) badge(box,n.tier==="extension"?"扩展":"核心");
  if(n.note) add(box,"p",textValue(n.note));
  const excluded=new Set(["id","label","class","kind","source","note","identityStatus","tier"]);
  const extras=Object.entries(n).filter(([key])=>!excluded.has(key));
  if(extras.length){
    add(box,"h3","节点属性");
    const dl=add(box,"dl","","kv");
    for(const [k,v] of extras){add(dl,"dt",k);add(dl,"dd",textValue(v));}
  }
  if(activeTab==="concept"){
    const features=(DATA.model.features||[]).filter(f=>(f.domain||[]).includes(n.id));
    if(features.length){
      add(box,"h3","适用特征");
      for(const f of features){
        const card=add(box,"div","","card");
        add(card,"strong",f.label||f.id);
        add(card,"p",f.id+" · "+(f.datatype||"类型未注明")+(f.unit?" · 单位 "+f.unit:""));
        add(card,"p",f.definition||"");
      }
    }
    const rels=relatedEdges(selectedId);
    if(rels.length){
      add(box,"h3","一跳关系");
      for(const e of rels){
        const other=String(e.source)===selectedId?nodeById(e.target):nodeById(e.source);
        add(box,"p",(String(e.source)===selectedId?"→ ":"← ")+(other?nodeName(other):e.target)+" · "+e.label);
      }
    }
    return;
  }
  const assertionRecords=(CASE.assertions||[]).filter(a=>String(a.subject)===selectedId ||
    (Object.prototype.hasOwnProperty.call(a,"object") && String(a.object)===selectedId));
  if(assertionRecords.length){
    add(box,"h3","相关关系与属性");
    for(const a of assertionRecords) assertionCard(box,a,selectedId);
  }
  const classRecords=(CASE.classifications||[]).filter(c=>String(c.subject)===selectedId || String(c.type)===selectedId);
  if(classRecords.length){
    add(box,"h3","相关类型判断");
    for(const c of classRecords) classificationCard(box,c);
  }
  if(n.kind==="value" || n.kind==="missing"){
    const edge=currentEdges.find(e=>String(e.target)===selectedId);
    if(edge && edge.record && !assertionRecords.some(a=>String(a.id)===String(edge.record.id))){
      if(edge.kind==="assertion") assertionCard(box,edge.record,edge.source);
      else if(edge.kind==="classification") classificationCard(box,edge.record);
    }
  }
  if(!assertionRecords.length&&!classRecords.length&&n.kind!=="value"&&n.kind!=="missing")
    add(box,"p","暂无关联断言或分类判断记录。","muted");
}
function pageSummary(ids) {
  const eMap=evidenceMap();
  return evidenceIds(ids).map(id=>{
    const e=eMap.get(String(id));
    return e ? (textValue(e.pdfPages)+"页"+(e.printedPages?" / "+textValue(e.printedPages):"")) : ("证据缺失："+id);
  }).join("；") || "未关联证据";
}
function renderTable(nodes, edges) {
  const box=$("tableContent"); box.replaceChildren();
  if(activeTab==="concept"){
    const relationTable=add(box,"table");
    const h=add(add(relationTable,"thead"),"tr");
    ["起点类别","有向关系","终点类别","含义"].forEach(x=>add(h,"th",x));
    const body=add(relationTable,"tbody");
    const nodeMap=new Map(nodes.map(n=>[String(n.id),n]));
    for(const e of edges){
      const row=add(body,"tr");
      add(row,"td",nodeName(nodeMap.get(String(e.source)))+" ("+labelForClass(e.source)+")");
      add(row,"td",(nodeName(nodeMap.get(String(e.source)))+" → "+e.label+" → "+nodeName(nodeMap.get(String(e.target)))));
      add(row,"td",nodeName(nodeMap.get(String(e.target)))+" ("+labelForClass(e.target)+")");
      add(row,"td",e.definition);
    }
    const features=(DATA.model.features||[]).filter(f=>!selectedId||(f.domain||[]).includes(selectedId));
    const title=add(box,"h3","特征定义");
    title.className="subsection";
    const ft=add(box,"table"), fh=add(add(ft,"thead"),"tr");
    ["特征","适用类别","数据类型 / 单位","定义"].forEach(x=>add(fh,"th",x));
    const fb=add(ft,"tbody");
    for(const f of features){
      const row=add(fb,"tr");
      add(row,"td",(f.label||f.id)+" · "+f.id);
      add(row,"td",(f.domain||[]).map(labelForClass).join("、"));
      add(row,"td",(f.datatype||"未注明")+(f.unit?" / "+f.unit:""));
      add(row,"td",f.definition||"");
    }
    return;
  }
  if(!edges.length){
    add(box,"p","当前筛选下没有有向关系。","empty-note");
  } else {
    const table=add(box,"table"), head=add(add(table,"thead"),"tr");
    ["起点","有向关系","终点 / 属性值","判断归属","状态 / 时点","证据与页码"].forEach(x=>add(head,"th",x));
    const body=add(table,"tbody"), nodeMap=new Map(nodes.map(n=>[String(n.id),n]));
    for(const e of edges){
      const row=add(body,"tr");
      const s=nodeMap.get(String(e.source)),t=nodeMap.get(String(e.target));
      add(row,"td",s?nodeName(s):String(e.source));
      add(row,"td",(e.kind==="classification"?"类型判断 · ":"")+e.label);
      add(row,"td",t?nodeName(t):String(e.target));
      add(row,"td",attribution(e.attribution).label);
      add(row,"td",(STATUS[e.status]||e.status||"未注明")+" / "+pageText(e.temporalScope));
      let evidenceText=pageSummary(e.evidence);
      if(e.conflictingEvidence && e.conflictingEvidence.length)evidenceText+="；冲突证据："+pageSummary(e.conflictingEvidence);
      add(row,"td",evidenceText);
    }
  }
  const claims=(CASE.assertions||[]).filter(a=>!selectedId||String(a.subject)===selectedId||String(a.object)===selectedId||(!Object.prototype.hasOwnProperty.call(a,"object")&&"@value:"+a.id===selectedId));
  if(claims.length){
    const title=add(box,"h3","断言明细");
    title.className="subsection";
    const table=add(box,"table"), head=add(add(table,"thead"),"tr");
    ["对象","特征 / 关系","值或目标","归属","状态","备注","证据定位"].forEach(x=>add(head,"th",x));
    const body=add(table,"tbody");
    for(const a of claims){
      const row=add(body,"tr"), s=nodeMapGet(CASE.nodes,a.subject);
      add(row,"td",s?nodeName(s):textValue(a.subject));
      add(row,"td",predicateLabel(a.predicate));
      const isDisputed=a.status==="disputed";
      add(row,"td",(Object.prototype.hasOwnProperty.call(a,"value")?textValue(a.value):textValue(a.object))+(isDisputed?"（原文值；有争议）":""));
      add(row,"td",attribution(a.attribution).label);
      add(row,"td",STATUS[a.status]||a.status||"未注明");
      add(row,"td",pageText(a.note));
      let evidenceText=pageSummary(a.evidence);
      if(evidenceIds(a.conflictingEvidence).length)evidenceText+="；冲突证据："+pageSummary(a.conflictingEvidence);
      add(row,"td",evidenceText);
    }
  }
}
function nodeMapGet(nodes,id){return (nodes||[]).find(n=>String(n.id)===String(id));}
function renderSupplements() {
  const box=$("caseSupplements"); box.replaceChildren();
  if(activeTab!=="case") return;
  const sources=CASE.sources||[], gaps=CASE.gaps||[];
  const details=add(box,"details");
  add(details,"summary","来源与明确空缺 · "+sources.length+" 个来源 · "+gaps.length+" 条空缺");
  const inside=add(details,"div","","inside");
  const srcSection=add(inside,"section","","subsection");
  add(srcSection,"h2","文献来源");
  if(!sources.length) add(srcSection,"p","暂无来源记录；不推测文献条目。","muted");
  else {
    const table=add(srcSection,"table"),head=add(add(table,"thead"),"tr");
    ["来源 ID","文献","Zotero Key","附件 Key","本地路径"].forEach(x=>add(head,"th",x));
    const body=add(table,"tbody");
    for(const s of sources){
      const row=add(body,"tr");
      add(row,"td",textValue(s.id));add(row,"td",textValue(s.title));
      add(row,"td",pageText(s.zoteroKey));add(row,"td",pageText(s.attachmentKey));add(row,"td",pageText(s.path));
    }
  }
  const gapSection=add(inside,"section","","subsection");
  add(gapSection,"h2","明确空缺");
  if(!gaps.length) add(gapSection,"p","没有录入空缺记录。","muted");
  else {
    const table=add(gapSection,"table"),head=add(add(table,"thead"),"tr");
    ["对象","字段","状态","原因"].forEach(x=>add(head,"th",x));
    const body=add(table,"tbody");
    for(const g of gaps){
      const row=add(body,"tr");
      const n=nodeById(g.subject);
      add(row,"td",n?nodeName(n):pageText(g.subject));
      add(row,"td",pageText(g.field));add(row,"td",pageText(g.status));add(row,"td",pageText(g.reason));
    }
  }
}
$("conceptTab").addEventListener("click",()=>{activeTab="concept";selectedId="Dwelling";focusOneHop=true;refresh();});
$("caseTab").addEventListener("click",()=>{activeTab="case";selectedId="R_8";focusOneHop=true;refresh();});
$("graphButton").addEventListener("click",()=>{activeView="graph";refresh();});
$("tableButton").addEventListener("click",()=>{activeView="table";refresh();});
$("focusButton").addEventListener("click",()=>{focusOneHop=!focusOneHop;refresh();});
$("nodeSelect").addEventListener("change",ev=>{selectedId=ev.target.value;refresh();});
refresh();
</script>
</body>
</html>
'''

def read_json(path: Path, *, empty_on_missing: bool = False) -> Any:
    if not path.exists():
        if empty_on_missing:
            return {"nodes": [], "evidence": [], "sources": [], "assertions": [], "classifications": [], "gaps": []}
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> None:
    parser = argparse.ArgumentParser(description="生成单体层知识图谱离线浏览页")
    parser.add_argument("--model", type=Path, default=None, help="模型定义 JSON")
    parser.add_argument("--case", type=Path, default=None, help="案例图谱 JSON")
    parser.add_argument("--output", type=Path, default=None, help="输出 HTML")
    args = parser.parse_args()
    model_path = (args.model or DEFAULT_DIR / "模型定义.json").expanduser()
    case_path = (args.case or DEFAULT_DIR / "案例图谱.json").expanduser()
    output_path = (args.output or DEFAULT_DIR / "图谱浏览.html").expanduser()
    model = read_json(model_path)
    case = read_json(case_path, empty_on_missing=True)
    if not isinstance(model, dict):
        raise ValueError("模型定义必须是 JSON 对象")
    if not isinstance(case, dict):
        raise ValueError("案例图谱必须是 JSON 对象")
    for key in ("nodes", "evidence", "sources", "assertions", "classifications", "gaps"):
        case.setdefault(key, [])
        if not isinstance(case[key], list):
            raise ValueError(f"案例图谱字段 {key} 必须是数组")
    payload = json.dumps({"model": model, "case": case}, ensure_ascii=True, separators=(",", ":"))
    # Prevent a JSON string from closing the embedded script element.
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
    print(f"写入 {output_path}")
    print(f"模型类 {len(model.get('classes', []))}，关系 {len(model.get('relations', []))}，案例节点 {len(case['nodes'])}，断言 {len(case['assertions'])}，分类 {len(case['classifications'])}，证据 {len(case['evidence'])}，空缺 {len(case['gaps'])}")

if __name__ == "__main__":
    main()
