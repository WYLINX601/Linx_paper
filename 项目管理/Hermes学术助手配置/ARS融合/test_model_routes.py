"""Official model_map integration and explicit ARS preflight; no model/API calls."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, '/Users/wangyuelin/.hermes/hermes-agent')
import ars_role_routes as roles
import ars_paper as adapter

PLUGIN = Path('/Users/wangyuelin/.hermes/profiles/academic/plugins/advanced-delegation/model_map.py')
spec = importlib.util.spec_from_file_location('official_model_routes_under_test', PLUGIN)
official = importlib.util.module_from_spec(spec)
spec.loader.exec_module(official)


class ModelRoutesTests(unittest.TestCase):
    def setUp(self):
        self.data = roles.load_registry(HERE / '角色路由.json')
        mapping = json.loads((HERE / '工作流映射.json').read_text())
        self.options = [{'name':name, 'description':'Configuration-only fixture',
                         'provider':'openai-codex', 'model':'gpt-6.1-sol',
                         'reasoning_effort':'medium', 'service_tier':'normal',
                         'fallback_providers':[]}
                        for name in mapping['delegation']['route_names']]
        self.config = {'backend':'model_map', 'backends':{'model_map':{
            'options':self.options, 'default':'evidence_review'}}}
        self.backend = official.ModelMapDelegationProvider()

    def task(self, identifier='deep-research/bibliography_agent'):
        return roles.role_brief(self.data, identifier, 'Configuration fixture')['native_task']

    def test_all_42_role_seat_and_protocol_bindings_use_official_options(self):
        entries = self.data['roles'] + self.data['instances'] + self.data['contract_calls']
        count = 0
        for row in entries:
            resolved = roles.resolve_role(self.data, row['id'])
            if resolved['execution'] != 'subagent':
                continue
            with self.subTest(role=row['id']):
                task = self.task(row['id'])
                self.assertEqual(set(task), {'goal', 'context', 'option'})
                self.assertEqual(roles.validate_native_task(self.data, task, self.config)['status'], 'pass')
                self.assertEqual(self.backend.route_task(task, self.config)['label'], resolved['route'])
                self.assertEqual(json.loads(task['context'])['role_id'], row['id'])
                count += 1
        self.assertEqual(count, 42)

    def test_official_schema_has_option_not_ars_role(self):
        fields = self.backend.task_parameters(self.config)
        self.assertEqual(set(fields), {'option'})
        self.assertEqual(set(fields['option']['enum']), {row['name'] for row in self.options})

    def test_standalone_interpreter_loads_official_parser_without_test_path_injection(self):
        program = ('import sys,json; sys.path.insert(0,'+repr(str(HERE))+'); '
                   'import ars_role_routes as r; '
                   'print(json.dumps(sorted(r.model_options('+repr(self.config)+'))))')
        result = subprocess.run([sys.executable, '-I', '-c', program], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), sorted(row['name'] for row in self.options))

    def test_model_choice_is_per_route_not_hardcoded_by_paper(self):
        # Synthetic fixture only, not a provider setup, consent or live invocation.
        self.options[0].update(provider='fixture-provider', model='fixture-model')
        task = self.task()
        self.assertEqual(roles.validate_native_task(self.data, task, self.config)['status'], 'pass')
        self.assertEqual(self.backend.route_task(task, self.config)['model'], 'fixture-model')
        other = self.backend.route_task({'option':'evidence_review'}, self.config)
        self.assertEqual(other['model'], 'gpt-6.1-sol')

    def test_wrong_option_fails_explicit_preflight(self):
        task = self.task()
        task['option'] = 'academic_write'
        with self.assertRaisesRegex(ValueError, 'does not match'):
            roles.validate_native_task(self.data, task, self.config)

    def test_legacy_selector_is_not_an_official_task(self):
        task = self.task()
        task['ars_role'] = task.pop('option')
        with self.assertRaisesRegex(ValueError, 'exactly'):
            roles.validate_native_task(self.data, task, self.config)

    def test_missing_context_contract_is_refused_by_preflight(self):
        task = self.task()
        context = json.loads(task['context'])
        del context['output_contract']
        task['context'] = json.dumps(context)
        with self.assertRaises(ValueError):
            roles.validate_native_task(self.data, task, self.config)

    def test_preflight_is_not_automatically_called_by_official_backend(self):
        task = self.task()
        task['context'] = '{}'
        with self.assertRaises(ValueError):
            roles.validate_native_task(self.data, task, self.config)
        self.assertEqual(self.backend.route_task(task, self.config)['label'], 'literature')

    def test_provider_fallback_is_explicitly_disabled(self):
        task = self.task()
        self.assertEqual(self.backend.route_task(task, self.config)['fallback_providers'], [])
        self.options[0].pop('fallback_providers')
        with self.assertRaisesRegex(ValueError, 'fallback_providers'):
            roles.validate_native_task(self.data, task, self.config)

    def test_duplicate_routes_and_wrong_backend_are_refused_by_preflight(self):
        self.options.append(copy.deepcopy(self.options[0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            roles.validate_native_task(self.data, self.task(), self.config)
        self.config['backend'] = 'ars_roles'
        with self.assertRaisesRegex(ValueError, 'fresh'):
            roles.validate_native_task(self.data, self.task(), self.config)

    def test_unselected_task_has_explicit_named_default(self):
        route = self.backend.route_task({'goal':'Configuration fixture'}, self.config)
        self.assertEqual(route['label'], 'evidence_review')
        self.assertEqual(route['model'], 'gpt-6.1-sol')
        self.assertEqual(route['fallback_providers'], [])

    def test_transport_preserves_official_payload(self):
        brief = roles.role_brief(self.data, 'sr-screener/reviewer_a', 'fixture')
        transport = roles.role_transport(brief)
        task = dict(transport['native_task_without_context'])
        task['context'] = json.dumps(transport['context_object'], ensure_ascii=False)
        self.assertEqual(task, brief['native_task'])
        self.assertEqual(brief['binding_enforcement'], 'preflight_only_not_enforced_by_model_map')

    def test_official_invalid_route_fields_fail_preflight(self):
        for key,value in [('description', ''), ('description', '  \t'), ('description', None),
                          ('description', 123), ('model', 123), ('model', '   '),
                          ('provider', 123), ('name', None)]:
            with self.subTest(field=key, value=value):
                config = copy.deepcopy(self.config)
                config['backends']['model_map']['options'][0][key] = value
                with self.assertRaisesRegex(ValueError, 'Official model parser skipped'):
                    roles.validate_native_task(self.data, self.task(), config)

    def test_official_missing_description_fails_preflight(self):
        self.options[0].pop('description')
        with self.assertRaisesRegex(ValueError, 'Official model parser skipped'):
            roles.validate_native_task(self.data, self.task(), self.config)

    def test_normalized_duplicate_route_names_fail_preflight(self):
        duplicate = copy.deepcopy(self.options[0])
        duplicate['name'] = '  literature  '
        self.options.append(duplicate)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            roles.validate_native_task(self.data, self.task(), self.config)

    def test_official_name_and_route_string_normalization_are_shared(self):
        self.options[0]['name'] = ' literature '
        self.options[0]['model'] = ' gpt-6.1-sol '
        self.assertEqual(roles.model_options(self.config)['literature']['model'], 'gpt-6.1-sol')
        self.assertEqual(roles.validate_native_task(self.data, self.task(), self.config)['status'], 'pass')

    def test_payload_matches_installed_core_and_official_provider_schema(self):
        tree = ast.parse(Path('/Users/wangyuelin/.hermes/hermes-agent/tools/delegate_tool.py').read_text())
        schema = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == 'DELEGATE_TASK_SCHEMA' for target in node.targets))
        for field in ('parameters', 'properties', 'tasks', 'items', 'properties'):
            schema = next(value for key,value in zip(schema.keys,schema.values)
                          if isinstance(key,ast.Constant) and key.value == field)
        allowed = {key.value for key in schema.keys} | set(self.backend.task_parameters(self.config))
        self.assertLessEqual(set(self.task()), allowed)
        self.assertNotIn('ars_role', allowed)

    def test_doctor_accepts_route_specific_models_and_detects_bad_default(self):
        self.options[0].update(provider='fixture-provider', model='fixture-model')
        config = {'delegation':self.config,
                  'skills':{'auto_load':['academic-workspace', 'academic-research-suite']},
                  'platform_toolsets':{'cli':['delegation'], 'api_server':['delegation']}}
        self.config['inherit_mcp_toolsets'] = False
        data = adapter.load_mapping(HERE / '工作流映射.json')
        original = adapter.yaml.safe_load
        def fixture_config(raw):
            if isinstance(raw, str) and 'delegation:' in raw and 'mcp_servers:' in raw:
                return config
            return original(raw)
        with patch.object(adapter.yaml, 'safe_load', side_effect=fixture_config):
            report = adapter.doctor(data, HERE / '角色路由.json')
            self.assertEqual(report['status'], 'pass', report)
            self.config['backends']['model_map']['default'] = 'missing'
            report = adapter.doctor(data, HERE / '角色路由.json')
            self.assertIn('explicit_default_model_route', [row['check'] for row in report['checks'] if row['status']=='fail'])


if __name__ == '__main__':
    unittest.main()
