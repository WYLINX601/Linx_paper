"""Configured SSH-backed MCP only; no direct database credentials or driver."""
import asyncio, contextlib, datetime, hashlib, json, os
from pathlib import Path
import yaml
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PROFILE = Path('/Users/wangyuelin/.hermes/profiles/academic')

def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

@contextlib.asynccontextmanager
async def connected(logdir):
    # Read only this configured server; never export configuration or credentials.
    config = yaml.safe_load((PROFILE / 'config.yaml').read_text())['mcp_servers']
    cfg = config.get('neo4j-paper', config.get('neo4j_paper'))
    assert cfg and cfg['command'] == '/usr/bin/ssh', 'Configured SSH route required'
    params = StdioServerParameters(command=cfg['command'], args=cfg['args'], cwd=cfg.get('cwd'), env={**os.environ, **cfg.get('env', {})})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=datetime.timedelta(seconds=120)) as session:
            init = await session.initialize()
            tools = (await session.list_tools()).tools
            save(Path(logdir)/'mcp-tools.json', [t.model_dump(mode='json') for t in tools])
            names = {t.name.replace('-', '_'):t.name for t in tools}
            assert 'read_cypher' in names and 'write_cypher' in names
            async def call(query, params=None, write=False, receipt=None):
                result = await session.call_tool(names['write_cypher' if write else 'read_cypher'], {'query':query, 'params':params or {}}, read_timeout_seconds=datetime.timedelta(seconds=120))
                raw = result.model_dump(mode='json')
                if receipt: save(receipt, {'query':query, 'raw':raw, 'at':datetime.datetime.now().astimezone().isoformat()})
                assert not result.isError, str(raw)
                texts = [x.text for x in result.content if getattr(x,'type',None)=='text']
                value = json.loads('\n'.join(texts)) if texts else result.structuredContent
                while isinstance(value,dict) and 'result' in value:
                    value = value['result']; value = json.loads(value) if isinstance(value,str) else value
                if isinstance(value,dict) and 'error' in value: raise RuntimeError(value['error'])
                return value
            yield call

SNAPSHOT = '''CALL {
 MATCH (n) WITH n ORDER BY coalesce(n.uid,elementId(n))
 RETURN collect({key:coalesce(n.uid,'eid:'+elementId(n)),labels:labels(n),properties:properties(n),types:[k IN keys(n) | {key:k,type:valueType(n[k])}]}) AS nodes
} CALL {
 MATCH (a)-[r]->(b) WITH a,r,b ORDER BY coalesce(r.uid,elementId(r))
 RETURN collect({key:coalesce(r.uid,'eid:'+elementId(r)),source:coalesce(a.uid,'eid:'+elementId(a)),target:coalesce(b.uid,'eid:'+elementId(b)),type:type(r),properties:properties(r),types:[k IN keys(r) | {key:k,type:valueType(r[k])}]}) AS relationships
} RETURN nodes,relationships'''
CONSTRAINTS = 'SHOW CONSTRAINTS YIELD name,type,labelsOrTypes,properties RETURN name,type,labelsOrTypes,properties ORDER BY name'
INDEXES = 'SHOW INDEXES YIELD name,type,labelsOrTypes,properties,state RETURN name,type,labelsOrTypes,properties,state ORDER BY name'

def canonical(graph):
    import copy
    g=copy.deepcopy(graph)
    for category in ('nodes','relationships'):
        g[category].sort(key=lambda r:r['key'])
        for row in g[category]:
            if 'labels' in row: row['labels'].sort()
            row['types'].sort(key=lambda t:t['key'])
    return g

async def snapshot(call, out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    g=canonical((await call(SNAPSHOT,receipt=out/'raw.json'))[0])
    save(out/'graph.json',g)
    constraints=await call(CONSTRAINTS)
    indexes=await call(INDEXES)
    save(out/'schema.json',{'constraints':constraints,'indexes':indexes})
    summary={'nodes':len(g['nodes']),'relationships':len(g['relationships']),'fingerprint':digest(g),'kind':'logical snapshot, not binary dump; restore not rehearsed'}
    save(out/'summary.json',summary)
    return g,summary

async def main():
    import sys
    out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
    async with connected(out) as call:
        print('connection',await call("RETURN 'connected' AS status"))
        print('components',await call('CALL dbms.components() YIELD name,versions,edition RETURN name,versions,edition',write=True))
        g,s=await snapshot(call,out/'before')
        assert not any(n['properties'].get('caseId')=='D03V01' or n['key'].startswith('D03V01:') for n in g['nodes']), 'D03 namespace already present: inspect before writing'
        print(json.dumps(s,ensure_ascii=False))
if __name__=='__main__': asyncio.run(main())
