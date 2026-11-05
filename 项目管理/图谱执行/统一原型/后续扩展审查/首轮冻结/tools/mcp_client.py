"""Use only the configured academic SSH-backed Neo4j MCP route."""
import asyncio,contextlib,datetime,hashlib,json,os
from pathlib import Path
import yaml
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters,stdio_client
PROFILE=Path('/Users/wangyuelin/.hermes/profiles/academic')
def save(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
@contextlib.asynccontextmanager
async def connected(logdir):
 config=yaml.safe_load((PROFILE/'config.yaml').read_text())['mcp_servers'];cfg=config.get('neo4j-paper',config.get('neo4j_paper'))
 assert cfg and cfg['command']=='/usr/bin/ssh','Configured SSH route required'
 params=StdioServerParameters(command=cfg['command'],args=cfg['args'],cwd=cfg.get('cwd'),env={**os.environ,**cfg.get('env',{})})
 async with stdio_client(params) as (read,write):
  async with ClientSession(read,write,read_timeout_seconds=datetime.timedelta(seconds=120)) as session:
   await session.initialize();tools=(await session.list_tools()).tools;save(Path(logdir)/'mcp-tools.json',[t.model_dump(mode='json') for t in tools]);names={t.name.replace('-','_'):t.name for t in tools}
   assert 'read_cypher' in names and 'write_cypher' in names
   async def call(query,params=None,write=False,receipt=None):
    result=await session.call_tool(names['write_cypher' if write else 'read_cypher'],{'query':query,'params':params or {}},read_timeout_seconds=datetime.timedelta(seconds=120));raw=result.model_dump(mode='json')
    if receipt:save(receipt,{'query':query,'raw':raw,'at':datetime.datetime.now().astimezone().isoformat()})
    assert not result.isError,str(raw)
    texts=[x.text for x in result.content if getattr(x,'type',None)=='text'];value=json.loads('\n'.join(texts)) if texts else result.structuredContent
    while isinstance(value,dict) and 'result' in value:
     value=value['result'];value=json.loads(value) if isinstance(value,str) else value
    if isinstance(value,dict) and 'error' in value:raise RuntimeError(value['error'])
    return value
   yield call
SNAPSHOT='''CALL { MATCH (n) WITH n ORDER BY coalesce(n.uid,elementId(n)) RETURN collect({key:coalesce(n.uid,'eid:'+elementId(n)),labels:labels(n),properties:properties(n),types:[k IN keys(n)|{key:k,type:valueType(n[k])}]}) AS nodes } CALL { MATCH (a)-[r]->(b) WITH a,r,b ORDER BY coalesce(r.uid,elementId(r)) RETURN collect({key:coalesce(r.uid,'eid:'+elementId(r)),source:coalesce(a.uid,'eid:'+elementId(a)),target:coalesce(b.uid,'eid:'+elementId(b)),type:type(r),properties:properties(r),types:[k IN keys(r)|{key:k,type:valueType(r[k])}]}) AS relationships } RETURN nodes,relationships'''
CONSTRAINTS='SHOW CONSTRAINTS YIELD name,type,labelsOrTypes,properties RETURN name,type,labelsOrTypes,properties ORDER BY name'
INDEXES='SHOW INDEXES YIELD name,type,labelsOrTypes,properties,state RETURN name,type,labelsOrTypes,properties,state ORDER BY name'
def canonical(g):
 import copy
 g=copy.deepcopy(g)
 for k in ['nodes','relationships']:
  g[k].sort(key=lambda r:r['key'])
  for r in g[k]:
   if 'labels' in r:r['labels'].sort()
   r['types'].sort(key=lambda t:t['key'])
 return g
async def snapshot(call,out):
 out=Path(out);g=canonical((await call(SNAPSHOT,receipt=out/'raw.json'))[0]);save(out/'graph.json',g);schema={'constraints':await call(CONSTRAINTS),'indexes':await call(INDEXES)};save(out/'schema.json',schema);summary={'nodes':len(g['nodes']),'relationships':len(g['relationships']),'fingerprint':digest(g),'kind':'logical snapshot, not binary dump; restore not rehearsed'};save(out/'summary.json',summary);return g,summary
