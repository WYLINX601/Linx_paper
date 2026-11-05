"""Read-only verification against the currently published source and receipts."""
import asyncio,json,subprocess,tempfile
from pathlib import Path
from types import SimpleNamespace
from compile_model import MODEL,PACKAGE
from run_graph import main
from mcp_client import PROFILE
if __name__=='__main__':
    scratch=PROFILE/'cache/scratch';scratch.mkdir(parents=True,exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix='d03-six-readonly-',dir=scratch))
    paths={MODEL:'model.json',PACKAGE+'/Neo4j/执行阶段.json':'db/execution-stage.json',PACKAGE+'/Neo4j/扩展前/逻辑快照.json':'db/before/graph.json',PACKAGE+'/Neo4j/扩展前/Schema.json':'db/before/schema.json'}
    for source,target in paths.items():
        local=d/target;local.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run([str(PROFILE/'bin/mac-paper'),'download',source,str(local)],capture_output=True,text=True,check=True)
    stage=json.loads((d/'db/execution-stage.json').read_text())
    asyncio.run(main(SimpleNamespace(workspace=str(d),model=str(d/'model.json'),model_sha=stage['modelSHA256'],mode='verify')))
    print('Read-only verification evidence:',d)
