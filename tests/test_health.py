import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from census_health import calculate


def run(day=13, height=100, outcome='ok'):
    stamp = f'2026-09-{day:02d}T12:00:00Z'
    records = []
    for host, network in [('8.8.8.8', 'clearnet'), ('a' * 56 + '.onion', 'tor'), ('a' * 52 + '.b32.i2p', 'i2p')]:
        records.append(dict(host=host, port=8333, network=network, runStartedAt=stamp,
                            observedAt=stamp, runSample=0, inputSHA256='a' * 64,
                            outcome=outcome, startHeight=height, services=64,
                            userAgent='/old-version/', latencyMs=1))
    raw = ('\n'.join(json.dumps(r) for r in records) + '\n').encode()
    summary = dict(generatedAt=stamp, observationEndedAt=stamp, completeRun=True,
                   sample=0, recordsSHA256=hashlib.sha256(raw).hexdigest(),
                   observedTip=100, dialled=3, expectedRecords=3,
                   inputSHA256='a' * 64, processingRevision='b' * 40,
                   networks={n: dict(dialled=1, usable=1, noCompactFilters=0)
                             for n in ('clearnet', 'tor', 'i2p')})
    return summary, raw


class HealthTests(unittest.TestCase):
    now = dt.datetime(2026, 9, 13, 18, tzinfo=dt.timezone.utc)

    def test_one_day_and_replay_do_not_claim_consistency(self):
        report = calculate([run(), run()], self.now)
        self.assertEqual(len(report['acceptedDays']), 1)
        self.assertTrue(all(n['consistencyScore'] is None for n in report['nodes']))
        self.assertIsNone(report['overallBitcoinHealthScore'])

    def test_gaps_are_not_failures_and_old_software_has_no_penalty(self):
        report = calculate([run(9), run(11), run(13)], self.now)
        for node in report['nodes']:
            self.assertEqual(node['attemptDays'], 3)
            self.assertEqual(node['consistencyScore'], 100)

    def test_extreme_and_negative_heights_do_not_overflow(self):
        report = calculate([run(9), run(11, 2**128), run(13, -1)], self.now)
        for node in report['nodes']:
            self.assertAlmostEqual(node['consistencyScore'], 100 / 3)

    def test_future_partial_hash_and_overlay_failures_rejected(self):
        cases = [('sample', 1), ('completeRun', False), ('recordsSHA256', 'bad'),
                 ('expectedRecords', 4), ('observationEndedAt', '2099-01-01T00:00:00Z')]
        for key, value in cases:
            summary, raw = run()
            summary[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                calculate([(summary, raw)], self.now)
        summary, raw = run()
        summary['networks']['tor']['usable'] = 0
        with self.assertRaises(ValueError):
            calculate([(summary, raw)], self.now)

    def test_different_same_day_run_requires_selection(self):
        with self.assertRaises(ValueError):
            calculate([run(13, 99), run(13, 100)], self.now)

    def test_run_order_does_not_change_report(self):
        runs = [run(9), run(11), run(13)]
        self.assertEqual(calculate(runs, self.now), calculate(list(reversed(runs)), self.now))
