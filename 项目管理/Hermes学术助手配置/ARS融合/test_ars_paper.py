"""Synthetic contract tests; not evidence of scientific correctness."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ars_paper', HERE / 'ars_paper.py')
ars = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ars)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.data = ars.load_mapping(HERE / '工作流映射.json')

    def test_inventory_covers_every_workflow(self):
        self.assertEqual(set(self.data['core_workflows']), {'deep-research', 'academic-paper',
                         'academic-paper-reviewer', 'academic-pipeline', 'sr-screener', 'experiment-agent'})

    def test_every_task_resolves_without_spawning(self):
        for task in self.data['tasks']:
            with self.subTest(task=task['id']):
                plan = ars.task_plan(self.data, task['id'])
                self.assertEqual(plan['execution_status'], 'prepared_not_dispatched')
                self.assertTrue(plan['role_prompt_required_at_dispatch'])

    def test_unknown_task_is_refused(self):
        with self.assertRaises(ValueError):
            ars.task_plan(self.data, 'invented-agent')

    def test_duplicate_task_is_refused(self):
        self.data['tasks'].append(copy.deepcopy(self.data['tasks'][0]))
        with self.assertRaises(ValueError):
            ars.validate_mapping(self.data)

    def test_upstream_mode_overrides_are_available(self):
        for name, mode in [('screening', 'ft-screen'), ('review', 'methodology-focus'),
                           ('write', 'abstract-only'), ('research', 'systematic-review')]:
            self.assertEqual(ars.task_plan(self.data, name, mode)['mode'], mode)

    def test_invalid_mode_override_is_refused(self):
        with self.assertRaises(ValueError):
            ars.task_plan(self.data, 'research', 'made-up-mode')

    def test_extension_cannot_claim_upstream_mode(self):
        with self.assertRaises(ValueError):
            ars.task_plan(self.data, 'graph-design', 'full')
        self.data['tasks'][3]['mode'] = 'full'
        with self.assertRaises(ValueError):
            ars.validate_mapping(self.data)

    def test_empty_goal_is_refused(self):
        with self.assertRaises(ValueError):
            ars.make_brief(self.data, 'review', '  ', [])

    def test_exact_goal_and_honest_status_are_preserved(self):
        goal = '  只讨论问题，不建立映射。\n保留原句。  '
        brief = ars.make_brief(self.data, 'rq-discuss', goal, [])
        self.assertEqual(brief['user_task_verbatim'], goal)
        self.assertTrue(brief['not_an_ars_material_passport'])
        self.assertNotIn('approved', brief)
        self.assertEqual(brief['plan']['execution_status'], 'prepared_not_dispatched')

    def test_source_receipts_deduplicate_and_do_not_claim_research_review(self):
        with patch.object(ars, 'bridge_read', return_value={'sha256': 'a' * 64, 'text': 'fixture'}):
            brief = ars.make_brief(self.data, 'review', 'Review fixture', ['a.md', 'a.md'])
        self.assertEqual(len(brief['source_refs']), 1)
        self.assertEqual(brief['source_refs'][0]['state'], 'bytes_read_not_research_verified')

    def test_unsafe_source_paths_are_refused_before_subprocess(self):
        for path in ('../secret', '/etc/passwd', '.env', '.obsidian/app.json', 'a/.hidden/file', 'a\\b'):
            with self.subTest(path=path), patch.object(ars.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    ars.bridge_read(path)
                run.assert_not_called()

    def test_bridge_hash_mismatch_is_refused(self):
        class Result:
            returncode = 0
            stdout = json.dumps({'ok': True, 'result': {'text': 'fixture', 'sha256': '0' * 64}})
        with patch.object(ars.subprocess, 'run', return_value=Result()):
            with self.assertRaises(RuntimeError):
                ars.bridge_read('fixture.md')

    def test_route_typo_is_refused(self):
        self.data['tasks'][0]['route'] = 'nonexistent'
        with self.assertRaises(ValueError):
            ars.validate_mapping(self.data)

    def test_required_gates_are_preserved(self):
        screening = ars.task_plan(self.data, 'screening')
        self.assertIn('explicit_screening_request', screening['gates'])
        graph = ars.task_plan(self.data, 'graph-design')
        self.assertIn('database_write_separately_authorized', graph['gates'])
        rq = ars.task_plan(self.data, 'rq-discuss')
        self.assertIn('no_automatic_lower_mapping', rq['gates'])

    def test_mode_change_does_not_reuse_task_default_gates(self):
        plan = ars.task_plan(self.data, 'experiment-plan', 'run')
        self.assertNotIn('plan_not_executed_result', plan['gates'])
        self.assertTrue(plan['mode_contract']['changed_from_task_default'])
        self.assertFalse(plan['dispatch_allowed_by_this_adapter'])
        self.assertIn('verify_mode_specific_inputs_and_user_authority', plan['gates'])

    def test_even_default_mode_requires_actual_contract_loading(self):
        plan = ars.task_plan(self.data, 'review')
        self.assertEqual(plan['mode_contract']['status'], 'not_loaded_by_adapter')
        self.assertFalse(plan['dispatch_allowed_by_this_adapter'])

    def test_unknown_task_kind_is_refused(self):
        self.data['tasks'][0]['kind'] = 'official_magic_agent'
        with self.assertRaises(ValueError):
            ars.validate_mapping(self.data)

    def test_removed_authority_policy_is_refused(self):
        del self.data['execution_policy']['paper_write']
        with self.assertRaises(ValueError):
            ars.validate_mapping(self.data)

    def test_removed_mandatory_gate_is_refused(self):
        task = next(t for t in self.data['tasks'] if t['id'] == 'screening')
        task['gates'] = ['arbitrary_nonempty_gate']
        with self.assertRaises(ValueError):
            ars.validate_mapping(self.data)

    def test_missing_source_lock_is_a_controlled_error(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            suite = Path(directory)
            (suite / 'manifest.json').write_text('{"source_repositories": []}')
            with patch.object(ars, 'SUITE', suite):
                with self.assertRaisesRegex(ValueError, 'source lock'):
                    ars.doctor(self.data)


if __name__ == '__main__':
    unittest.main()
