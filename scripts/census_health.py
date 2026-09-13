#!/usr/bin/env python3
"""Replay endpoint consistency from accepted, hash-linked full runs.

No network access and no mutation of peer catalogs. Each manifest entry provides
summary and records paths (plain or gzip); paths are relative to the manifest.
The output keeps missing components null instead of inventing a Bitcoin grade.
"""
import argparse
import collections
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from census_compare import endpoint, overlay

UTC = dt.timezone.utc
MAX_BYTES = 32 * 1024 * 1024


def read(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('oversized evidence')
    return data


def stamp(value):
    result = dt.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)
    return result


def ratio(n, d):
    return 100 * n / d if d else None


def accepted(summary, raw, now):
    start, end = stamp(summary['generatedAt']), stamp(summary['observationEndedAt'])
    if not start <= end <= now:
        raise ValueError('invalid observation window')
    if summary.get('completeRun') is not True or summary.get('sample') != 0:
        raise ValueError('diagnostic or incomplete run')
    if hashlib.sha256(raw).hexdigest() != summary.get('recordsSHA256'):
        raise ValueError('raw evidence hash mismatch')
    if type(summary['observedTip']) is not int or summary['observedTip'] < 0:
        raise ValueError('invalid reference tip')
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if len(records) != summary['dialled'] or len(records) != summary['expectedRecords'] or not records:
        raise ValueError('incomplete records')
    nets = summary['networks']
    if set(nets) != {'clearnet', 'tor', 'i2p'}:
        raise ValueError('missing overlay')
    for n in nets.values():
        if n['dialled'] <= 0 or not .5 <= (n['usable'] + n['noCompactFilters']) / n['dialled'] <= 1:
            raise ValueError('unhealthy overlay')
    seen, counts = set(), collections.Counter()
    for r in records:
        key = endpoint(f"{r['host']}:{r['port']}")
        network = overlay(key)
        expected = 'clearnet' if network in ('ipv4', 'ipv6') else network
        if expected not in nets or r['network'] != expected or key in seen:
            raise ValueError('duplicate or misclassified endpoint')
        if (r.get('runStartedAt') != summary['generatedAt'] or r.get('runSample') != 0
                or r.get('inputSHA256') != summary.get('inputSHA256')
                or not start <= stamp(r['observedAt']) <= end):
            raise ValueError('record provenance mismatch')
        seen.add(key)
        counts[expected] += 1
    if any(counts[k] != v['dialled'] for k, v in nets.items()):
        raise ValueError('overlay count mismatch')
    return start, records


def calculate(runs, now):
    days, nodes, evidence = {}, {}, []
    cutoff = now.date() - dt.timedelta(days=29)
    for summary, raw in runs:
        start, records = accepted(summary, raw, now)
        day = start.date().isoformat()
        if start.date() < cutoff:
            continue
        if day in days:
            if days[day] == summary['recordsSHA256']:
                continue  # Replaying identical evidence never increases confidence.
            raise ValueError('multiple observations on one day require explicit run selection')
        days[day] = summary['recordsSHA256']
        evidence.append({k: summary[k] for k in (
            'generatedAt', 'observationEndedAt', 'observedTip', 'inputSHA256',
            'recordsSHA256', 'processingRevision')})
        for r in records:
            key = endpoint(f"{r['host']}:{r['port']}")
            node = nodes.setdefault(key, {'endpoint': key, 'network': overlay(key), 'observations': []})
            answered = r['outcome'] in ('ok', 'noCompactFilters')
            height = r.get('startHeight')
            near = answered and type(height) is int and height >= 0 and abs(height - summary['observedTip']) <= 100
            node['observations'].append({
                'date': day, 'outcome': r['outcome'], 'answered': answered,
                'nearTipReport': near, 'reportedHeight': height,
                'userAgent': r.get('userAgent'), 'services': r.get('services'),
                'probeDurationMs': r.get('latencyMs')})
    for node in nodes.values():
        obs = sorted(node['observations'], key=lambda x: x['date'])
        node['observations'] = obs
        node['attemptDays'] = len(obs)
        node['responseDays'] = sum(o['answered'] for o in obs)
        node['nearTipResponseDays'] = sum(o['nearTipReport'] for o in obs)
        node['consistencyScore'] = ratio(node['nearTipResponseDays'], len(obs)) if len(obs) >= 3 else None
        node['status'] = 'measured' if len(obs) >= 3 else 'insufficient_history'
    return {
        'schemaVersion': 1, 'modelVersion': 'observed-consistency-1',
        'asOf': now.isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'windowStartDate': cutoff.isoformat(), 'acceptedDays': sorted(days),
        'overallBitcoinHealthScore': None,
        'overallStatus': 'unavailable: mining evidence and a validated composite model are required',
        'mining': {'status': 'unavailable', 'metrics': None},
        'definitions': {'consistencyScore': '100 * near-tip version response days / attempted days; minimum 3 days',
                        'missingDays': 'not attempted; excluded from denominator',
                        'capabilities': 'reported services, separate from consistency; age has no automatic penalty'},
        'evidence': sorted(evidence, key=lambda x: x['generatedAt']),
        'nodes': [nodes[k] for k in sorted(nodes)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--as-of', required=True, help='UTC timestamp, YYYY-MM-DDTHH:MM:SSZ')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    now = stamp(args.as_of)
    if now > dt.datetime.now(UTC):
        parser.error('future evaluation time')
    manifest = json.loads(read(args.manifest))
    if manifest.get('schemaVersion') != 1 or not 0 < len(manifest['runs']) <= 30:
        parser.error('unknown schema or invalid run count')
    base = args.manifest.resolve().parent
    runs = [(json.loads(read(base / r['summary'])), read(base / r['records'])) for r in manifest['runs']]
    report = calculate(runs, now)
    report['manifestSHA256'] = hashlib.sha256(read(args.manifest)).hexdigest()
    report['processingRevision'] = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[1], text=True).strip()
    data = (json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=args.out.parent, delete=False) as f:
        f.write(data)
        staged = f.name
    os.replace(staged, args.out)
    print(f"{len(report['nodes'])} endpoints; {len(report['acceptedDays'])} accepted days; composite unavailable")


if __name__ == '__main__':
    main()
