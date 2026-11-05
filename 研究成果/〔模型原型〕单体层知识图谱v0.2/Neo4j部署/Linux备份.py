#!/usr/bin/env python3
"""Run on the installed Linux host: consistent dump, then restart and verify."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

base = Path.home() / '.local/share/neo4j-paper'
meta = json.loads((base / 'deployment.json').read_text())
env = os.environ.copy()
env.update(JAVA_HOME=str(base / 'runtime/jdk-21.0.13+9'),
           NEO4J_CONF=str(Path(meta['config'])))
admin = str(base / 'runtime/neo4j-community-5.26.32/bin/neo4j-admin')
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup = base / 'backups' / stamp
backup.mkdir(mode=0o700)

def run(args):
    return subprocess.run(args, env=env, check=True, capture_output=True, text=True).stdout

run(['systemctl', '--user', 'stop', 'neo4j-paper.service'])
try:
    dump_log = run([admin, 'database', 'dump', 'neo4j', '--to-path=' + str(backup)])
    info = run([admin, 'database', 'load', 'neo4j', '--from-path=' + str(backup), '--info'])
    shutil.copytree(base / 'input', backup / 'input')
    shutil.copy2(base / 'deployment.json', backup / 'deployment.json')
    shutil.copy2(Path(meta['config']) / 'neo4j.conf', backup / 'neo4j.conf')
    (backup / 'archive-info.txt').write_text(info)
finally:
    run(['systemctl', '--user', 'start', 'neo4j-paper.service'])

verify_args = ['python3', str(base / 'tools/导入与验证.py'),
               '--source-dir', str(base / 'input'),
               '--endpoint', 'http://' + meta['listenAddress'] + ':7474',
               '--credentials-file', str(Path.home() / '.config/neo4j-paper/access.json'),
               '--output-dir', str(base / 'reports/after-restart'), '--mode', 'verify']
for attempt in range(30):
    result = subprocess.run(verify_args, capture_output=True, text=True)
    if result.returncode == 0:
        break
    time.sleep(2)
else:
    raise RuntimeError('Service restarted but database verification did not pass within 60 seconds')

dump = backup / 'neo4j.dump'
report = {'status': 'passed', 'backupDirectory': str(backup),
          'dumpBytes': dump.stat().st_size,
          'dumpSha256': hashlib.sha256(dump.read_bytes()).hexdigest(),
          'archiveInfo': info, 'serviceRestartAndGraphVerification': 'passed',
          'boundary': 'Native dump metadata checked; no restoration into another database performed. The system/auth database is not included.'}
(base / 'reports/备份与重启.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
