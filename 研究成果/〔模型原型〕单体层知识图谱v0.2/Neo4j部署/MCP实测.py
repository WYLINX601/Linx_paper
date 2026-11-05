#!/usr/bin/env python3
"""Test the official server over the exact SSH stdio connection used by Codex."""
import argparse
import datetime
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

COMMAND = ['/usr/bin/ssh', '-T', '-o', 'BatchMode=yes',
           'linx-HP-EliteDesk-880-G6-Tower-PC', '/usr/bin/python3',
           '/home/linx/.local/share/neo4j-paper/tools/MCP启动.py']

class MCP:
    def __init__(self):
        self.process = subprocess.Popen(COMMAND, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = b''
        self.sequence = 0

    def send(self, value):
        self.process.stdin.write((json.dumps(value, ensure_ascii=False) + '\n').encode())
        self.process.stdin.flush()

    def request(self, method, params):
        self.sequence += 1
        sequence = self.sequence
        self.send({'jsonrpc': '2.0', 'id': sequence, 'method': method, 'params': params})
        end = time.monotonic() + 45
        while time.monotonic() < end:
            if b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                if not line.strip():
                    continue
                message = json.loads(line)
                if message.get('id') == sequence:
                    if 'error' in message:
                        raise RuntimeError(json.dumps(message['error'], ensure_ascii=False))
                    result = message['result']
                    if result.get('isError'):
                        raise RuntimeError(json.dumps(result, ensure_ascii=False))
                    return result
                continue
            if not self.selector.select(max(0, end - time.monotonic())):
                break
            data = os.read(self.process.stdout.fileno(), 65536)
            if not data:
                raise RuntimeError('MCP server closed stdout before responding')
            self.buffer += data
        raise TimeoutError('MCP response timed out')

    def close(self):
        self.selector.close()
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=3)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--queries', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    client = MCP()
    try:
        report = {'testedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'transport': 'SSH stdio', 'command': COMMAND}
        report['initialize'] = client.request('initialize', {
            'protocolVersion': '2024-11-05', 'capabilities': {},
            'clientInfo': {'name': 'paper-neo4j-acceptance', 'version': '1.0'}})
        client.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        report['tools'] = client.request('tools/list', {})['tools']
        report['calls'] = []
        for call in json.loads(args.queries.read_text()) if args.queries else []:
            result = client.request('tools/call', {
                'name': call['name'], 'arguments': call['arguments']})
            report['calls'].append({'purpose': call.get('purpose'), **call, 'result': result})
        report['status'] = 'passed'
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'status': 'passed', 'server': report['initialize']['serverInfo'],
                          'tools': [t['name'] for t in report['tools']],
                          'calls': len(report['calls']), 'report': str(args.output)}, ensure_ascii=False))
    finally:
        client.close()

if __name__ == '__main__':
    main()
