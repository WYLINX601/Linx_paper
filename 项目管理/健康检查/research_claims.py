"""Generate read-only views for research questions and claims; publish via mac-paper."""
from pathlib import Path
import argparse, json, posixpath, subprocess
from urllib.parse import quote
import yaml

ROOT = Path('/Users/wangyuelin/Desktop/Obsidian/Paper')
BRIDGE = '/Users/wangyuelin/.hermes/profiles/academic/bin/mac-paper'
T_GLOB = '主题研究/*/*.md'
Q_GLOB = '主题研究/*/问题/*.md'
C_GLOB = '主题研究/*/论点/*.md'
INDEX = '项目管理/研究论证索引.md'
GRAPH = '项目管理/研究论证关系.json'
TOPIC_INDEX = '主题研究/README.md'
ROLE_ORDER = ['前提', '比较', '解释', '表达', '检验', '综合']
Q_STATUS = {'open', 'active', 'resolved', 'merged', 'retired'}
C_STATUS = {'candidate', 'working', 'supported', 'contested', 'superseded'}
C_KIND = {'原文结论', '文献综合', '研究判断', '候选规则', '工作规则'}
REL = {'supports', 'qualifies', 'contradicts', 'refines', 'supersedes', 'depends_on'}


def read(path):
    r = subprocess.run([BRIDGE, '--timeout', '30', 'read', path], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    if not d.get('ok'):
        raise RuntimeError(d)
    return d['result']['text']


def meta(text):
    if not text.startswith('---\n'):
        raise ValueError('missing frontmatter')
    return yaml.safe_load(text.split('---', 2)[1])


def block(text, name, body, anchor=None):
    begin = '<!-- ' + name + ':start -->'
    end = '<!-- ' + name + ':end -->'
    new = begin + '\n' + body.rstrip() + '\n' + end
    if begin in text:
        assert text.count(begin) == 1 and text.count(end) == 1, name
        a, b = text.split(begin)
        _, c = b.split(end)
        return a + new + c
    if anchor and anchor in text:
        return text.replace(anchor, new + '\n\n' + anchor, 1)
    return text.rstrip() + '\n\n' + new + '\n'


def link(source, target, label):
    rel = posixpath.relpath(target.split('#')[0], posixpath.dirname(source) or '.')
    frag = '#' + quote(target.split('#', 1)[1]) if '#' in target else ''
    return '[' + str(label).replace('|', '／') + '](' + quote(rel) + frag + ')'


def cell(v):
    return str(v).replace('|', '／').replace('\n', ' ')


def note(uid, title, body):
    fm = {'wiki_id': uid, 'type': 'derived-index', 'status': 'active', 'summary': title}
    return '---\n' + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=120) + '---\n\n# ' + title + '\n\n' + body


def discover(read_fn):
    topics = {}
    for p in sorted(ROOT.glob(T_GLOB)):
        rel = str(p.relative_to(ROOT))
        s = read_fn(rel)
        if not s.startswith('---\n'):
            continue
        m = meta(s)
        if m.get('type') != 'research-topic':
            continue
        topics[m['wiki_id']] = {'path': rel, 'meta': m, 'title': m['topic_title'], 'role': m['research_role']}
    assert topics, 'no research topics discovered'
    by_path = {v['path']: k for k, v in topics.items()}

    questions = {}
    for p in sorted(ROOT.glob(Q_GLOB)):
        rel = str(p.relative_to(ROOT))
        m = meta(read_fn(rel))
        assert m.get('type') == 'research-question', rel
        questions[m['wiki_id']] = {'path': rel, 'meta': m}

    claims = {}
    for p in sorted(ROOT.glob(C_GLOB)):
        rel = str(p.relative_to(ROOT))
        m = meta(read_fn(rel))
        assert m.get('type') == 'research-claim', rel
        claims[m['wiki_id']] = {'path': rel, 'meta': m}

    ids = list(topics) + list(questions) + list(claims)
    assert len(ids) == len(set(ids)), 'duplicate wiki_id across topics/questions/claims'

    for qid, q in questions.items():
        m = q['meta']
        topic = m['primary_topic']
        assert topic in by_path, (qid, 'unknown primary_topic')
        assert Path(q['path']).parent.parent == Path(topic).parent, (qid, 'question is not under its primary topic directory')
        assert isinstance(m.get('order'), int), (qid, 'order must be an integer')
        assert m.get('logic_role') in ROLE_ORDER, (qid, 'unknown logic_role')
        assert m.get('status') in Q_STATUS, (qid, 'unknown status')
        assert m.get('question_title') and m.get('summary'), (qid, 'missing title/summary')

    for cid, c in claims.items():
        m = c['meta']
        topic = m['primary_topic']
        assert topic in by_path, (cid, 'unknown primary_topic')
        assert Path(c['path']).parent.parent == Path(topic).parent, (cid, 'claim is not under its primary topic directory')
        assert m.get('status') in C_STATUS, (cid, 'unknown status')
        assert m.get('claim_kind') in C_KIND, (cid, 'unknown claim_kind')
        qs = m.get('claim_questions') or []
        assert qs and set(qs) <= set(questions), (cid, 'claim_questions must reference existing questions')
        ev = m.get('claim_evidence') or []
        assert ev, (cid, 'claim_evidence required')
        for e in ev:
            assert e.get('source') and e.get('locator') and e.get('use'), (cid, 'evidence needs source/locator/use')
            src = e['source']
            if not str(src).startswith('http'):
                assert (ROOT / src).is_file() or read_fn(src), (cid, 'missing evidence source: ' + src)
        for r in m.get('claim_relations') or []:
            assert r.get('to') in claims and r['to'] != cid, (cid, 'unknown/self relation target')
            assert r.get('type') in REL, (cid, 'unknown relation type')
    return topics, by_path, questions, claims


def topic_block(topic, questions, claims):
    path = topic['path']
    qs = sorted([q for q in questions.values() if q['meta']['primary_topic'] == path],
                key=lambda q: (q['meta']['order'], q['meta']['wiki_id']))
    body = '## 子问题与研究逻辑\n\n> 本节由子问题页与论点页生成；研究判断在各页维护，主题不复制论点全文。\n\n'
    body += '**研究逻辑：** ' + str(topic['meta'].get('topic_logic') or '待补充：说明各子问题的分工、先后或依赖。') + '\n\n'
    if not qs:
        body += '本主题尚未建立独立子问题页。\n'
        return body
    body += '| 序 | 子问题 | 逻辑作用 | 状态 | 已形成论点 |\n|---:|---|---|---|---:|\n'
    for i, q in enumerate(qs, 1):
        n = sum(1 for c in claims.values() if q['meta']['wiki_id'] in (c['meta'].get('claim_questions') or []))
        body += f"| {i} | {link(path, q['path'], q['meta']['question_title'])} | {cell(q['meta']['logic_role'])} | {cell(q['meta']['status'])} | {n} |\n"
    return body


def question_block(q, claims):
    path = q['path']
    cs = sorted([c for c in claims.values() if q['meta']['wiki_id'] in (c['meta'].get('claim_questions') or [])],
                key=lambda c: c['meta']['wiki_id'])
    body = '## 当前回答与关联论点\n\n> 本节由论点页的 `claim_questions` 生成；一个论点可回答多个问题，不在此复制主张全文。\n\n'
    if not cs:
        body += '尚无独立论点页；本问题保持开放，不补造结论。\n'
        return body
    body += '| 论点 | 状态 | 主张 | 依据数 |\n|---|---|---|---:|\n'
    for c in cs:
        m = c['meta']
        body += f"| {link(path, c['path'], m['claim_title'])} | {cell(m['status'])} | {cell(m['summary'])} | {len(m.get('claim_evidence') or [])} |\n"
    return body


def claim_block(c, topics, by_path, questions, claims):
    path = c['path']
    m = c['meta']
    body = '## 关联入口\n\n> 本节由关系字段生成；不在此重复章节采用关系。\n\n'
    body += '- **所属主题**：' + link(path, m['primary_topic'], topics[by_path[m['primary_topic']]]['title']) + '\n'
    body += '- **回答的问题**：' + '、'.join(link(path, questions[x]['path'], questions[x]['meta']['question_title']) for x in m['claim_questions']) + '\n'
    rels = m.get('claim_relations') or []
    if rels:
        body += '- **关联论点**：' + '；'.join(link(path, claims[r['to']]['path'], claims[r['to']]['meta']['claim_title']) + '（' + r['type'] + ('：' + cell(r['note']) if r.get('note') else '') + '）' for r in rels) + '\n'
    else:
        body += '- **关联论点**：暂未建立与其他论点的直接关系。\n'
    return body


def index_body(topics, by_path, questions, claims):
    qs = sorted(questions.values(), key=lambda q: (q['meta']['primary_topic'], q['meta']['order'], q['meta']['wiki_id']))
    cs = sorted(claims.values(), key=lambda c: (c['meta']['primary_topic'], c['meta']['wiki_id']))
    open_qs = [q for q in qs if not any(q['meta']['wiki_id'] in (c['meta'].get('claim_questions') or []) for c in cs)]
    body = '本页由 `项目管理/健康检查/research_claims.py` 生成；研究判断仍在各子问题页与论点页维护，不在此复制或改判。\n\n'
    active = [t for t in topics.values() if any(q['meta']['primary_topic'] == t['path'] for q in qs)]
    body += f"当前 {len(topics)} 个主题中 {len(active)} 个已建立子问题页；共 {len(qs)} 个子问题、{len(cs)} 个论点。"
    body += ('全部子问题均已关联至少一个论点页。\n\n' if not open_qs else f"其中 {len(open_qs)} 个问题尚无独立论点页。\n\n")
    body += '未列出的主题尚未建立独立子问题页，不表示该主题没有研究内容；既有分析文字仍在各主题页维护，按实际使用逐步接入。\n\n'
    body += '## 按主题\n\n| 主题 | 子问题 | 论点 | 开放问题 |\n|---|---:|---:|---:|\n'
    for t in active:
        tq = [q for q in qs if q['meta']['primary_topic'] == t['path']]
        tc = [c for c in cs if c['meta']['primary_topic'] == t['path']]
        to = [q for q in open_qs if q['meta']['primary_topic'] == t['path']]
        body += f"| {link(INDEX, t['path'], '〔' + t['role'] + '〕' + t['title'])} | {len(tq)} | {len(tc)} | {len(to)} |\n"
    rest = [t for t in topics.values() if t not in active]
    if rest:
        body += '\n尚未建立子问题页的主题：' + '、'.join(link(INDEX, t['path'], t['title']) for t in rest) + '。\n'
    body += '\n## 论点清单\n\n| 论点 | 主题 | 性质 | 状态 | 主张 |\n|---|---|---|---|---|\n'
    for c in cs:
        m = c['meta']; t = topics[by_path[m['primary_topic']]]
        body += f"| {link(INDEX, c['path'], m['claim_title'])} | {cell(t['title'])} | {cell(m['claim_kind'])} | {cell(m['status'])} | {cell(m['summary'])} |\n"
    body += '\n## 尚待回答\n\n'
    if open_qs:
        body += '| 子问题 | 主题 | 逻辑作用 |\n|---|---|---|\n'
        for q in open_qs:
            m = q['meta']; t = topics[by_path[m['primary_topic']]]
            body += f"| {link(INDEX, q['path'], m['question_title'])} | {cell(t['title'])} | {cell(m['logic_role'])} |\n"
    else:
        body += '当前每个子问题都至少有一个关联论点页。\n'
    body += '\n## 使用与维护\n\n新建或修改子问题、论点后，在Mac学术环境运行 `research_claims.py --check`；更新时先生成到Paper库外目录，审核差异后用最新SHA发布。论点状态不代表章节采用或实证完成。维护判断见 ' + link(INDEX, '项目管理/子问题与论点维护规则.md', '子问题与论点维护规则') + '。\n'
    return body


def generate(read_fn):
    topics, by_path, questions, claims = discover(read_fn)
    out = {}
    for t in topics.values():
        if not any(q['meta']['primary_topic'] == t['path'] for q in questions.values()):
            continue
        p = t['path']; s = read_fn(p)
        out[p] = block(s, 'research-questions', topic_block(t, questions, claims), '## 当前认识与状态')
    for q in questions.values():
        p = q['path']; s = read_fn(p)
        out[p] = block(s, 'question-claims', question_block(q, claims), '## 分歧与未决')
    for c in claims.values():
        p = c['path']; s = read_fn(p)
        out[p] = block(s, 'claim-links', claim_block(c, topics, by_path, questions, claims), '## 变更记录')
    out[INDEX] = note('research-argument-index', '研究论证索引', index_body(topics, by_path, questions, claims))

    nodes = []
    for tid, t in topics.items():
        nodes.append({'id': tid, 'kind': 'topic', 'title': t['title'], 'status': t['meta'].get('status'), 'path': t['path']})
    for qid, q in questions.items():
        nodes.append({'id': qid, 'kind': 'question', 'title': q['meta']['question_title'], 'status': q['meta']['status'], 'path': q['path']})
    for cid, c in claims.items():
        nodes.append({'id': cid, 'kind': 'claim', 'title': c['meta']['claim_title'], 'status': c['meta']['status'], 'path': c['path']})
    edges = []
    for qid, q in questions.items():
        edges.append({'from': by_path[q['meta']['primary_topic']], 'to': qid, 'type': 'contains'})
    for cid, c in claims.items():
        for qid in c['meta']['claim_questions']:
            edges.append({'from': cid, 'to': qid, 'type': 'answers'})
        for r in c['meta'].get('claim_relations') or []:
            edges.append({'from': cid, 'to': r['to'], 'type': r['type'], 'note': r.get('note', '')})
    out[GRAPH] = json.dumps({'generated_from': '项目管理/健康检查/research_claims.py', 'nodes': nodes, 'edges': edges},
                            ensure_ascii=False, indent=2) + '\n'

    p = TOPIC_INDEX; s = read_fn(p)
    tq = len(questions); tc = len(claims)
    b = '## 子问题与论点\n\n> 本节为派生入口；研究判断在各主题页维护。\n\n'
    b += f"当前共 {tq} 个子问题、{tc} 个论点。" + link(p, INDEX, '查看研究论证索引') + ' · ' + link(p, '项目管理/子问题与论点维护规则.md', '维护规则') + '。\n'
    out[p] = block(s, 'research-claim-index', b)

    open_qs = sum(1 for q in questions.values() if not any(q['meta']['wiki_id'] in (c['meta'].get('claim_questions') or []) for c in claims.values()))
    stats = {'topics': len(topics), 'questions': len(questions), 'claims': len(claims), 'edges': len(edges), 'open_questions': open_qs}
    return out, stats


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--output-dir', type=Path)
    a = ap.parse_args()
    if not a.check and not a.output_dir:
        ap.error('choose --check or --output-dir')
    if a.output_dir and a.output_dir.resolve().is_relative_to(ROOT):
        ap.error('output must be outside Paper')
    cache = {}

    def cached(p):
        if p not in cache:
            cache[p] = read(p) if (ROOT / p).exists() else ''
        return cache[p]

    out, stats = generate(cached)
    changed = [p for p, s in out.items() if s != cached(p)]
    if a.output_dir:
        for p, s in out.items():
            f = a.output_dir / p
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(s)
    print(json.dumps({**stats, 'out_of_sync': changed}, ensure_ascii=False, indent=2))
    if a.check and changed:
        raise SystemExit(1)
