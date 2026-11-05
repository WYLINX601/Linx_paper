"""在授权的 Linux 用户目录部署固定版本。只在 Linux 上运行；不输出密码。"""
from pathlib import Path
import hashlib, json, os, secrets, shutil, subprocess, tarfile, time, urllib.request

BASE=Path.home()/'.local/share/neo4j-paper'
CONF=Path.home()/'.config/neo4j-paper'
UNIT=Path.home()/'.config/systemd/user/neo4j-paper.service'
IP='100.68.38.32'
PACKAGES=[
 {'name':'neo4j-community-5.26.32-unix.tar.gz','url':'https://dist.neo4j.org/neo4j-community-5.26.32-unix.tar.gz','sha256':'d279ae6a9b38034280681a558b0cd222dce89f87cc3d9867f1f7bd28ef5ebc30','directory':'neo4j-community-5.26.32'},
 {'name':'OpenJDK21U-jdk_x64_linux_hotspot_21.0.13_9.tar.gz','url':'https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.13%2B9/OpenJDK21U-jdk_x64_linux_hotspot_21.0.13_9.tar.gz','sha256':'d7f5d5cf865a2902b70ff549b97586a7d3f234e016f041ab447ea740c7d66d1c','directory':'jdk-21.0.13+9'},
]
if UNIT.exists() or (BASE/'deployment.json').exists():
    raise SystemExit('已有部署或服务，停止；需人工核对后维护，不覆盖。')
os.umask(0o077)
for p in [BASE,CONF,BASE/'downloads',BASE/'runtime',BASE/'data',BASE/'logs',BASE/'run',BASE/'import',BASE/'reports',BASE/'backups',BASE/'input',BASE/'tools']:
    p.mkdir(parents=True,exist_ok=True)

for pkg in PACKAGES:
    archive=BASE/'downloads'/pkg['name']
    def digest():
        h=hashlib.sha256()
        with archive.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        return h.hexdigest()
    if not archive.exists() or digest()!=pkg['sha256']:
        print('Downloading '+pkg['name'],flush=True)
        result=subprocess.run(['curl','--fail','--location','--retry','2','--connect-timeout','20','--max-time','600','--silent','--show-error','--output',str(archive),pkg['url']])
        if result.returncode:raise SystemExit('官方下载失败；保留已有部分文件以便诊断。')
    if digest()!=pkg['sha256']:raise SystemExit('SHA-256校验失败，停止解压。')
    print('Verified '+pkg['name'],flush=True)
    dest=BASE/'runtime'/pkg['directory']
    if not dest.exists():
        with tarfile.open(archive,'r:gz') as tf:tf.extractall(BASE/'runtime',filter='data')
    if not dest.is_dir():raise SystemExit('解压目录与固定版本不符。')

NEO=BASE/'runtime'/PACKAGES[0]['directory']
JAVA=BASE/'runtime'/PACKAGES[1]['directory']
shutil.copytree(NEO/'conf',CONF/'conf',dirs_exist_ok=True)
config=f'''# Paper 单体层知识图谱；仅绑定 Tailscale 私网地址。
server.default_listen_address={IP}
server.default_advertised_address={IP}
server.http.enabled=true
server.http.listen_address=:7474
server.http.advertised_address={IP}:7474
server.https.enabled=false
server.bolt.enabled=true
server.bolt.listen_address=:7687
server.bolt.advertised_address={IP}:7687
server.bolt.tls_level=DISABLED
dbms.security.auth_enabled=true
dbms.usage_report.enabled=false
initial.dbms.default_database=neo4j
server.directories.data={BASE}/data
server.directories.logs={BASE}/logs
server.directories.run={BASE}/run
server.directories.import={BASE}/import
server.memory.heap.initial_size=256m
server.memory.heap.max_size=768m
server.memory.pagecache.size=256m
db.tx_log.rotation.size=16M
db.tx_log.rotation.retention_policy=2 days 256M
db.tx_log.preallocate=false
'''
(CONF/'conf/neo4j.conf').write_text(config)
env=os.environ.copy();env.update(JAVA_HOME=str(JAVA),NEO4J_CONF=str(CONF/'conf'),NEO4J_HOME=str(NEO))
r=subprocess.run([str(NEO/'bin/neo4j-admin'),'server','validate-config'],env=env,capture_output=True,text=True)
print(r.stdout,flush=True)
if r.returncode:print(r.stderr);raise SystemExit('配置校验未通过；尚未启动。')
credfile=CONF/'access.json'
if credfile.exists():credentials=json.loads(credfile.read_text())
else:
    credentials={'username':'neo4j','password':secrets.token_urlsafe(24),'browser':f'http://{IP}:7474/browser/','bolt':f'bolt://{IP}:7687','database':'neo4j'}
    credfile.write_text(json.dumps(credentials,ensure_ascii=False,indent=2)+'\n');credfile.chmod(0o600)
marker=CONF/'initial-password-set'
if not marker.exists():
    r=subprocess.run([str(NEO/'bin/neo4j-admin'),'dbms','set-initial-password',credentials['password'],'--require-password-change=false'],env=env,capture_output=True,text=True)
    if r.returncode:raise SystemExit('初始化密码失败；错误输出未打印以免包含凭据。')
    marker.write_text('initialized\n')
UNIT.parent.mkdir(parents=True,exist_ok=True)
UNIT.write_text(f'''[Unit]
Description=Neo4j Community for Paper dwelling knowledge graph
After=network-online.target

[Service]
Type=simple
WorkingDirectory={NEO}
Environment=JAVA_HOME={JAVA}
Environment=NEO4J_HOME={NEO}
Environment=NEO4J_CONF={CONF}/conf
ExecStart={NEO}/bin/neo4j console
Restart=on-failure
RestartSec=10
TimeoutStopSec=120
SuccessExitStatus=143
LimitNOFILE=65535
UMask=0077
MemoryHigh=1800M
MemoryMax=2300M

[Install]
WantedBy=default.target
''')
for cmd in [['systemctl','--user','daemon-reload'],['systemctl','--user','enable','--now','neo4j-paper.service']]:
    subprocess.run(cmd,check=True)
manifest={'date':'2026-10-22','service':'neo4j-paper.service','base':str(BASE),'config':str(CONF/'conf'),'credentials':str(credfile),'listenAddress':IP,'ports':[7474,7687],'neo4j':'5.26.32-community','java':'Temurin 21.0.13+9','packages':PACKAGES,'access':'Tailscale私网 + Neo4j认证；不绑定校园网或公网接口','scope':'用户目录部署；未安装Docker或修改全局Java。','memory':'heap max 768MiB + page cache 256MiB; service MemoryMax 2300M'}
(BASE/'deployment.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'installed':True,'base':str(BASE),'browser':credentials['browser'],'credentialsFile':str(credfile)},ensure_ascii=False),flush=True)
