"""Compatibility entry: use the guarded replacement executor, never first-create."""
import sys,subprocess
from pathlib import Path
if __name__=='__main__':
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).with_name('run_graph.py')),*sys.argv[1:],'--mode','preflight']))
