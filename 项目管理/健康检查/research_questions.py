"""Render thesis-level questions without inferring lower-level associations."""
import copy
import json
import re
import yaml
import posixpath
from urllib.parse import quote

ROUTE = '研究成果/〔研究路线〕论文研究路径/研究路径结构.json'
QUESTIONS = '论文章节/研究问题.md'
INDEX = '项目管理/研究论证索引.md'
GRAPH = '项目管理/研究论证关系.json'
EXISTING_INDEX = '项目管理/既有主题论证索引.md'
EXISTING_GRAPH = '项目管理/既有主题论证关系.json'
ASSOCIATIONS = ('topics', 'subquestions', 'claims', 'chapters', 'artifacts')
MODE = 'research-question-skeleton'


def validate(route):
    questions = route.get('research_questions') or []
    if not questions:
        assert route.get('view_mode') != MODE, 'question skeleton requires declarations'
        return []
    assert route.get('view_mode') == MODE, 'declare the question-skeleton view explicitly'
    assert route.get('logic_status') == 'pending-discussion'
    assert route.get('association_status') == 'deferred'
    assert route.get('source_document') and route.get('source_note') and route.get('source_locator')
    assert not route['edges'], 'unreviewed question dependencies must remain empty'
    ids = [q['id'] for q in questions]
    uids = [q['wiki_id'] for q in questions]
    assert len(ids) == len(set(ids)) and len(uids) == len(set(uids)), 'duplicate question identity'
    for q in questions:
        assert re.fullmatch(r'RQ[1-9][0-9]*', q['id'])
        assert re.fullmatch(r'[a-z][a-z0-9-]*', q['wiki_id'])
        assert all(q.get(k) for k in ('title', 'content', 'expected_outputs', 'source_locator'))
        assert q['status'] in {'open', 'active', 'resolved', 'merged', 'retired'}
        assert q.get('logic_role') is None, 'logic roles require a separate discussion'
        assert set(q['associations']) == set(ASSOCIATIONS)
        assert all(q['associations'][k] == [] for k in ASSOCIATIONS), 'deferred mappings must be empty'
    refs = [n['question_id'] for n in route['nodes']]
    assert refs == ids, 'route nodes must reference each declared question once in display order'
    by_id = {q['id']: q for q in questions}
    for n in route['nodes']:
        assert n['id'] == by_id[n['question_id']]['wiki_id'], 'stable question/route identities differ'
        assert not any(k in n for k in ('title', 'topics', 'status')), 'question text is maintained only in declarations'
    return questions


def resolve_route(route):
    questions = validate(route)
    result = copy.deepcopy(route)
    if questions:
        by_id = {q['id']: q for q in questions}
        for n in result['nodes']:
            q = by_id[n['question_id']]
            n.update(title=q['id'] + ' ' + q['title'], topics=[], status='问题开放；逻辑关系与下层映射待讨论')
    return result


def note(uid, title, body):
    fm = {'wiki_id': uid, 'type': 'derived-index', 'status': 'active', 'summary': title}
    return '---\n' + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + '---\n\n# ' + title + '\n\n' + body


def cell(text):
    return str(text).replace('|', '／').replace('\n', ' ')


def link(source, target, title):
    path, _, fragment = target.partition('#')
    relative = posixpath.relpath(path, posixpath.dirname(source) or '.')
    return '[' + cell(title) + '](' + quote(relative) + ('#' + quote(fragment) if fragment else '') + ')'


def boundary(route):
    source_label = route.get('source_label') or '用户提供的方向修订文件'
    text = ('本页依据[[' + route['source_note'] + '|' + source_label + ']]生成。'
            '问题文本、内容和预期成果唯一维护在[[' + ROUTE + ']]的 `research_questions`，'
            '研究定位仍以[[context/PROJECT_CONTEXT.md]]为准。\n\n'
            '**本轮只更新上层研究问题。问题之间的论证关系、逻辑角色与主题等下层映射均待讨论；'
            '空关系不是没有研究内容，也不是对既有积累的否定。不得由问题顺序推定依赖、因果或研究完成。**\n\n')
    if route.get('positioning_note'):
        text += '> **定位状态：** ' + route['positioning_note'] + '\n\n'
    return text


def generate(route):
    questions = validate(route)
    assert questions, 'no current thesis-level questions'
    body = boundary(route)
    body += '## 研究问题\n\n'
    if route.get('core_question'):
        body += '**核心问题：** ' + route['core_question'] + '\n\n'
    for q in questions:
        body += '<a id="' + q['id'].lower() + '"></a>\n'
        body += '### ' + q['id'] + ' ' + q['title'] + '\n\n'
        body += q['content'] + '\n\n'
        body += '- **预期成果**：' + '；'.join(q['expected_outputs']) + '。\n'
        body += '- **状态**：开放，尚无本轮研究结论。\n'
        body += '- **逻辑作用与关联**：待讨论；暂不关联主题、子问题、论点、章节或成果。\n'
        body += '- **来源定位**：' + q['source_locator'] + '。\n\n'
    body += ('## 使用边界\n\n文档中的假设、创新点和相关研究线索仍需验证；本次更新不构成文献论证、'
             '样本确定、方法实施或有效性验证。旧主题内部的局部问题与论点继续保留，但尚未确认与上述问题的对应。\n\n'
             '关系入口：[[' + INDEX + ']]；既有积累独立查看[[' + EXISTING_INDEX + ']]。\n')
    index = boundary(route)
    index += '## 当前上层问题\n\n| 编号 | 研究问题 | 状态 | 论证关系 | 下层关联 |\n|---|---|---|---|---|\n'
    for q in questions:
        index += '| ' + q['id'] + ' | ' + link(INDEX, QUESTIONS + '#' + q['id'].lower(), q['title']) + ' | ' + q['status'] + ' | 待梳理 | 暂不建立 |\n'
    index += ('\n当前关系文件[[' + GRAPH + ']]仅包含上述问题节点，没有问题间连线，也没有通向下层节点的连线。\n\n'
              '## 既有积累与本轮范围\n\n[[' + EXISTING_INDEX + '|既有主题内部的子问题与论点]]及其[[' + EXISTING_GRAPH + '|局部关系数据]]单独保留；'
              '它们不是新研究问题的已确认支撑网络。旧内容未删除，旧状态未因方向修订自动升格或作废。\n\n'
              '后续先讨论问题之间的分工和论证逻辑，再逐项确认下层内容的适配关系。不得为补齐关系图自动连线。\n')
    nodes = [{'id': q['wiki_id'], 'kind': 'research-question', 'level': 'thesis', 'display_id': q['id'],
              'title': q['title'], 'status': q['status'], 'path': QUESTIONS + '#' + q['id'].lower(),
              'logic_role': None, 'associations': copy.deepcopy(q['associations'])} for q in questions]
    graph = {'generated_from': ROUTE + '#research_questions', 'scope': 'current-thesis-questions',
             'logic_status': route['logic_status'], 'association_status': route['association_status'],
             'source_document': route['source_document'], 'source_locator': route['source_locator'],
             'existing_graph': EXISTING_GRAPH, 'nodes': nodes, 'edges': []}
    return {QUESTIONS: note('thesis-research-questions', '当前研究问题', body),
            INDEX: note('research-argument-index', '研究论证索引', index),
            GRAPH: json.dumps(graph, ensure_ascii=False, indent=2) + '\n'}


def route_view(route):
    questions = validate(route)
    assert questions, 'route view requires current question declarations'
    graph = 'flowchart TB\n'
    for q in questions:
        label = (q['id'] + ' ' + q['title']).replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        graph += '  ' + q['wiki_id'] + '["' + label + '"]\n'
    body = ('**当前为研究问题骨架，不是已梳理完成的工作流程。** 问题间关系与下层映射暂空，'
            '不由排列顺序推定先后、支撑或因果。\n\n' + boundary(route))
    body += '```mermaid\n' + graph + '```\n\n'
    body += '问题内容与预期成果见[[' + QUESTIONS + ']]；当前论证关系见[[' + INDEX + ']]。\n\n'
    body += ('## 旧框架的身份\n\n2026-11-05至2026-11-06的大纲及详细框架图保留原内容，尚未按本轮问题重构。'
             '旧主题、试例及成果不自动挂到新问题上；现有合成试验不作为真实建筑学结论。'
             '旧研究路径及本轮修改前原件见[[' + route.get('previous_snapshot', 'archive/README.md') + '|方向切换前快照]]。\n')
    return note('dynamic-research-path', '研究路径工作图', body)
