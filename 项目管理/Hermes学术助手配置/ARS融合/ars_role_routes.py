"""Source-locked role contracts and native delegate payloads; no model calls."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import yaml

PROFILE = Path('/Users/wangyuelin/.hermes/profiles/academic')
SUITE = PROFILE / 'skills/academic-research-suite'
REGISTRY = '项目管理/Hermes学术助手配置/ARS融合/角色路由.json'
BRIDGE = PROFILE / 'bin/mac-paper'
ROLE_DIRS = ('deep-research', 'academic-paper', 'academic-paper-reviewer',
             'academic-pipeline', 'sr-screener', 'experiment-agent', 'shared')
EXECUTION_INSTRUCTIONS = ('Before substantive role work, read the exact prompt_absolute_path and the named workflow/role protocols. '
                          'Load required skills via skill_view if available; otherwise read their exact bound skill_refs absolute paths with read_file. '
                          'Skill text does not grant tools. Do not substitute another role, skip required inputs, or infer author confirmation. '
                          'Follow the original role output protocol; separately disclose the output_contract metadata to the main session without changing a required wire format.')
TOOL_SCOPE_NOTE = ('The installed model-facing delegate_task API has no role/toolsets task parameters; children inherit the parent tool surface. '
                   'The declared tool profile is guidance only in an unrestricted parent session. '
                   'For a strict tool subset, start a bounded parent CLI session with only delegation plus the declared ars_* toolset. '
                   'File paths and write destinations remain prompt-level constraints, not an OS sandbox.')
DEFAULT_OUTPUT_CONTRACT = {'authority':'original_role_prompt', 'publication':'main_session_only',
                           'must_disclose':['actual_read_scope','source_locators','unresolved','execution_evidence']}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_path(relative: str, suite: Path = SUITE) -> Path:
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'ars':
        raise ValueError('Role source must be an exact ars/-relative installed path')
    target = (suite / relative).resolve()
    if not target.is_relative_to(suite.resolve()):
        raise ValueError('Role source escapes the installed suite')
    return target


def skill_references(names: list[str]) -> list[dict]:
    """Bind installed skill bytes without granting any additional tools."""
    if not names:
        return []
    found = {}
    for file in (PROFILE / 'skills').rglob('SKILL.md'):
        relative = file.relative_to(PROFILE / 'skills')
        if 'ars' in relative.parts or any(part.startswith('.') for part in relative.parts):
            continue
        raw = file.read_bytes()
        text = raw.decode('utf-8')
        if not text.startswith('---\n'):
            continue
        metadata = yaml.safe_load(text.split('---', 2)[1]) or {}
        if metadata.get('name') in names:
            name = metadata['name']
            if name in found:
                raise ValueError('Ambiguous installed skill identity: ' + name)
            found[name] = {'name': name, 'absolute_path': str(file.resolve()), 'sha256': digest(raw)}
    if set(found) != set(names):
        raise ValueError('Missing installed role skill: ' + repr(sorted(set(names)-set(found))))
    return [found[name] for name in names]


def load_registry(path: Path | None = None) -> dict:
    if path is not None:
        raw = path.read_bytes()
    else:
        result = subprocess.run([str(BRIDGE), 'read', REGISTRY], capture_output=True, text=True, timeout=25)
        if result.returncode:
            raise ValueError('Cannot read current Paper role registry; delegation is refused')
        response = json.loads(result.stdout)
        if not response.get('ok'):
            raise ValueError('Paper role registry read was refused')
        row = response['result']
        raw = row['text'].encode('utf-8')
        if digest(raw) != row['sha256']:
            raise ValueError('Paper role registry readback hash mismatch')
    data = json.loads(raw)
    data['_registry_sha256'] = digest(raw)
    return data


def validate_registry(data: dict, model_routes: dict | None = None, suite: Path = SUITE) -> dict:
    if data.get('schema') != 'ars-role-routes/1':
        raise ValueError('Unsupported role registry')
    manifest = json.loads((suite/'manifest.json').read_text(encoding='utf-8'))
    source = next((row for row in manifest.get('source_repositories', [])
                   if row.get('name') == 'academic-research-skills'), None)
    lock = data['source_lock']
    if not source or source.get('version') != lock['suite_version'] or source.get('commit') != lock['upstream_commit']:
        raise ValueError('Role registry does not match the installed upstream source lock')
    expected = {str(path.relative_to(suite)) for group in ROLE_DIRS
                for path in (suite / 'ars' / group / 'agents').glob('*.md')}
    role_ids, covered = set(), set()
    for row in data['roles']:
        identifier = row['id']
        if identifier in role_ids or row['prompt_file'] in covered:
            raise ValueError('Duplicate role identity or prompt source: ' + identifier)
        role_ids.add(identifier)
        covered.add(row['prompt_file'])
        if (identifier != row['workflow'] + '/' + Path(row['prompt_file']).stem
                or row['prompt_file'] != 'ars/' + row['workflow'] + '/agents/' + Path(row['prompt_file']).name):
            raise ValueError('Role ID and source owner disagree: ' + identifier)
        if row['execution'] not in ('main', 'subagent'):
            raise ValueError('Unknown execution owner: ' + identifier)
        if digest(source_path(row['prompt_file'], suite).read_bytes()) != row['prompt_sha256']:
            raise ValueError('Role prompt changed; reconcile binding first: ' + identifier)
        if row['execution'] == 'main':
            if row['route'] is not None or row['tool_profile'] != 'main':
                raise ValueError('Main-session roles must not imply a worker fallback: ' + identifier)
        else:
            if not row['route'] or row['tool_profile'] not in data['tool_profiles']:
                raise ValueError('Subagent role lacks route/tool profile: ' + identifier)
            if model_routes is not None and row['route'] not in model_routes:
                raise ValueError('Missing configured model route: ' + row['route'])
        if not {'main_session_final_publication', 'actual_user_scope',
                'selected_role_and_workflow_contract'} <= set(row['gates']):
            raise ValueError('Missing role authority boundary: ' + identifier)
        if row['workflow'] != 'shared' and ('ars/' + row['workflow'] + '/WORKFLOW.md') not in row['protocols']:
            raise ValueError('Missing owning workflow contract: ' + identifier)
        for relative in row['protocols']:
            source_path(relative, suite).read_bytes()
    if covered != expected:
        raise ValueError('Role coverage mismatch: missing=' + repr(sorted(expected-covered))
                         + '; extra=' + repr(sorted(covered-expected)))
    calls = data.get('contract_calls', [])
    required_calls = {'academic-paper-reviewer/re_review_' + phase
                      for phase in ('phase1', 'phase2a', 'phase2b', 'phase2b_scoped')}
    if {row['id'] for row in calls} != required_calls or len(calls) != len(required_calls):
        raise ValueError('Re-review protocol-call inventory is incomplete or duplicated')
    for row in calls:
        if row['kind'] != 'protocol_call' or row['execution'] != 'subagent' or row['tool_profile'] != 'readonly':
            raise ValueError('Protocol calls must be explicitly read-only subagents')
        if (row['workflow'] != 'academic-paper-reviewer'
                or row['id'] != row['workflow'] + '/re_review_' + row['phase']
                or row['prompt_file'] != 'ars/academic-paper-reviewer/references/re_review_mode_protocol.md'
                or 'ars/academic-paper-reviewer/WORKFLOW.md' not in row['protocols']):
            raise ValueError('Protocol-call identity must match its owning protocol')
        if not {'actual_user_scope', 'main_session_final_publication',
                'selected_role_and_workflow_contract', 'phase_specific_withholding_matrix'} <= set(row['gates']):
            raise ValueError('Missing protocol-call authority boundary')
        raw = source_path(row['prompt_file'], suite).read_bytes()
        if digest(raw) != row['prompt_sha256'] or row['source_anchor'] not in raw.decode('utf-8'):
            raise ValueError('Protocol-call source or anchor changed: ' + row['id'])
        if model_routes is not None and row['route'] not in model_routes:
            raise ValueError('Missing protocol-call route: ' + row['route'])
        for path in row['protocols']:
            source_path(path, suite).read_bytes()
    aliases = {str(path.relative_to(suite)) for path in (suite / 'ars/agents').glob('*.md')}
    indexed = set()
    byid = {row['id']: row for row in data['roles']}
    for alias in data['aliases']:
        if alias['prompt_file'] in indexed:
            raise ValueError('Duplicate plugin alias')
        indexed.add(alias['prompt_file'])
        if alias['canonical_role'] not in byid:
            raise ValueError('Alias references unknown canonical role')
        sha = digest(source_path(alias['prompt_file'], suite).read_bytes())
        if sha != alias['sha256'] or sha != byid[alias['canonical_role']]['prompt_sha256']:
            raise ValueError('Plugin alias no longer byte-identical: ' + alias['prompt_file'])
    if aliases != indexed:
        raise ValueError('Plugin alias inventory is incomplete')
    instance_ids = set()
    required_seats = {'sr-screener/' + name for name in ('reviewer_a', 'reviewer_b', 'adjudicator', 'senior_qc')}
    if {row['id'] for row in data['instances']} != required_seats:
        raise ValueError('Screening seat inventory is incomplete or unrecognized')
    for instance in data['instances']:
        if set(instance) != {'id', 'canonical_role', 'seat', 'context_policy', 'prompt_variant_source', 'prompt_variant_anchor'}:
            raise ValueError('Instance may not override canonical execution, route or tools')
        if instance['id'] in role_ids | instance_ids or instance['canonical_role'] not in byid:
            raise ValueError('Invalid or duplicate instance')
        if instance['canonical_role'] != 'sr-screener/screening_reviewer_agent':
            raise ValueError('Screening seats must inherit the canonical screening reviewer')
        instance_ids.add(instance['id'])
        text = source_path(instance['prompt_variant_source'], suite).read_text(encoding='utf-8')
        if instance['prompt_variant_anchor'] not in text:
            raise ValueError('Screening prompt variant anchor is missing')
    if data.get('default_unknown_role') != 'refuse_no_parent_model_fallback':
        raise ValueError('Unsafe unknown-role policy')
    readonly = data['tool_profiles']['readonly']
    toolsets = [profile['toolset'] for profile in data['tool_profiles'].values()]
    if len(toolsets) != len(set(toolsets)):
        raise ValueError('Role toolset names must be unique')
    if readonly['toolset'] != 'ars_readonly' or set(readonly['tools']) != {'read_file','search_files'}:
        raise ValueError('Read-only role surface widened')
    return {'canonical_roles': len(role_ids), 'subagents': sum(row['execution']=='subagent' for row in data['roles']),
            'main_roles': sum(row['execution']=='main' for row in data['roles']),
            'aliases': len(indexed), 'instances': len(instance_ids), 'contract_calls': len(calls), 'unmapped': 0}


def resolve_role(data: dict, identifier: str) -> dict:
    aliases = {row['prompt_file']: row['canonical_role'] for row in data['aliases']}
    identifier = aliases.get(identifier, identifier)
    instance = next((item for item in data['instances'] if item['id'] == identifier), None)
    canonical = instance['canonical_role'] if instance else identifier
    row = next((row for row in data['roles'] + data.get('contract_calls', []) if row['id'] == canonical), None)
    if row is None:
        raise ValueError('Unknown role; no default fallback: ' + identifier)
    output = dict(row)
    output['canonical_role'] = canonical
    if instance:
        output.update({key:value for key,value in instance.items() if key != 'canonical_role'})
    return output


def role_plan(data: dict, identifier: str) -> dict:
    row = resolve_role(data, identifier)
    return {**row, 'execution_status':'configured_not_executed',
            'toolset': None if row['execution']=='main' else data['tool_profiles'][row['tool_profile']]['toolset'],
            'contract_load_required': True,
            'notice':'Binding and source hashes are configuration, not task authorization or scientific validation.'}


def role_brief(data: dict, identifier: str, goal: str, source_refs: list | None = None,
               suite: Path = SUITE, backend: str = 'model_map') -> dict:
    row = resolve_role(data, identifier)
    if row['execution'] != 'subagent':
        raise ValueError('This role belongs in the main session; it must not be delegated: ' + identifier)
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError('An explicit task goal is required')
    text = source_path(row['prompt_file'], suite).read_text(encoding='utf-8')
    if digest(text.encode('utf-8')) != row['prompt_sha256']:
        raise ValueError('Stale role source')
    refs = [{'path':path, 'sha256':digest(source_path(path,suite).read_bytes())}
            for path in row['protocols']]
    if 'prompt_variant_source' in row:
        path = row['prompt_variant_source']
        refs.append({'path':path, 'sha256':digest(source_path(path,suite).read_bytes())})
    context = {'schema':'ars-role-context/1', 'role_id':row['id'], 'canonical_role':row['canonical_role'],
               'registry_sha256':data['_registry_sha256'], 'prompt_file':row['prompt_file'],
               'prompt_sha256':row['prompt_sha256'],
               'prompt_absolute_path':str(source_path(row['prompt_file'],suite)),
               'prompt_delivery':'read_exact_installed_source_before_actual_work',
               'execution_instructions':EXECUTION_INSTRUCTIONS,
               'required_skills':row['skills'], 'skill_refs':skill_references(row['skills']), 'protocol_refs':refs,
               'source_anchor':row.get('source_anchor'), 'phase':row.get('phase'),
               'prompt_variant_anchor':row.get('prompt_variant_anchor'),
               'output_contract':row.get('output_contract', DEFAULT_OUTPUT_CONTRACT),
               'source_refs':source_refs or [], 'gates':row['gates'],
               'context_policy':row['context_policy'], 'seat':row.get('seat'),
               'publication':'candidate_only_main_session_publishes',
               'authorization':'derive_from_actual_user_task_not_this_file',
               'declared_tool_profile':row['tool_profile'],
               'tool_profile_enforcement':'parent_session_scope_not_per_task_native_parameters',
               'tool_scope_note':TOOL_SCOPE_NOTE}
    if backend not in ('model_map', 'ars_roles'):
        raise ValueError('Unsupported role transport backend: ' + backend)
    selector = {'option':row['route']} if backend == 'model_map' else {'ars_role':row['id']}
    payload = {'goal':goal, 'context':json.dumps(context,ensure_ascii=False), **selector}
    return {'schema':'ars-role-brief/1', 'execution_status':'prepared_not_dispatched',
            'role_id':row['id'], 'model_route':row['route'], 'native_task':payload,
            'delegation_backend':backend,
            'binding_enforcement':('preflight_only_not_enforced_by_model_map' if backend == 'model_map'
                                   else 'legacy_ars_roles_backend'),
            'parent_toolset_scope_for_strict_subset':['delegation', data['tool_profiles'][row['tool_profile']]['toolset']],
            'native_api_notice':'No model-facing role/toolsets task fields; child capability is depth-derived and tools inherit the parent scope.',
            'gates_require_actual_task_evidence':True}


def role_transport(brief: dict) -> dict:
    """Readable transport avoids tool truncation of one long escaped context line."""
    payload = dict(brief['native_task'])
    context = json.loads(payload.pop('context'))
    return {**{key:value for key,value in brief.items() if key != 'native_task'},
            'schema':'ars-role-transport/1', 'native_task_without_context':payload,
            'context_object':context,
            'dispatch_instruction':'Serialize context_object as a JSON string into native_task_without_context.context; preserve all binding values. This transport does not dispatch.'}


def validate_context(data: dict, row: dict, raw_context, suite: Path = SUITE) -> dict:
    try:
        context = json.loads(raw_context)
    except (TypeError, ValueError) as exc:
        raise ValueError('Use ars-paper role-brief; a bound JSON role context is required') from exc
    checks = {'schema':'ars-role-context/1', 'role_id':row['id'], 'canonical_role':row['canonical_role'],
              'registry_sha256':data['_registry_sha256'], 'prompt_file':row['prompt_file'],
              'prompt_sha256':row['prompt_sha256'], 'required_skills':row['skills'],
              'skill_refs':skill_references(row['skills']),
              'source_anchor':row.get('source_anchor'), 'phase':row.get('phase'),
              'prompt_variant_anchor':row.get('prompt_variant_anchor'),
              'output_contract':row.get('output_contract', DEFAULT_OUTPUT_CONTRACT),
              'execution_instructions':EXECUTION_INSTRUCTIONS,
              'authorization':'derive_from_actual_user_task_not_this_file',
              'declared_tool_profile':row['tool_profile'],
              'tool_profile_enforcement':'parent_session_scope_not_per_task_native_parameters',
              'tool_scope_note':TOOL_SCOPE_NOTE,
              'prompt_absolute_path':str(source_path(row['prompt_file'],suite)),
              'prompt_delivery':'read_exact_installed_source_before_actual_work',
              'gates':row['gates'], 'publication':'candidate_only_main_session_publishes',
              'context_policy':row['context_policy'], 'seat':row.get('seat')}
    if not isinstance(context,dict) or any(context.get(key)!=value for key,value in checks.items()):
        raise ValueError('Role identity, source, skill or gate binding mismatch')
    if digest(source_path(row['prompt_file'],suite).read_bytes()) != row['prompt_sha256']:
        raise ValueError('Role source bytes changed since binding')
    expected_protocols = list(row['protocols'])
    if 'prompt_variant_source' in row:
        expected_protocols.append(row['prompt_variant_source'])
    protocol_refs = context.get('protocol_refs', [])
    if not isinstance(protocol_refs, list) or not all(isinstance(ref, dict) for ref in protocol_refs):
        raise ValueError('Protocol references must be objects in a list')
    if [reference.get('path') for reference in protocol_refs] != expected_protocols:
        raise ValueError('Required role protocol references were omitted or changed')
    for reference in context.get('protocol_refs',[]):
        if digest(source_path(reference['path'],suite).read_bytes()) != reference['sha256']:
            raise ValueError('Protocol source changed; prepare a fresh brief')
    return context


def model_options(config: dict) -> dict:
    """Use installed official parsing; reject silently skipped/duplicate entries."""
    path = PROFILE / 'plugins/advanced-delegation/model_map.py'
    spec = importlib.util.spec_from_file_location('paper_official_model_map_parser', path)
    if spec is None or spec.loader is None:
        raise ValueError('Installed official Model routes parser is unavailable')
    module = importlib.util.module_from_spec(spec)
    # The standalone ars-paper interpreter does not inherit Hermes core's path.
    core = str(PROFILE.parent.parent / 'hermes-agent')
    added = core not in sys.path
    if added:
        sys.path.insert(0, core)
    try:
        spec.loader.exec_module(module)
    finally:
        if added:
            sys.path.remove(core)
    settings = config.get('backends', {}).get('model_map', {})
    raw = settings.get('options')
    if not isinstance(raw, list) or not raw:
        raise ValueError('Model routes options must be a non-empty list')
    parsed = module.configured_options(settings)
    if len(parsed) != len(raw):
        raise ValueError('Official model parser skipped invalid or duplicate normalized routes')
    return {name:{'name':name, 'description':value['description'], **value['route']}
            for name,value in parsed.items()}


def validate_native_task(data: dict, task: dict, config: dict, suite: Path = SUITE) -> dict:
    """Explicit preflight only; official model_map does not call this validator."""
    if config.get('backend') != 'model_map':
        raise ValueError('Start a fresh model_map session before dispatch')
    if not isinstance(task, dict) or set(task) != {'goal', 'context', 'option'}:
        raise ValueError('Official ARS payload must contain exactly goal/context/option')
    if not isinstance(task['goal'], str) or not task['goal'].strip():
        raise ValueError('An explicit task goal is required')
    try:
        context = json.loads(task['context'])
        identifier = context['role_id']
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Bound role context is required') from exc
    routes = model_options(config)
    validate_registry(data, routes, suite)
    row = resolve_role(data, identifier)
    if row['execution'] != 'subagent':
        raise ValueError('Main-session roles must not be delegated')
    validate_context(data, row, task['context'], suite)
    if task['option'] != row['route']:
        raise ValueError('Selected option does not match the role route')
    route = routes[task['option']]
    if not route.get('model') or not (route.get('provider') or route.get('base_url')):
        raise ValueError('Selected model route is incomplete')
    if route.get('fallback_providers') != []:
        raise ValueError('ARS model routes require explicit empty fallback_providers')
    return {'status':'pass', 'role_id':row['id'], 'option':task['option'],
            'enforcement':'explicit_preflight_only_not_runtime_interception',
            'authorization':'not_granted_by_preflight'}
