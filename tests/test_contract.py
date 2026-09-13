"""Offline contract/publication fixtures; run after `swift build`."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(os.environ.get('CENSUS_BINARY', ROOT / '.build/debug/WinnowCensus'))
DATE = '2026-09-11T07:08:08Z'

def onion(n):
    key = n.to_bytes(32, 'big')
    checksum = hashlib.sha3_256(b'.onion checksum' + key + b'\x03').digest()[:2]
    return base64.b32encode(key + checksum + b'\x03').decode().lower() + '.onion'

def record(host, height=900_000, outcome='ok', latency=10):
    return dict(host=host, port=8333, outcome=outcome, userAgent='/Satoshi:30/',
                startHeight=height, services=64, latencyMs=latency,
                network='tor' if host.endswith('.onion') else 'i2p' if host.endswith('.i2p') else 'clearnet',
                runStartedAt=DATE, observedAt=DATE, inputSHA256='0' * 64, runSample=0)

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def run_records(self, records, extra=(), success=True):
        for r in records:
            r.setdefault('expectedRecords', len(records))
        raw = self.root / 'records.jsonl'
        raw.write_text(''.join(json.dumps(r) + '\n' for r in records))
        result = subprocess.run([str(BIN), '--replay', str(raw), '--tip', '900000', '--summary-json', str(self.root / 'summary.json'),
                                 '--tor-socks', '127.0.0.1:9050', '--i2p-socks', '127.0.0.1:4447', *extra], capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stderr.decode())
        if success:
            return json.loads((self.root / 'summary.json').read_text()), json.loads((self.root / 'peers.json').read_text())
    def full(self):
        return [record('8.8.8.8'), record(onion(1)), record('a' * 52 + '.b32.i2p')]
    def publish(self, success=True):
        result = subprocess.run([str(ROOT / 'scripts/census-publish'), str(self.root / 'summary.json'), '--peers', str(self.root / 'peers.json'),
                                 '--records', str(self.root / 'records.jsonl'), '--validator', str(BIN), '--dir', str(self.root / 'public')], capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stderr.decode())
    def test_replay_dates_and_complete_publication(self):
        s, p = self.run_records(self.full())
        self.assertEqual(s['generatedAt'], DATE)
        self.assertEqual(p['date'], DATE[:10])
        self.assertTrue(s['completeRun'])
        self.publish()
        self.assertTrue((self.root / 'public/2026-09-11.json').exists())
        days = json.loads((self.root / 'public/index.json').read_text())['days']
        self.assertEqual([d['date'] for d in days], ['2026-09-11'])
    def test_symmetric_extreme_heights(self):
        s, p = self.run_records([record('8.8.8.8', 900100), record('9.9.9.9', 899900), record('1.1.1.1', 900101),
                                 record('2.2.2.2', -2147483648), record('3.3.3.3', 2147483647)])
        self.assertEqual(s['networks']['clearnet']['atTip'], 2)
        self.assertEqual(s['families']['Core']['atTip'], 2)
        self.assertEqual(len(p['networks']['clearnet']), 2)
    def test_aliases_validation_and_diversity(self):
        rows = [record('::ffff:8.8.8.8'), record('8.8.8.8'), record('8.8.4.4'), record('127.0.0.1'),
                record('2001:db8::1'), record(onion(1).upper()), record(onion(1)), record('a'*56+'.onion')]
        _, p = self.run_records(rows)
        self.assertEqual(len(p['networks']['clearnet']), 1)
        self.assertEqual(len(p['networks']['tor']), 1)
        self.assertEqual(p['networks']['tor'][0]['host'], onion(1))
        before = (self.root / 'peers.json').read_bytes()
        self.run_records(list(reversed(rows)))
        self.assertEqual(before, (self.root / 'peers.json').read_bytes())
    def test_overlay_cap(self):
        _, p = self.run_records([record(onion(n)) for n in range(2005)])
        self.assertEqual(len(p['networks']['tor']), 2000)
    def test_missing_or_invalid_replay_dates(self):
        rows = self.full()
        for r in rows: r.pop('runStartedAt')
        self.run_records(rows, success=False)
        self.run_records(rows, extra=('--observed-at', DATE))
        self.run_records(rows, extra=('--observed-at', '2099-01-01T00:00:00Z'), success=False)
        self.run_records(rows, extra=('--observed-at', '2026-02-30T00:00:00Z'), success=False)
    def test_failure_retains_all_previous_good_files(self):
        self.run_records(self.full()); self.publish()
        public = self.root / 'public'
        baseline = {p.name: p.read_bytes() for p in public.iterdir()}
        for field, value in [('completeRun', False), ('sample', 1), ('expectedRecords', 10), ('peerListSHA256', 'wrong')]:
            self.run_records(self.full())
            p = self.root / 'summary.json'; s = json.loads(p.read_text()); s[field] = value; p.write_text(json.dumps(s))
            self.publish(success=False)
            self.assertEqual(baseline, {p.name: p.read_bytes() for p in public.iterdir()})
        rows = self.full(); rows[1]['outcome'] = 'timeout'
        self.run_records(rows); self.publish(success=False)
        self.assertEqual(baseline, {p.name: p.read_bytes() for p in public.iterdir()})

if __name__ == '__main__': unittest.main()
