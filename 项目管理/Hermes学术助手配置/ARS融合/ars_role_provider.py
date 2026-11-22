"""Hermes native role-aware delegation backend, composing existing model routes."""
from __future__ import annotations
import subprocess
from agent.delegation_provider import DelegationProvider, DelegationRouteError
from ars_role_routes import load_registry, validate_registry, resolve_role, validate_context

FIELDS = ('provider','model','base_url','api_mode','reasoning_effort','service_tier')


def model_options(config):
    options = config.get('backends',{}).get('model_map',{}).get('options',[])
    found = {}
    for row in options:
        if row['name'] in found:
            raise ValueError('Duplicate model route: ' + row['name'])
        found[row['name']] = row
    return found


class ArsRoleProvider(DelegationProvider):
    def __init__(self, registered_registry_sha256=None):
        self._registered_registry_sha256 = registered_registry_sha256

    def check_registry_epoch(self, data):
        if (self._registered_registry_sha256 is not None
                and data['_registry_sha256'] != self._registered_registry_sha256):
            raise ValueError('ARS registry changed since tool/schema registration; start a fresh session')

    @property
    def name(self):
        return 'ars_roles'

    @property
    def display_name(self):
        return 'Paper ARS role routes'

    @property
    def summary(self):
        return 'Source-locked ARS roles mapped onto existing model routes; explicit native options remain available.'

    def task_parameters(self, config):
        data = load_registry()
        self.check_registry_epoch(data)
        options = model_options(config)
        validate_registry(data, options)
        canonical = [row['id'] for row in data['roles'] if row['execution']=='subagent']
        instances = [row['id'] for row in data['instances']]
        calls = [row['id'] for row in data.get('contract_calls', [])]
        return {
            'ars_role': {'type':'string','enum':canonical+instances+calls,
                         'description':'ARS role ID. Obtain goal/context/ars_role from ars-paper role-brief. Main-session roles cannot be delegated. The current native API inherits parent tools; strict subsets require a restricted parent session.'},
            'option': {'type':'string','enum':list(options),
                       'description':'For explicitly non-ARS native-extension tasks only. Mutually exclusive with ars_role; never an implicit fallback.'},
        }

    def description(self, config):
        return ('ARS tasks must set ars_role with the bound role context from ars-paper role-brief. '
                'Do not invent native role/toolsets task fields: the installed API inherits parent tools. '
                'Use the declared parent CLI toolset scope for strict read-only/candidate/compute boundaries. '
                'Native-extension tasks may explicitly set option instead. No implicit parent-model fallback.')

    def route_task(self, task, config):
        try:
            options = model_options(config)
            role_id, option = task.get('ars_role'), task.get('option')
            if bool(role_id) == bool(option):
                raise ValueError('Supply exactly one ars_role or explicit native-extension option; no fallback')
            if option:
                if option not in options:
                    raise ValueError('Unknown model route: ' + str(option))
                chosen = options[option]
                label = 'native:' + option
            else:
                if config.get('inherit_mcp_toolsets') is not False:
                    raise ValueError('ARS compatibility policy requires inherit_mcp_toolsets=false; this alone does not restrict inherited parent tools')
                data = load_registry()
                self.check_registry_epoch(data)
                validate_registry(data, options)
                row = resolve_role(data, role_id)
                if row['execution'] != 'subagent':
                    raise ValueError('This role is owned by the main session, not a child: ' + role_id)
                validate_context(data, row, task.get('context'))
                chosen = options[row['route']]
                label = row['id']
            if not all(chosen.get(key) for key in ('provider','model','reasoning_effort')):
                raise ValueError('Configured route lacks explicit provider/model/reasoning effort')
            route = {key:chosen[key] for key in FIELDS if chosen.get(key)}
            # No implicit credential/fallback selection; core resolves the named existing provider.
            route['fallback_providers'] = []
            route['label'] = label
            return route
        except (KeyError, TypeError, OSError, ValueError, subprocess.SubprocessError) as exc:
            raise DelegationRouteError(str(exc)) from exc


def register(ctx):
    from toolsets import create_custom_toolset
    data = load_registry()
    validate_registry(data)
    for profile in data['tool_profiles'].values():
        create_custom_toolset(profile['toolset'],
                              'ARS role-specific subset; no added tool implementations',
                              tools=profile['tools'])
    ctx.register_delegation_provider(ArsRoleProvider(data['_registry_sha256']))
