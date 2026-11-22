"""Synthetic and source-bound contract tests, not scientific-performance tests."""
import ast
import copy
import json
import subprocess
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, '/Users/wangyuelin/.hermes/hermes-agent')
import ars_role_routes as role_module
import ars_role_provider as provider
from functools import partial
from types import SimpleNamespace

# Retain legacy backend regression coverage; active official routes have their
# own tests in test_model_routes.py. Do not monkeypatch the production module.
roles = SimpleNamespace(**{**vars(role_module), 'role_brief':partial(role_module.role_brief, backend='ars_roles')})


class RoleTests(unittest.TestCase):
    def setUp(self):
        self.data = roles.load_registry(HERE/'角色路由.json')
        mapping = json.loads((HERE/'工作流映射.json').read_text())
        self.options = {name: {'name':name, 'provider':'openai-codex', 'model':'gpt-6.1-sol',
                              'reasoning_effort':'medium','service_tier':'normal'}
                        for name in mapping['delegation']['route_names']}
        self.config = {'inherit_mcp_toolsets':False, 'backends':{'model_map':{'options':list(self.options.values())}}}
        self.backend = provider.ArsRoleProvider()

    def route(self, task):
        with patch.object(provider,'load_registry',return_value=self.data):
            return self.backend.route_task(task,self.config)

    def test_exact_source_inventory_and_aliases(self):
        count = roles.validate_registry(self.data,self.options)
        self.assertEqual(count,{'canonical_roles':45,'subagents':34,'main_roles':11,'aliases':4,'instances':4,'contract_calls':4,'unmapped':0})

    def test_every_role_resolves_and_has_one_owner(self):
        for row in self.data['roles']:
            with self.subTest(role=row['id']):
                plan=roles.role_plan(self.data,row['id'])
                self.assertEqual(plan['execution'],row['execution'])
                self.assertEqual(plan['execution_status'],'configured_not_executed')

    def test_all_subagent_bindings_resolve_to_explicit_models(self):
        count=0
        for row in self.data['roles']:
            if row['execution']!='subagent':continue
            with self.subTest(role=row['id']):
                payload=roles.role_brief(self.data,row['id'],'Configuration-only fixture')['native_task']
                actual=self.route(payload)
                self.assertEqual(actual['model'],'gpt-6.1-sol')
                self.assertEqual(actual['reasoning_effort'],'medium')
                self.assertEqual(actual['label'],row['id'])
                self.assertEqual(actual['fallback_providers'],[])
                count+=1
        self.assertEqual(count,34)

    def test_main_roles_are_not_delegated(self):
        for row in self.data['roles']:
            if row['execution']=='main':
                with self.subTest(role=row['id']),self.assertRaises(ValueError):
                    roles.role_brief(self.data,row['id'],'fixture')

    def test_native_enum_contains_only_subagents_and_seats(self):
        with patch.object(provider,'load_registry',return_value=self.data):
            declared=self.backend.task_parameters(self.config)
        self.assertEqual(len(declared['ars_role']['enum']),42)
        for row in self.data['roles']:
            self.assertEqual(row['id'] in declared['ars_role']['enum'],row['execution']=='subagent')

    def test_duplicate_role_is_refused(self):
        self.data['roles'].append(copy.deepcopy(self.data['roles'][0]))
        with self.assertRaises(ValueError):roles.validate_registry(self.data,self.options)

    def test_omitted_role_is_refused(self):
        self.data['roles'].pop()
        with self.assertRaises(ValueError):roles.validate_registry(self.data,self.options)

    def test_stale_prompt_hash_is_refused(self):
        self.data['roles'][0]['prompt_sha256']='0'*64
        with self.assertRaises(ValueError):roles.validate_registry(self.data,self.options)

    def test_missing_model_route_is_refused(self):
        del self.options['literature']
        with self.assertRaises(ValueError):roles.validate_registry(self.data,self.options)

    def test_empty_selection_has_no_parent_fallback(self):
        with self.assertRaises(ValueError):self.route({'goal':'fixture'})

    def test_conflicting_selectors_are_refused(self):
        with self.assertRaises(ValueError):self.route({'ars_role':self.data['roles'][0]['id'],'option':'literature'})

    def test_native_extension_requires_explicit_option(self):
        actual=self.route({'goal':'Native extension fixture','option':'graph_modeling'})
        self.assertEqual(actual['label'],'native:graph_modeling')

    def test_role_without_bound_context_is_refused(self):
        with self.assertRaises(ValueError):self.route({'ars_role':self.data['roles'][0]['id'],'goal':'fixture'})

    def test_changed_context_bytes_are_refused(self):
        task=roles.role_brief(self.data,self.data['roles'][0]['id'],'fixture')['native_task']
        context=json.loads(task['context']);context['prompt_absolute_path']+='not-in-source';task['context']=json.dumps(context)
        with self.assertRaises(ValueError):self.route(task)

    def test_removed_skill_binding_is_refused(self):
        task=roles.role_brief(self.data,self.data['roles'][0]['id'],'fixture')['native_task']
        context=json.loads(task['context']);context['required_skills']=[];task['context']=json.dumps(context)
        with self.assertRaises(ValueError):self.route(task)

    def test_required_protocol_cannot_be_omitted(self):
        task=roles.role_brief(self.data,'academic-paper-reviewer/eic_agent','fixture')['native_task']
        context=json.loads(task['context']);context['protocol_refs']=[];task['context']=json.dumps(context)
        with self.assertRaises(ValueError):self.route(task)

    def test_registry_drift_refuses_old_brief(self):
        task=roles.role_brief(self.data,self.data['roles'][0]['id'],'fixture')['native_task']
        self.data['_registry_sha256']='0'*64
        with self.assertRaises(ValueError):self.route(task)

    def test_mcp_auto_inheritance_is_refused(self):
        task=roles.role_brief(self.data,self.data['roles'][0]['id'],'fixture')['native_task']
        self.config['inherit_mcp_toolsets']=True
        with self.assertRaises(ValueError):self.route(task)

    def test_screening_seats_have_distinct_ids(self):
        seats=[]
        for instance in self.data['instances']:
            brief=roles.role_brief(self.data,instance['id'],'Screening fixture only')
            self.assertEqual(brief['parent_toolset_scope_for_strict_subset'],['delegation','ars_readonly'])
            seats.append(self.route(brief['native_task'])['label'])
        self.assertEqual(len(set(seats)),4)

    def test_plugin_aliases_are_not_new_role_counts(self):
        for alias in self.data['aliases']:
            self.assertEqual(roles.resolve_role(self.data,alias['prompt_file'])['id'],alias['canonical_role'])

    def test_role_source_path_escape_is_refused(self):
        with self.assertRaises(ValueError):roles.source_path('../config.yaml')

    def test_readonly_toolset_cannot_be_widened(self):
        self.data['tool_profiles']['readonly']['tools'].append('write_file')
        with self.assertRaises(ValueError):roles.validate_registry(self.data,self.options)

    def test_unique_toolset_names_prevent_overwrite(self):
        self.data['tool_profiles']['candidate']['toolset']='ars_readonly'
        with self.assertRaises(ValueError):roles.validate_registry(self.data,self.options)

    def test_exact_goal_preserved(self):
        goal='  配置探针。\n不要开展科研。 '
        task=roles.role_brief(self.data,self.data['roles'][0]['id'],goal)['native_task']
        self.assertEqual(task['goal'],goal)

    def test_registered_readonly_subset_uses_real_core_resolver(self):
        class Context:
            def register_delegation_provider(self, value):self.provider=value
        context=Context()
        with patch.object(provider,'load_registry',return_value=self.data):provider.register(context)
        from toolsets import resolve_toolset
        self.assertEqual(set(resolve_toolset('ars_readonly',include_registry=False)),{'read_file','search_files'})
        self.assertEqual(context.provider.name,'ars_roles')

    def test_missing_owning_workflow_is_refused(self):
        self.data['roles'][0]['protocols'] = []
        with self.assertRaisesRegex(ValueError, 'owning workflow'):
            roles.validate_registry(self.data, self.options)

    def test_required_skill_has_bound_readable_source(self):
        brief = roles.role_brief(self.data, 'academic-paper/peer_reviewer_agent', 'Configuration fixture')
        context = json.loads(brief['native_task']['context'])
        self.assertEqual([ref['name'] for ref in context['skill_refs']], ['nature-reviewer'])
        for reference in context['skill_refs']:
            self.assertEqual(roles.digest(Path(reference['absolute_path']).read_bytes()), reference['sha256'])

    def test_omitted_skill_source_ref_is_refused(self):
        task = roles.role_brief(self.data, 'academic-paper/peer_reviewer_agent', 'fixture')['native_task']
        context = json.loads(task['context'])
        context['skill_refs'] = []
        task['context'] = json.dumps(context)
        with self.assertRaises(ValueError):
            self.route(task)

    def test_instances_cannot_override_tool_permissions(self):
        self.data['instances'][0]['tool_profile'] = 'compute'
        with self.assertRaisesRegex(ValueError, 'Instance may not override'):
            roles.validate_registry(self.data, self.options)

    def test_role_owner_must_match_source(self):
        self.data['roles'][0]['workflow'] = 'academic-paper'
        with self.assertRaisesRegex(ValueError, 'owner disagree'):
            roles.validate_registry(self.data, self.options)

    def test_legacy_role_brief_uses_only_legacy_backend_fields(self):
        task = roles.role_brief(self.data, self.data['roles'][0]['id'], 'fixture')['native_task']
        self.assertEqual(set(task), {'goal', 'context', 'ars_role'})
        # Inspect the installed primary source without importing unrelated CLI/terminal dependencies.
        tree = ast.parse(Path('/Users/wangyuelin/.hermes/hermes-agent/tools/delegate_tool.py').read_text())
        schema = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == 'DELEGATE_TASK_SCHEMA' for target in node.targets))
        for field in ('parameters', 'properties', 'tasks', 'items', 'properties'):
            schema = next(value for key, value in zip(schema.keys, schema.values)
                          if isinstance(key, ast.Constant) and key.value == field)
        allowed = {key.value for key in schema.keys}
        with patch.object(provider, 'load_registry', return_value=self.data):
            allowed.update(self.backend.task_parameters(self.config))
        self.assertLessEqual(set(task), allowed)

    def test_all_four_tool_profiles_resolve_to_declared_tools(self):
        class Context:
            def register_delegation_provider(self, value):self.provider=value
        with patch.object(provider,'load_registry',return_value=self.data):provider.register(Context())
        from toolsets import resolve_toolset
        for name, profile in self.data['tool_profiles'].items():
            with self.subTest(profile=name):
                self.assertEqual(set(resolve_toolset(profile['toolset'], include_registry=False)), set(profile['tools']))

    def test_re_review_calls_use_protocol_not_first_round_agent(self):
        for row in self.data['contract_calls']:
            with self.subTest(call=row['id']):
                task = roles.role_brief(self.data, row['id'], 'Configuration fixture')['native_task']
                context = json.loads(task['context'])
                self.assertTrue(context['prompt_file'].endswith('re_review_mode_protocol.md'))
                self.assertEqual(context['phase'], row['phase'])
                self.assertEqual(self.route(task)['label'], row['id'])

    def test_missing_protocol_call_is_refused(self):
        self.data['contract_calls'].pop()
        with self.assertRaisesRegex(ValueError, 'protocol-call inventory'):
            roles.validate_registry(self.data, self.options)

    def test_joint_workflow_and_id_reassignment_is_refused(self):
        row = self.data['roles'][0]
        row['workflow'] = 'academic-paper'
        row['id'] = row['workflow'] + '/' + Path(row['prompt_file']).stem
        row['protocols'].append('ars/academic-paper/WORKFLOW.md')
        with self.assertRaisesRegex(ValueError, 'owner disagree'):
            roles.validate_registry(self.data, self.options)

    def test_execution_and_output_contract_fields_cannot_be_removed(self):
        task = roles.role_brief(self.data, self.data['roles'][0]['id'], 'fixture')['native_task']
        for field in ('execution_instructions', 'authorization', 'tool_profile_enforcement',
                      'tool_scope_note', 'output_contract'):
            with self.subTest(field=field):
                changed = dict(task)
                context = json.loads(task['context'])
                del context[field]
                changed['context'] = json.dumps(context)
                with self.assertRaises(ValueError):
                    self.route(changed)

    def test_registered_provider_refuses_registry_epoch_drift(self):
        self.backend = provider.ArsRoleProvider(self.data['_registry_sha256'])
        self.data['_registry_sha256'] = '0' * 64
        task = roles.role_brief(self.data, self.data['roles'][0]['id'], 'fixture')['native_task']
        with self.assertRaisesRegex(ValueError, 'fresh session'):
            self.route(task)

    def test_unknown_role_is_refused_without_model_fallback(self):
        with self.assertRaisesRegex(ValueError, 'Unknown role'):
            self.route({'ars_role':'unregistered/no_such_role', 'context':'{}'})

    def test_missing_screening_seat_is_refused(self):
        self.data['instances'].pop()
        with self.assertRaisesRegex(ValueError, 'seat inventory'):
            roles.validate_registry(self.data, self.options)

    def test_registry_timeout_is_a_structured_route_refusal(self):
        with patch.object(provider, 'load_registry', side_effect=subprocess.TimeoutExpired('mac-paper', 25)):
            with self.assertRaises(provider.DelegationRouteError):
                self.backend.route_task({'ars_role':self.data['roles'][0]['id']}, self.config)

    def test_readable_transport_roundtrip_keeps_native_binding(self):
        brief = roles.role_brief(self.data, self.data['roles'][0]['id'], ' fixture\n原样保留 ')
        transport = roles.role_transport(brief)
        self.assertNotIn('native_task', transport)
        task = dict(transport['native_task_without_context'])
        task['context'] = json.dumps(transport['context_object'], ensure_ascii=False)
        self.assertEqual(task, brief['native_task'])
        self.assertEqual(self.route(task)['label'], brief['role_id'])

    def test_output_contract_is_delivered(self):
        for row in self.data['roles'] + self.data['contract_calls']:
            if row['execution'] != 'subagent':
                continue
            with self.subTest(role=row['id']):
                context = json.loads(roles.role_brief(self.data, row['id'], 'fixture')['native_task']['context'])
                self.assertEqual(context['output_contract'], row.get('output_contract', roles.DEFAULT_OUTPUT_CONTRACT))


if __name__=='__main__':unittest.main()
