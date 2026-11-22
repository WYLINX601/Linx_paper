#!/usr/bin/env python3
"""Read-only ARS/Paper routing and handoff adapter; never dispatch or publish."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

import yaml
import ars_role_routes as role_routes

PAPER = Path('/Users/wangyuelin/Desktop/Obsidian/Paper')
PROFILE = Path('/Users/wangyuelin/.hermes/profiles/academic')
BRIDGE = PROFILE / 'bin/mac-paper'
SUITE = PROFILE / 'skills/academic-research-suite'
MAPPING = '项目管理/Hermes学术助手配置/ARS融合/工作流映射.json'


def bridge_read(relative: str) -> dict:
    p = PurePosixPath(relative)
    if (not p.parts or p.is_absolute() or '..' in p.parts or '\\' in relative
            or any(part.startswith('.') for part in p.parts)):
        raise ValueError('Use an explicit non-hidden Paper-relative path without traversal.')
    proc = subprocess.run([str(BRIDGE), 'read', relative], capture_output=True,
                          text=True, timeout=25)
    if proc.returncode:
        raise RuntimeError(f'Paper read failed for {relative}: {proc.stdout.strip() or proc.stderr.strip()}')
    response = json.loads(proc.stdout)
    if not response.get('ok'):
        raise RuntimeError(f'Paper read refused for {relative}')
    result = response['result']
    if hashlib.sha256(result['text'].encode('utf-8')).hexdigest() != result['sha256']:
        raise RuntimeError(f'Paper text/hash mismatch: {relative}')
    return result


def load_mapping(path: Path | None = None) -> dict:
    data = json.loads(path.read_text(encoding='utf-8') if path else bridge_read(MAPPING)['text'])
    validate_mapping(data)
    return data


def validate_mapping(data: dict) -> None:
    if data.get('schema') != 'ars-paper-integration/1':
        raise ValueError('Unsupported integration schema')
    core = data['core_workflows']
    required = {'deep-research', 'academic-paper', 'academic-paper-reviewer',
                'academic-pipeline', 'sr-screener', 'experiment-agent'}
    if set(core) != required:
        raise ValueError('Core/companion workflow inventory is incomplete')
    mandatory_policy = {
        'cross_model_default': 'off_requires_provider_and_content_consent',
        'database_default': 'no_implicit_write',
        'paper_write': 'mac-paper_current_sha_or_expect_missing',
        'research_decisions': 'user_owned_no_inferred_confirmation',
    }
    for key, value in mandatory_policy.items():
        if data.get('execution_policy', {}).get(key) != value:
            raise ValueError(f'Missing or changed authority policy: {key}')
    mandatory_gates = {
        'rq-discuss': {'user_research_decision', 'no_automatic_lower_mapping'},
        'graph-design': {'read_dual_baselines', 'database_write_separately_authorized'},
        'screening': {'explicit_screening_request', 'confirmed_protocol'},
        'analysis': {'explicit_execution_authorization', 'real_inputs_and_outputs'},
        'pipeline': {'explicit_end_to_end_request', 'stage_confirmation'},
    }
    ids = set()
    for task in data['tasks']:
        if task.get('kind') not in {'ars', 'companion', 'native_extension'}:
            raise ValueError('Unknown task kind')
        if task['id'] in ids:
            raise ValueError(f'Duplicate task: {task["id"]}')
        ids.add(task['id'])
        workflow, mode = task['workflow'], task['mode']
        if workflow is not None and workflow not in core:
            raise ValueError(f'Unknown workflow: {workflow}')
        if task['kind'] != 'native_extension' and (not workflow or mode not in core[workflow]['modes']):
            raise ValueError(f'Unsupported upstream mode: {task["id"]}')
        if task['kind'] == 'native_extension' and mode is not None:
            raise ValueError('Native extensions must not invent upstream modes')
        if task['route'] is not None and task['route'] not in data['delegation']['route_names']:
            raise ValueError(f'Unknown worker route: {task["id"]}')
        if not task['gates'] or not task['output_owner']:
            raise ValueError(f'Missing handoff boundary: {task["id"]}')
        if not mandatory_gates.get(task['id'], set()) <= set(task['gates']):
            raise ValueError(f'Required task gate removed: {task["id"]}')


def skill_index() -> dict[str, str]:
    found = {}
    for file in (PROFILE / 'skills').rglob('SKILL.md'):
        if any(part.startswith('.') or part == 'ars' for part in file.relative_to(PROFILE / 'skills').parts):
            continue
        text = file.read_text(encoding='utf-8')
        if text.startswith('---\n'):
            metadata = yaml.safe_load(text.split('---', 2)[1]) or {}
            if metadata.get('name'):
                found[metadata['name']] = str(file)
    return found


def task_plan(data: dict, task_id: str, mode: str | None = None) -> dict:
    task = next((task for task in data['tasks'] if task['id'] == task_id), None)
    if task is None:
        raise ValueError(f'Unknown task {task_id!r}; use list.')
    plan = dict(task)
    if mode is not None:
        if task['kind'] == 'native_extension' or mode not in data['core_workflows'][task['workflow']]['modes']:
            raise ValueError(f'Unsupported mode override: {mode}')
        plan['mode'] = mode
    changed_mode = mode is not None and mode != task['mode']
    # A mode list is discovery, not a complete executable contract. Never
    # carry task-default gates into an overridden mode as though they apply.
    plan['task_default_gates'] = list(task['gates'])
    if changed_mode:
        plan['gates'] = ['read_selected_workflow_mode_contract_before_dispatch',
                         'verify_mode_specific_inputs_and_user_authority']
    else:
        plan['gates'] = list(task['gates']) + ['read_selected_workflow_mode_contract_before_dispatch']
    plan['workflow_path'] = (str(SUITE / data['core_workflows'][task['workflow']]['path'])
                             if task['workflow'] else None)
    plan['framework_skill'] = data['framework_skill']
    plan['skills_are_selective'] = True
    plan['execution_status'] = 'prepared_not_dispatched'
    plan['dispatch_allowed_by_this_adapter'] = False
    plan['mode_contract'] = {'status': 'not_loaded_by_adapter',
                             'changed_from_task_default': changed_mode,
                             'requires': 'Read the selected workflow and role contracts; establish their inputs, prerequisites and real author decisions before dispatch.'}
    plan['role_prompt_required_at_dispatch'] = True
    plan['authority'] = data['authority']
    plan['execution_policy'] = data['execution_policy']
    plan['notice'] = 'This is routing metadata, not a running agent, source review, permission grant, or completed stage.'
    return plan


def make_brief(data: dict, task_id: str, goal: str, sources: list[str], mode: str | None = None) -> dict:
    if not goal.strip():
        raise ValueError('An explicit user task is required')
    plan = task_plan(data, task_id, mode)
    refs = []
    for relative in dict.fromkeys(sources):
        result = bridge_read(relative)
        refs.append({'path': relative, 'sha256': result['sha256'],
                     'state': 'bytes_read_not_research_verified'})
    return {'schema': 'ars-paper-handoff/1', 'user_task_verbatim': goal,
            'plan': plan, 'source_refs': refs, 'authorization': 'derive_from_actual_user_task_not_this_file',
            'required_result_fields': ['actual_read_scope', 'source_locators', 'findings',
                                       'inferences', 'candidate_changes', 'unresolved',
                                       'execution_evidence', 'independence_disclosure'],
            'publication': 'main_session_current_sha_guarded_write_only',
            'not_an_ars_material_passport': True}


def doctor(data: dict, registry_path: Path | None = None) -> dict:
    checks, failures = [], []
    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({'check': name, 'status': 'pass' if passed else 'fail', 'detail': detail})
        if not passed:
            failures.append(name)
    for name, workflow in data['core_workflows'].items():
        file = SUITE / workflow['path']
        available = file.is_file() and bool(file.read_bytes())
        check('workflow:' + name, available, str(file))
    manifest = json.loads((SUITE / 'manifest.json').read_text(encoding='utf-8'))
    locked = next((source for source in manifest.get('source_repositories', [])
                   if source.get('name') == 'academic-research-skills'), None)
    if locked is None:
        raise ValueError('Installed manifest lacks the ARS upstream source lock')
    check('suite_source_lock', locked['version'] == data['source_lock']['suite_version']
          and locked['commit'] == data['source_lock']['upstream_commit'], locked['version'])
    index = skill_index()
    for name in sorted({data['framework_skill']} | {s for task in data['tasks'] for s in task['skills']}):
        check('skill:' + name, name in index, index.get(name, 'not found'))
    # Read non-secret settings from the active profile; never print credential fields.
    config = yaml.safe_load((PROFILE / 'config.yaml').read_text(encoding='utf-8'))
    check('profile_scope', Path(os.environ.get('HERMES_HOME', str(PROFILE))).resolve() == PROFILE,
          'academic only')
    loaded = config.get('skills', {}).get('auto_load', [])
    check('framework_auto_load', data['framework_skill'] in loaded and 'academic-workspace' in loaded,
          ', '.join(loaded))
    section = config.get('delegation', {})
    check('delegation_backend', section.get('backend') == data['delegation']['backend'], str(section.get('backend')))
    try:
        options = role_routes.model_options(section)
        check('official_model_routes_parser', True, 'Installed official parser; no skipped or normalized-duplicate entries')
    except ValueError as exc:
        options = {}
        check('official_model_routes_parser', False, str(exc))
    expected = data['delegation']
    for name in expected['route_names']:
        route = options.get(name, {})
        check('route:' + name,
              bool(route.get('model') and route.get('description')
                   and (route.get('provider') or route.get('base_url'))
                   and route.get('fallback_providers') == []),
              'Explicit model/provider or endpoint, description and no provider fallback; per-route model choice is owned by Hermes, not Paper')
    default = section.get('backends', {}).get('model_map', {}).get('default')
    check('explicit_default_model_route', isinstance(default, str) and default.strip() in options,
          'Valid named default is configured in Hermes; its choice is user-managed, not fixed by Paper')
    # This installed CLI accepts cli/api_server; legacy local/acp config
    # blocks are not valid --platform targets and must not be treated as tested.
    for platform in ('cli', 'api_server'):
        check('delegation_toolset:' + platform,
              'delegation' in config.get('platform_toolsets', {}).get(platform, []),
              'effective on new sessions; live child execution is a separate test')
    registry = role_routes.load_registry(registry_path)
    role_counts = role_routes.validate_registry(registry, options)
    check('role_registry_full_coverage', role_counts['unmapped'] == 0, json.dumps(role_counts))
    check('mcp_inheritance_compatibility_setting', section.get('inherit_mcp_toolsets') is False,
          'This setting alone is not a per-task tool boundary: the installed native API inherits parent tools; restrict the parent session when required')
    return {'status': 'pass' if not failures else 'fail', 'task_count': len(data['tasks']),
            'workflow_count': len(data['core_workflows']), 'role_counts': role_counts, 'checks': checks,
            'failure_count': len(failures), 'source_truth': 'Paper mapping + installed files/config',
            'not_tested_by_doctor': ['MCP service connectivity', 'scientific validity',
                                   'full ARS pipeline', 'independent multi-review accuracy',
                                   'whole-vault health', 'GUI acceptance', 'LLM child execution']}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping-file', type=Path, help='Explicit offline candidate; normal runs read Paper through mac-paper.')
    parser.add_argument('--role-registry-file', type=Path, help='Explicit offline role-registry candidate.')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    route = sub.add_parser('route')
    route.add_argument('task')
    route.add_argument('--mode')
    brief = sub.add_parser('brief')
    brief.add_argument('task')
    brief.add_argument('--goal', required=True)
    brief.add_argument('--source', action='append', default=[])
    brief.add_argument('--mode')
    sub.add_parser('doctor')
    roles = sub.add_parser('roles')
    roles.add_argument('--workflow')
    roles.add_argument('--all-bindings', action='store_true', help='Also list screening seats and protocol-call bindings; these are not extra upstream agent files.')
    role = sub.add_parser('role')
    role.add_argument('role_id')
    role_brief = sub.add_parser('role-brief')
    role_brief.add_argument('role_id')
    role_brief.add_argument('--goal', required=True)
    role_brief.add_argument('--source', action='append', default=[])
    role_brief.add_argument('--readable-context', action='store_true', help='Emit a multiline context object for tool-safe reading; serialize it to the native context string at dispatch.')
    role_check = sub.add_parser('role-check', help='Explicitly validate a prepared official Model routes task; does not intercept dispatch or authorize work.')
    role_check.add_argument('task_file', type=Path, help='JSON object containing goal/context/option, or a role-brief with native_task.')
    args = parser.parse_args()
    try:
        data = load_mapping(args.mapping_file)
        if args.command == 'list':
            result = [{'id': task['id'], 'title': task['title'], 'kind': task['kind']}
                      for task in data['tasks']]
        elif args.command == 'route':
            result = task_plan(data, args.task, args.mode)
        elif args.command == 'brief':
            result = make_brief(data, args.task, args.goal, args.source, args.mode)
        elif args.command in ('roles', 'role', 'role-brief'):
            registry = role_routes.load_registry(args.role_registry_file)
            role_routes.validate_registry(registry)
            if args.command == 'roles':
                entries = registry['roles'] + (registry['instances'] + registry['contract_calls'] if args.all_bindings else [])
                result = [role_routes.role_plan(registry,row['id']) for row in entries]
                if args.workflow:
                    result = [row for row in result if row['workflow']==args.workflow]
            elif args.command == 'role':
                result = role_routes.role_plan(registry,args.role_id)
            else:
                refs = []
                for source in dict.fromkeys(args.source):
                    current = bridge_read(source)
                    refs.append({'path':source,'sha256':current['sha256'],
                                 'state':'bytes_read_not_research_verified'})
                result = role_routes.role_brief(registry,args.role_id,args.goal,refs)
                if args.readable_context:
                    result = role_routes.role_transport(result)
        elif args.command == 'role-check':
            registry = role_routes.load_registry(args.role_registry_file)
            task = json.loads(args.task_file.read_text(encoding='utf-8'))
            if not isinstance(task, dict):
                raise ValueError('Task file must contain a JSON object')
            task = task.get('native_task', task)
            config = yaml.safe_load((PROFILE / 'config.yaml').read_text(encoding='utf-8'))
            result = role_routes.validate_native_task(registry, task, config.get('delegation', {}))
        else:
            result = doctor(data,args.role_registry_file)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if isinstance(result, dict) and result.get('status') == 'fail' else 0
    except (KeyError, ValueError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
