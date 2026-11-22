"""Regression checks use isolated scratch roots, never the live Paper vault."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

BRIDGE = Path('/Users/wangyuelin/.hermes/profiles/academic/bin/mac-paper')
SCRATCH = Path('/Users/wangyuelin/.hermes/profiles/academic/cache/scratch')
MODULE = runpy.run_path(str(BRIDGE), run_name='bridge_test_module')
INNER = {}
exec(compile(MODULE['REMOTE_SOURCE'].split('\ntry:\n    REQUEST =')[0], '<bridge-test>', 'exec'), INNER)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mac-paper-test-', dir=SCRATCH)
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args, ok=True):
        p = subprocess.run([sys.executable, str(BRIDGE), '--root', str(self.root), *args], capture_output=True, text=True, timeout=20)
        result = json.loads(p.stdout)
        self.assertEqual(result['ok'], ok, result)
        self.assertEqual(p.returncode == 0, ok)
        return result.get('result') if ok else result['error']

    def create(self, name='new.md', text='中文正文\n'):
        return self.cli('write', name, '--expect-missing', '--create-mode', 'recoverable', '--text', text)

    def test_create_and_recovery_receipt(self):
        r = self.create()
        self.assertFalse(r['complete_file_atomic_visibility'])
        self.assertEqual(self.cli('read', 'new.md')['text'], '中文正文\n')
        rec = self.cli('recoveries', 'new.md')['records'][0]
        self.assertEqual(rec['status'], 'verified')
        self.assertEqual(sha((self.root / rec['payload_path']).read_bytes()), rec['sha256'])

    def test_binary_upload_download(self):
        payload = bytes(range(256)) * 20
        (self.root / 'input.bin').write_bytes(payload)
        self.cli('upload', str(self.root / 'input.bin'), 'out.bin', '--expect-missing', '--create-mode', 'recoverable')
        self.cli('download', 'out.bin', str(self.root / 'copy.bin'))
        self.assertEqual((self.root / 'copy.bin').read_bytes(), payload)

    def test_existing_target_rejected(self):
        self.create(text='keep')
        e = self.cli('write', 'new.md', '--expect-missing', '--create-mode', 'recoverable', '--text', 'erase', ok=False)
        self.assertEqual(e['code'], 'conflict')
        self.assertEqual(self.cli('read', 'new.md')['text'], 'keep')

    def test_stale_hash_and_backup_restore(self):
        self.create(text='original')
        e = self.cli('write', 'new.md', '--expected-sha256', '0' * 64, '--text', 'wrong', ok=False)
        self.assertEqual(e['code'], 'conflict')
        r = self.cli('write', 'new.md', '--expected-sha256', sha(b'original'), '--text', 'updated')
        backup = self.root / r['backup']['backup_path']
        self.assertEqual(backup.read_bytes(), b'original')
        self.cli('upload', str(backup), 'new.md', '--expected-sha256', sha(b'updated'))
        self.assertEqual(self.cli('read', 'new.md')['text'], 'original')

    def test_interrupted_create_recovery(self):
        actual_write = os.write
        count = 0
        def interrupt(fd, data):
            nonlocal count
            count += 1
            if count == 1:
                return actual_write(fd, data[:4])
            raise OSError('injected interruption')
        with patch('os.write', interrupt):
            with self.assertRaises(INNER['BridgeError']) as error:
                INNER['do_write'](self.root, 'partial.md', b'complete content', None, True, 'recoverable')
        self.assertEqual(error.exception.code, 'recoverable_write_incomplete')
        self.assertEqual((self.root / 'partial.md').read_bytes(), b'comp')
        rec = self.cli('recoveries', 'partial.md')['records'][0]
        self.assertEqual(rec['status'], 'interrupted')
        payload = self.root / rec['payload_path']
        self.assertEqual(sha(payload.read_bytes()), rec['sha256'])
        self.cli('upload', str(payload), 'partial.md', '--expected-sha256', sha(b'comp'))
        self.assertEqual((self.root / 'partial.md').read_bytes(), b'complete content')

    def test_short_writes(self):
        actual_write = os.write
        with patch('os.write', lambda fd, data: actual_write(fd, data[:3])):
            INNER['do_write'](self.root, 'short.md', b'1234567890', None, True, 'recoverable')
        self.assertEqual((self.root / 'short.md').read_bytes(), b'1234567890')

    def test_racing_external_creator(self):
        actual_open = os.open
        target = self.root / 'race.md'
        def race(path, flags, mode=0o777, **kwargs):
            if str(path) == str(target) and flags & os.O_EXCL and not target.exists():
                target.write_bytes(b'external')
            return actual_open(path, flags, mode, **kwargs)
        with patch('os.open', race):
            with self.assertRaises(INNER['BridgeError']) as error:
                INNER['do_write'](self.root, 'race.md', b'ours', None, True, 'recoverable')
        self.assertEqual(error.exception.code, 'conflict')
        self.assertEqual(target.read_bytes(), b'external')

    def test_parallel_creators(self):
        prefix = [sys.executable, str(BRIDGE), '--root', str(self.root), 'write', 'race.md', '--expect-missing', '--create-mode', 'recoverable', '--text']
        ps = [subprocess.Popen(prefix + [text], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for text in ['one', 'two']]
        results = [json.loads(p.communicate(timeout=20)[0]) for p in ps]
        self.assertEqual(sum(r['ok'] for r in results), 1)
        self.assertEqual([r['error']['code'] for r in results if not r['ok']], ['conflict'])
        self.assertIn((self.root / 'race.md').read_text(), ['one', 'two'])

    def test_default_atomic_and_explicit_opt_in(self):
        r = self.cli('write', 'atomic.md', '--expect-missing', '--text', 'default')
        self.assertTrue(r['complete_file_atomic_visibility'])
        self.assertEqual(r['publication_mode'], 'atomic-hardlink-create')
        with patch('os.link', side_effect=OSError('unsupported hardlink')):
            with self.assertRaises(INNER['BridgeError']):
                INNER['do_write'](self.root, 'no-fallback.md', b'data', None, True)
        self.assertFalse((self.root / 'no-fallback.md').exists())

    def test_path_and_parent_guards(self):
        for target in ['../escape.md', '/absolute.md', '.hermes-academic-backups/escape.md']:
            e = self.cli('write', target, '--expect-missing', '--create-mode', 'recoverable', '--text', 'no', ok=False)
            self.assertEqual(e['code'], 'invalid_path')
        self.assertEqual(self.cli('write', 'missing/a.md', '--expect-missing', '--create-mode', 'recoverable', '--text', 'no', ok=False)['code'], 'not_found')

    def test_recovery_symlink_guard(self):
        backup = self.root / '.hermes-academic-backups'
        backup.mkdir()
        outside = self.root / 'outside'
        outside.mkdir()
        (backup / 'recovery').symlink_to(outside, target_is_directory=True)
        e = self.cli('write', 'new.md', '--expect-missing', '--create-mode', 'recoverable', '--text', 'no', ok=False)
        self.assertEqual(e['code'], 'recovery_failed')
        self.assertFalse((self.root / 'new.md').exists())

    def test_empty_file(self):
        self.create(text='')
        self.assertEqual(self.cli('read', 'new.md')['size_bytes'], 0)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BridgeTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'successful': result.wasSuccessful(), 'bridge_sha256': sha(BRIDGE.read_bytes()), 'scope': 'isolated local scratch roots; fault injection is not physical power-loss testing'}
    (SCRATCH / 'mac-paper-recoverable-tests.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    sys.exit(not result.wasSuccessful())
