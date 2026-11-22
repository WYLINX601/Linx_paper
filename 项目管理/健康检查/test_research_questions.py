"""Tests use explicit artificial question fixtures, never empirical research data."""
import copy
import json
import unittest
import research_questions as rq


def fixture():
    questions = [dict(id='RQ' + str(i), wiki_id='test-question-' + str(i), title='仅测试问题' + str(i) + '？',
                      content='仅用于生成器测试。', expected_outputs=['待形成结果'], status='open',
                      logic_role=None, source_locator='测试文档第六节',
                      associations={key: [] for key in rq.ASSOCIATIONS}) for i in (1, 2)]
    return dict(schema_version=1, view_mode=rq.MODE, logic_status='pending-discussion',
                association_status='deferred', source_document='测试原件.docx', source_note='测试来源.md',
                source_locator='测试文档第六节', previous_snapshot='archive/测试/README.md',
                research_questions=questions,
                nodes=[dict(id=q['wiki_id'], question_id=q['id']) for q in questions], edges=[])


class ThesisQuestionTests(unittest.TestCase):
    def setUp(self):
        self.route = fixture()

    def test_generation_is_read_only_and_repeatable(self):
        before = copy.deepcopy(self.route)
        self.assertEqual(rq.generate(self.route), rq.generate(self.route))
        rq.resolve_route(self.route)
        self.assertEqual(before, self.route)

    def test_graph_has_only_current_questions_and_no_edges(self):
        graph = json.loads(rq.generate(self.route)[rq.GRAPH])
        self.assertEqual([q['id'] for q in self.route['nodes']], [n['id'] for n in graph['nodes']])
        self.assertEqual(graph['edges'], [])
        self.assertTrue(all(n['level'] == 'thesis' for n in graph['nodes']))
        self.assertTrue(all(not value for n in graph['nodes'] for value in n['associations'].values()))

    def test_every_lower_association_is_rejected_while_deferred(self):
        for key in rq.ASSOCIATIONS:
            with self.subTest(key=key):
                route = copy.deepcopy(self.route)
                route['research_questions'][0]['associations'][key] = ['旧节点']
                with self.assertRaises(AssertionError):
                    rq.generate(route)

    def test_question_edges_are_not_inferred_or_accepted_as_unreviewed(self):
        self.route['edges'] = [dict(from_='test-question-1', to='test-question-2', kind='dependency')]
        with self.assertRaises(AssertionError):
            rq.validate(self.route)

    def test_logic_roles_are_not_preassigned(self):
        self.route['research_questions'][0]['logic_role'] = '前提'
        with self.assertRaises(AssertionError):
            rq.validate(self.route)

    def test_duplicate_question_and_stable_ids_are_rejected(self):
        for key in ('id', 'wiki_id'):
            with self.subTest(key=key):
                route = copy.deepcopy(self.route)
                route['research_questions'][1][key] = route['research_questions'][0][key]
                with self.assertRaises(AssertionError):
                    rq.validate(route)

    def test_missing_route_question_is_rejected(self):
        self.route['nodes'].pop()
        with self.assertRaises(AssertionError):
            rq.validate(self.route)

    def test_duplicate_inline_question_text_is_rejected(self):
        self.route['nodes'][0]['title'] = '第二份手工题名'
        with self.assertRaises(AssertionError):
            rq.validate(self.route)

    def test_single_source_title_change_propagates_to_all_views(self):
        self.route['research_questions'][0]['title'] = '只在声明中修改的新题名？'
        out = rq.generate(self.route)
        for path in (rq.QUESTIONS, rq.INDEX, rq.GRAPH):
            self.assertIn('只在声明中修改的新题名？', out[path])
        self.assertIn('只在声明中修改的新题名？', rq.route_view(self.route))
        self.assertIn('只在声明中修改的新题名？', rq.resolve_route(self.route)['nodes'][0]['title'])

    def test_route_does_not_mutate_declared_refs_or_add_topics(self):
        resolved = rq.resolve_route(self.route)
        self.assertNotIn('title', self.route['nodes'][0])
        self.assertTrue(all(n['topics'] == [] for n in resolved['nodes']))
        self.assertEqual(resolved['edges'], [])

    def test_table_links_do_not_add_columns(self):
        rows = [line for line in rq.generate(self.route)[rq.INDEX].splitlines() if line.startswith('|')]
        self.assertTrue(rows)
        self.assertTrue(all(line.count('|') == 6 for line in rows))

    def test_old_route_without_question_declarations_remains_supported(self):
        old = dict(schema_version=1, nodes=[dict(id='old', title='旧环节', topics=[], status='旧状态')], edges=[])
        self.assertEqual(rq.resolve_route(old), old)

    def test_empty_question_skeleton_is_rejected(self):
        self.route['research_questions'] = []
        with self.assertRaises(AssertionError):
            rq.resolve_route(self.route)


if __name__ == '__main__':
    unittest.main(verbosity=2)
