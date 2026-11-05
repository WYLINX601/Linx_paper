#!/usr/bin/env python3
"""Generate the findings-first courtyard pilot. No vault or database writes."""
import argparse
import base64
import hashlib
import json
import re
from pathlib import Path

VERSION = 'CMS-CY-render-2.0'
PAGE = '院落与外部空间审核.html'  # Stable incoming links; visible title is findings-first.
NOTE = '院落试例说明.md'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unique(items, what):
    result = {x['id']: x for x in items}
    if len(result) != len(items):
        raise ValueError(f'duplicate {what} IDs')
    return result


def validate(master, text_dir=None):
    p = master['courtyard_pilot']
    maps = {k: unique(p[k], k) for k in ['nodes', 'relations', 'evidence', 'findings', 'views', 'cases']}
    nodes, rels, evs = (maps[k] for k in ['nodes', 'relations', 'evidence'])
    papers = {x['key']: x for x in master['papers']}
    materials = {x['id']: x for paper in master['papers'] for x in paper['materials']}
    checks = []

    def check(ok, label):
        if not ok:
            raise ValueError(label)
        checks.append(label)

    check(not (nodes.keys() & rels.keys()), 'node/relation IDs distinct')
    for e in evs.values():
        check(e['paper'] in papers and e['material'] in materials, e['id'] + ': source exists')
        m = materials[e['material']]
        check(m['source_key'] == e['paper'], e['id'] + ': source aligned')
        page_ok = m['pdf_page'] == e['pdf_page']
        if e.get('material_page_relation') == 'continuation':
            page_ok = e['pdf_page'] == m['pdf_page'] + 1
        check(page_ok, e['id'] + ': page or declared continuation aligned')
        check(set(e['claim_ids']) <= {c['id'] for c in papers[e['paper']]['claims']}, e['id'] + ': original references retained')
        if text_dir:
            text = (Path(text_dir) / (e['paper'] + '-selected.txt')).read_text()
            parts = re.split(r'=== PDF (\d+) ===', text)
            pages = {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}
            norm = lambda s: re.sub(r'\s+', '', s)
            check(e['pdf_page'] in pages, e['id'] + ': exact page available')
            for quote in [e['quote']] + ([e['quote_extra']] if e.get('quote_extra') else []):
                check(norm(quote) in norm(pages[e['pdf_page']]), e['id'] + ': quotation matches exact PDF page')
    for category in ['nodes', 'relations', 'findings', 'cases']:
        for x in p[category]:
            check(bool(x['evidence']) and set(x['evidence']) <= evs.keys(), x['id'] + ': evidence valid')
            for f in x.get('fields', []):
                check(bool(f['evidence']) and set(f['evidence']) <= set(x['evidence']), x['id'] + ': field sources explicit')
            for image in x.get('images', []):
                check(image in materials and bool(materials[image].get('asset')), x['id'] + ': image exists')
    for n in nodes.values():
        check(set(n.get('example_refs', [])) <= maps['cases'].keys(), n['id'] + ': examples valid')
    for c in p['cases']:
        check(c['type_ref'] is None or c['type_ref'] in nodes, c['id'] + ': optional type valid')
    for r in rels.values():
        check(r['source'] in nodes and r['target'] in nodes, r['id'] + ': endpoints valid')
        check(set(r['views']) <= maps['views'].keys(), r['id'] + ': views valid')
    covered_nodes, covered_edges = set(), set()
    for v in p['views']:
        vn = set(v['nodes'])
        vr = [r for r in rels.values() if v['id'] in r['views']]
        check(vn <= nodes.keys() and set(v['positions']) == vn, v['id'] + ': complete display layout')
        check(all(r['source'] in vn and r['target'] in vn for r in vr), v['id'] + ': displayed endpoints valid')
        check(v['initial'] in vn, v['id'] + ': initial selection valid')
        covered_nodes.update(vn)
        covered_edges.update(r['id'] for r in vr)
    check(covered_nodes == nodes.keys() and covered_edges == rels.keys(), 'all network records reachable')
    for f in p['findings']:
        check(f['view'] in maps['views'], f['id'] + ': thematic placement valid')
        check(all(evs[k]['paper'] == f['paper'] for k in f['evidence']), f['id'] + ': author attribution consistent')
    seen_images = set()
    for image in p['image_notes']:
        check(image['material'] not in seen_images, 'one maintained image note per material')
        seen_images.add(image['material'])
        check(bool(materials[image['material']].get('asset')), image['material'] + ': original image reference valid')
        check(set(image['findings']) <= maps['findings'].keys(), image['material'] + ': findings links valid')
        for observation in image['observations']:
            check(observation['attribution'] == '阅读者图像说明', image['material'] + ': local observations separately attributed')
    check(all(set(x.get('images', [])) <= seen_images for k in ['nodes', 'findings', 'cases'] for x in p[k]), 'all displayed images have maintained notes')
    check(not (set(p['revision']['removed_graph_records']) & (nodes.keys() | rels.keys())), 'retired observation and conjecture records absent from network')
    alts = [r for r in p['relations'] if r.get('alternative_group')]
    check(len(alts) == 2 and len({r['alternative_group'] for r in alts}) == 1, 'source alternatives preserved')
    return checks


def build(source, images_dir, output_dir, template=None, text_dir=None):
    source, images_dir, output_dir = map(Path, [source, images_dir, output_dir])
    master = json.loads(source.read_text())
    p = master['courtyard_pilot']
    checks = validate(master, text_dir)
    paper_keys = {e['paper'] for e in p['evidence']}
    papers = {x['key']: {k: x[k] for k in ['key', 'title', 'authors', 'year', 'attachment', 'imprint', 'sha256']} for x in master['papers'] if x['key'] in paper_keys}
    materials = {x['id']: x for paper in master['papers'] for x in paper['materials']}
    images = {}
    for record in p['image_notes']:
        i = record['material']
        m = materials[i]
        path = images_dir / Path(m['asset']).name
        provenance = json.loads(Path(str(path) + '.provenance.json').read_text())
        if provenance['source_path'] != m['asset'] or provenance['sha256'] != sha(path):
            raise ValueError('Image provenance mismatch: ' + i)
        images[i] = {k: m[k] for k in ['title', 'locator', 'asset', 'source_key', 'pdf_page']}
        images[i].update(sha256=sha(path), data='data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode())
    payload = dict(pilot=p, papers=papers, images=images, master_sha256=sha(source), generator_version=VERSION)
    template = Path(template) if template else Path(__file__).with_name('courtyard_template.html')
    html = template.read_text()
    if html.count('__SNAPSHOT__') != 1:
        raise ValueError('Expected one template insertion marker')
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / PAGE).write_text(html.replace('__SNAPSHOT__', json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c')))
    evs = {e['id']: e for e in p['evidence']}

    def refs(ids):
        return '；'.join(f'[{eid}](#{eid.lower()})' for eid in ids)

    note = ['---', 'type: research-deliverable', 'status: literature-results-pilot', 'updated: ' + p['updated'], 'generated_from: 拆解主源.json#courtyard_pilot', '---', '', '# ' + p['title'], '', p['purpose'], '', f'[打开成果与关系视图]({PAGE}) · [返回成果入口](README.md) · [维护主源](拆解主源.json) · [执行记录](院落试例核验.json)', '', '## 文献已经形成的成果', '']
    for v in p['views']:
        note += ['### ' + v['name'], '']
        for f in [f for f in p['findings'] if f['view'] == v['id']]:
            paper = papers[f['paper']]
            note += ['#### ' + f['title'], '', f['summary'], '', f'{"、".join(paper["authors"])}（{paper["year"]}），{f["attribution"]}。{refs(f["evidence"])}。', '']
    note += ['## 类型、要素与特征', '', '| 类型或要素 | 文献描述 | 出处 |', '|---|---|---|']
    cell = lambda s: str(s).replace('|', '／').replace('\n', '<br>')
    for n in p['nodes']:
        description = n['summary'] + ''.join(' ' + f['label'] + '：' + f['value'] + '。' for f in n['fields'])
        note += [f'| {cell(n["name"])}〔{n["kind"]}〕 | {cell(description)} | {refs(n["evidence"])} |']
    note += ['', '## 文献所述联系', '', '| 两端 | 联系 | 文献描述与出处 |', '|---|---|---|']
    names = {n['id']: n['name'] for n in p['nodes']}
    for r in p['relations']:
        note += [f'| {names[r["source"]]} → {names[r["target"]]} | {cell(r["name"])} | {cell(r["summary"])} {refs(r["evidence"])} |']
    note += ['', '## 图片说明汇总', '']
    for record in p['image_notes']:
        image = images[record['material']]
        note += ['### ' + record['caption'], '', f'![{record["caption"]}](../../{image["asset"]})', '', record['role'] + '。对应：' + '、'.join(next(f['title'] for f in p['findings'] if f['id'] == i) for i in record['findings']) + '。', '', f'{image["locator"]}；图文：{"、".join(papers[image["source_key"]]["authors"])}；材料编号 `{record["material"]}`。', '']
        note += [o['attribution'] + '：' + o['text'] for o in record['observations']] + ['']
    note += ['## 文献中的案例记录', '']
    for c in p['cases']:
        note += [f'- **{c["name"]}**：{c["summary"]} {refs(c["evidence"])}。']
    note += ['', '## 原文与出处', '']
    for e in p['evidence']:
        paper = papers[e['paper']]
        note += ['### ' + e['id'], '', '> ' + e['quote']]
        if e.get('quote_extra'):
            note += ['', '> ' + e['quote_extra']]
        note += ['', f'{"、".join(paper["authors"])}（{paper["year"]}）《{paper["title"]}》；{e["locator"]}；{e["attribution"]}。Zotero `{e["paper"]}`／附件 `{paper["attachment"]}`；[打开原页](zotero://open-pdf/library/items/{paper["attachment"]}?page={e["pdf_page"]})。', '']
    note += ['## 本例组织与维护', '', *['- ' + s for s in p['organization']['principles']], '', p['reading']['coverage'], '', '三个视图是本例为阅读组织的分组；内容按作者归属保存，图中位置仅为页面排版。现行事实只在 `courtyard_pilot` 维护，旧版保存在[调整前归档](../../' + p['revision']['archive'] + ')。', '', '本轮为文献成果提取与呈现，未改动D03、双基准、V01、Zotero及Neo4j。', '', f'版本 {p["version"]}；主源 SHA-256：`{sha(source)}`；生成器：`{VERSION}`。', '']
    (output_dir / NOTE).write_text('\n'.join(note))
    manifest = dict(generator_version=VERSION, source_sha256=sha(source), counts={k: len(p[k]) for k in ['findings', 'nodes', 'relations', 'evidence', 'views', 'image_notes', 'cases']}, checks=checks, outputs={n: sha(output_dir / n) for n in [PAGE, NOTE]}, image_sha256={k: v['sha256'] for k, v in images.items()}, template_sha256=sha(template))
    (output_dir / 'build-checks.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['source', 'images-dir', 'output-dir']:
        parser.add_argument('--' + flag, required=True)
    parser.add_argument('--template')
    parser.add_argument('--evidence-text-dir')
    args = parser.parse_args()
    result = build(args.source, args.images_dir, args.output_dir, args.template, args.evidence_text_dir)
    print(json.dumps({'counts': result['counts'], 'checks_passed': len(result['checks']), 'outputs': result['outputs']}, ensure_ascii=False, indent=2))
