#!/usr/bin/env python3
"""Run on Linux after explicit approval for this plugin/config/restart change."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

base = Path.home() / '.local/share/neo4j-paper'
runtime = base / 'runtime/neo4j-community-5.26.32'
conf = Path.home() / '.config/neo4j-paper/conf/neo4j.conf'
original = conf.read_text()
backup = conf.with_name('neo4j.conf.before-mcp-20261022')
assert 'dbms.security.procedures.allowlist=' not in original
assert 'dbms.security.procedures.unrestricted=' not in original
jar = runtime / 'labs/apoc-5.26.32-core.jar'
target = runtime / 'plugins' / jar.name
assert not target.exists(), 'Existing plugin requires manual reconciliation'
if not backup.exists():
    shutil.copy2(conf, backup)
env = os.environ.copy()
env['JAVA_HOME'] = str(base / 'runtime/jdk-21.0.13+9')
env['NEO4J_CONF'] = str(conf.parent)
try:
    shutil.copy2(jar, target)
    conf.write_text(original + '\n# MCP v1.6.1: exact metadata-only APOC scope.\n'
                    'dbms.security.procedures.allowlist=apoc.meta.schema,apoc.version\n'
                    'dbms.security.procedures.unrestricted=apoc.meta.schema\n')
    subprocess.run([str(runtime / 'bin/neo4j-admin'), 'server', 'validate-config'],
                   env=env, check=True, capture_output=True, text=True)
    subprocess.run(['systemctl', '--user', 'restart', 'neo4j-paper.service'], check=True)
    spec = importlib.util.spec_from_file_location('kg', base / 'tools/导入与验证.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    credentials = module.load_credentials(Path.home() / '.config/neo4j-paper/access.json')
    endpoint = module.normalize_endpoint('http://100.68.38.32:7474')
    queries = [
        'RETURN apoc.version() AS apocVersion',
        'CALL apoc.meta.schema() YIELD value RETURN size(keys(value)) AS schemaEntries',
        "SHOW PROCEDURES YIELD name, mode WHERE name STARTS WITH 'apoc.' RETURN name,mode",
    ]
    for attempt in range(30):
        try:
            result = module.post_transaction(endpoint, credentials,
                                              [{'statement': q} for q in queries])
            break
        except module.ImportErrorWithContext:
            if attempt == 29:
                raise
            time.sleep(2)
    report = {'status': 'passed', 'apocJar': str(target),
              'apocSha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'configBackup': str(backup), 'unrestrictedProcedure': 'apoc.meta.schema',
              'queryResults': result,
              'testedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (base / 'reports/MCP-APOC启用.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
except Exception:
    conf.write_text(original)
    if target.exists():
        target.rename(target.with_suffix('.jar.disabled'))
    subprocess.run(['systemctl', '--user', 'restart', 'neo4j-paper.service'])
    raise
