#!/usr/bin/env python3
"""Linux stdio launcher; credentials remain in the private server file."""
import json
import os
from pathlib import Path

home = Path.home()
credentials = json.loads((home / '.config/neo4j-paper/access.json').read_text())
binary = home / '.local/share/neo4j-paper/mcp/v1.6.1/neo4j-mcp'
env = os.environ.copy()
env.update({
    'NEO4J_MCP_URI': credentials['bolt'],
    'NEO4J_MCP_USERNAME': credentials['username'],
    'NEO4J_MCP_PASSWORD': credentials['password'],
    'NEO4J_MCP_DATABASE': credentials['database'],
    'NEO4J_MCP_TRANSPORT_MODE': 'stdio',
    'NEO4J_MCP_READ_ONLY': 'true',
    'NEO4J_MCP_TELEMETRY': 'false',
    'NEO4J_MCP_LOG_LEVEL': 'error',
    'NEO4J_MCP_SCHEMA_SAMPLE_SIZE': '100',
})
os.execve(str(binary), [str(binary)], env)
