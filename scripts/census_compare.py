#!/usr/bin/env python3
"""Capture public evidence, then repeat normalization/comparison without network.

capture --out DIR [--btcnodes PATH] [--winnow-summary PATH] [--winnow-records PATH]
compare DIR
Each source fails independently. No command publishes production census data.
"""
import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import html.parser
import io
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import urllib.request

UTC = dt.timezone.utc
SOURCES = {
    'btcnodes': ('https://btcnodes.io/api/v1/snapshots/latest/', 'Winnow input source; shared endpoint data. BTCNodes and Bitnod.es link to related crawler software; observation independence is unconfirmed.'),
    'bitnodes': ('https://www.bitnod.es/', 'Separate published dashboard; shared Bitnodes crawler lineage, upstream observation independence unconfirmed.'),
    '21ninja': ('https://raw.githubusercontent.com/virtu/p2p-metrics/master/p2p_reachable_node_count.csv', 'Independent crawler implementation (virtu/p2p-crawler); discovery upstream may overlap.'),
    '21ninja_services': ('https://raw.githubusercontent.com/virtu/p2p-metrics/master/p2p_reachable_node_service_count.csv', 'Same 21 Ninja observation series; not another independent source.'),
    'coindance': ('https://coin.dance/nodes', 'Separate dashboard; implementation and upstream observation independence unconfirmed.'),
}
MAX_BYTES = 24 * 1024 * 1024

def now(): return dt.datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')
def sha(data): return hashlib.sha256(data).hexdigest()
def write(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def revision():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[1], text=True).strip()
def timestamp(value):
    if not value: return None
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=UTC)
def integer(value):
    try: return int(value.replace(',', '')) if isinstance(value, str) else int(value)
    except (ValueError, TypeError): return None

def endpoint(text):
    host, port = text.rsplit(':', 1)
    host = host.strip('[]').lower()
    try:
        address = ipaddress.ip_address(host)
        host = str(address.ipv4_mapped or address) if isinstance(address, ipaddress.IPv6Address) else str(address)
    except ValueError: pass
    port = int(port)
    if not 0 < port < 65536 or not host: raise ValueError('invalid endpoint')
    return f'[{host}]:{port}' if ':' in host else f'{host}:{port}'

def overlay(text):
    host = text.rsplit(':', 1)[0].strip('[]').lower()
    if host.endswith('.onion'): return 'tor'
    if host.endswith('.i2p'): return 'i2p'
    try:
        ip = ipaddress.ip_address(host)
        if isinstance(ip, ipaddress.IPv6Address) and ip in ipaddress.ip_network('fc00::/8'): return 'cjdns'
        return 'ipv4' if ip.version == 4 or ip.ipv4_mapped else 'ipv6'
    except ValueError: return 'unknown'

def family(ua):
    ua = ua or ''
    if 'Knots' in ua: return 'Knots'
    if ua.startswith('/Satoshi:'): return 'Core'
    if 'btcd' in ua: return 'btcd'
    if 'bcoin' in ua: return 'bcoin'
    return 'other'

def population(endpoints): return dict(collections.Counter(overlay(e) for e in endpoints))

class Tables(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.tables = []; self.rows = []; self.row = []; self.cell = None
    def handle_starttag(self, tag, attrs):
        if tag == 'table': self.rows = []
        if tag == 'tr': self.row = []
        if tag in ('td', 'th'): self.cell = ''
    def handle_data(self, data):
        if self.cell is not None: self.cell += data
    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None: self.row.append(self.cell.strip()); self.cell = None
        if tag == 'tr' and self.row: self.rows.append(self.row)
        if tag == 'table': self.tables.append(self.rows)

def normalize(name, raw, evidence):
    result = {'source': name, 'url': evidence['url'], 'inputSHA256': evidence['sha256'],
              'retrievedAt': evidence['retrievedAt'], 'independence': evidence['independence'],
              'observationStart': None, 'observationEnd': None, 'stages': {}, 'overlays': {},
              'software': None, 'endpoints': None, 'limitations': []}
    if name == 'btcnodes':
        data = json.loads(raw)
        nodes = {endpoint(k): v for k, v in data['nodes'].items()}
        observed = dt.datetime.fromtimestamp(data['timestamp'], UTC).isoformat().replace('+00:00', 'Z')
        result.update(observationStart=observed, observationEnd=observed, endpoints=sorted(nodes),
                      overlays=population(nodes), software=dict(collections.Counter(family(v[1]) for v in nodes.values())))
        result['stages'] = {'reachable': len(nodes), 'advertisedCompactFilters': sum(bool(int(v[3]) & 64) for v in nodes.values())}
        result['versionEndpoints'] = sorted(nodes)
        result['compactFilterEndpoints'] = sorted(k for k, v in nodes.items() if int(v[3]) & 64)
        result['definition'] = 'Reachable endpoint snapshot (address and port), with advertised version service bits.'
        result['limitations'].append('Snapshot timestamp is available; complete scan start/end and retry window may differ. Advertised services do not prove filter responses.')
    elif name == 'bitnodes':
        parser = Tables(); parser.feed(raw.decode())
        for table in parser.tables:
            if not table: continue
            heading = table[0][0]
            if heading == 'Protocol Type':
                result['overlays'] = {r[0].lower(): integer(r[1]) for r in table[1:] if r[0] != 'Total'}
                result['stages']['retainedReachable'] = next(integer(r[1]) for r in table if r[0] == 'Total')
            if heading == 'Service (Bit)':
                result['stages']['advertisedCompactFilters'] = next((integer(r[1]) for r in table if r[0].startswith('NODE_COMPACT_FILTERS ')), None)
        if not result['stages'].get('retainedReachable'): raise ValueError('Unrecognized Bitnod.es protocol table')
        result['definition'] = 'Endpoint dashboard retaining unresponsive endpoints for eight days; discovery hourly.'
        result['limitations'] += ['Exact observation window unavailable. No endpoint export captured.', 'Displayed protocol coverage is IPv4, IPv6 and Tor; I2P measurement unavailable.', 'Software table includes grouped rows; no unverified summation of overlapping groups.']
    elif name.startswith('21ninja'):
        rows = list(csv.DictReader(io.StringIO(raw.decode())))
        row = max(rows, key=lambda r: r['time'])
        day = row['time'][:10]
        result.update(observationStart=day+'T00:00:00Z', observationEnd=day+'T23:59:59Z')
        result['definition'] = 'Daily reachable endpoints measured by 21 Ninja p2p-crawler; date-only observation window.'
        if name == '21ninja':
            result['stages'] = {'reachable': integer(row['total'])}
            result['overlays'] = {k: integer(row[k]) for k in ['ipv4', 'ipv6', 'torv2', 'torv3', 'i2p', 'cjdns'] if k in row}
        else: result['stages'] = {'advertisedCompactFilters': integer(row.get('node_compact_filters'))}
        result['limitations'].append('Latest available CSV row may be historical. No endpoint list or successful filter-response metric in this series.')
    elif name == 'coindance':
        page = raw.decode()
        match = re.search(r'There are currently\s*<strong[^>]*>([\d,]+)</strong>\*? public nodes', page)
        if not match: raise ValueError('Unrecognized Coin Dance headline')
        result['stages'] = {'reachableAddresses': integer(match[1])}
        matches = re.findall(r'class="nodeTitle"><strong[^>]*>([\d,]+)</strong>\s*([^<]+) nodes', page)
        result['software'] = {name.removeprefix('Bitcoin '): integer(count) for count, name in matches} or None
        result['definition'] = 'Public listening nodes deduplicated by address, rather than address and port.'
        age = re.search(r'Last updated\s*<strong>([^<]+)</strong>', page)
        result['displayedFreshness'] = age[1] if age else None
        result['limitations'] += ['Exact scan window and overlay coverage unavailable; relative page freshness is not a precise scan timestamp.', 'No endpoint export captured. Address-deduplicated denominator differs from Winnow.']
    elif name == 'winnow':
        data = json.loads(raw)
        result.update(observationStart=data.get('generatedAt'), observationEnd=data.get('observationEndedAt'), software=data.get('wholeNetworkFamilies'))
        result['stages'] = {'attempted': data['dialled'], 'versionResponses': data['outcomes'].get('ok', 0)+data['outcomes'].get('noCompactFilters', 0),
                            'successfulWinnowHandshakes': data['usable'], 'nearTipCandidatesBeforeDiversity': sum(n['atTip'] for n in data.get('networks', {}).values()) if data.get('completeRun') else None}
        result['overlays'] = {k: v['dialled'] for k, v in data.get('networks', {}).items()}
        result['definition'] = 'New Winnow attempts against supported BTCNodes input endpoints. Version responses and successful compact-filter handshakes are distinct stages.'
        result['acceptedFullRun'] = data.get('completeRun') is True
        if not result['acceptedFullRun']: result['limitations'].append('Legacy or diagnostic artifact lacks full-run contract provenance; near-tip comparison unavailable.')
        result['limitations'].append('No successful compact-filter response test in the census handshake.')
    return result

def capture(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    if (out/'manifest.json').exists(): raise ValueError('Choose a new evidence directory; snapshots are immutable')
    specs = dict(SOURCES)
    if args.winnow_summary: specs['winnow'] = ('https://census.winnowwallet.com/census/'+Path(args.winnow_summary).name, 'Winnow observation, with BTCNodes input endpoints.')
    if args.winnow_records: specs['winnow_records'] = ('https://github.com/winnowwallet/census/actions/workflows/peer-census.yml', 'Raw observations from the same Winnow full run.')
    manifest = {'schemaVersion': 1, 'capturedAt': now(), 'processingRevision': revision(), 'toolSHA256': sha(Path(__file__).read_bytes()), 'sources': {}}
    for name, (url, independence) in specs.items():
        entry = dict(url=url, independence=independence, retrievedAt=now())
        try:
            local = {'btcnodes': args.btcnodes, 'winnow': args.winnow_summary, 'winnow_records': args.winnow_records}.get(name)
            if local:
                raw = Path(local).read_bytes(); entry['retrievalKind'] = 'local preserved run artifact; original retrieval time not asserted'
            else:
                request = urllib.request.Request(url, headers={'User-Agent': 'Winnow census comparison (+https://github.com/winnowwallet/census)'})
                with urllib.request.urlopen(request, timeout=60) as response:
                    raw = response.read(MAX_BYTES + 1); entry['finalURL'] = response.url
                    entry['etag'] = response.headers.get('ETag'); entry['lastModified'] = response.headers.get('Last-Modified')
            if len(raw) > MAX_BYTES: raise ValueError('Oversized source')
            entry.update(sha256=sha(raw), file=name+'.gz', status='captured')
            (out/entry['file']).write_bytes(gzip.compress(raw, mtime=0))
        except Exception as error: entry.update(status='unavailable', error=str(error))
        manifest['sources'][name] = entry
    write(out/'manifest.json', manifest)
    compare(out)

def comparison(winnow, source, max_hours=6):
    a, b = timestamp(winnow.get('observationStart')), timestamp(source.get('observationStart'))
    delta = abs((a-b).total_seconds()) if a and b else None
    result = {'source': source['source'], 'timestampDifferenceSeconds': delta,
              'status': 'inconclusive', 'countDifference': None, 'percentagePointDifference': None,
              'reason': 'Definitions, denominators or observation windows are not matched.'}
    if delta is None: result['reason'] = 'Exact observation window unavailable; no comparable percentage calculated.'
    elif delta > max_hours*3600: result['reason'] = 'Observation windows exceed the configured six-hour proximity bound; no confirmation claimed.'
    if source['source'] == 'btcnodes':
        result['reason'] += ' BTCNodes is the input source, so agreement is not independent confirmation.'
    left, right = winnow.get('endpoints'), source.get('endpoints')
    if left is not None and right is not None:
        aa, bb = set(left), set(right)
        result['endpointOverlap'] = {'definition': 'All Winnow attempted address:port endpoints versus source snapshot endpoints; not two independent reachable sets.',
                                     'intersection': len(aa & bb), 'winnowOnly': sorted(aa-bb), 'sourceOnly': sorted(bb-aa)}
    # This is a deliberately narrower population than a whole-network count:
    # exactly the endpoints that returned a version in both observations.
    required = ['versionEndpoints', 'compactFilterEndpoints']
    if delta is not None and delta <= max_hours*3600 and all(k in s for k in required for s in [winnow, source]):
        denominator = set(winnow['versionEndpoints']) & set(source['versionEndpoints'])
        if denominator:
            own = len(set(winnow['compactFilterEndpoints']) & denominator)
            other = len(set(source['compactFilterEndpoints']) & denominator)
            result.update(status='descriptive matched-population comparison',
                          countDifference=own-other, percentagePointDifference=100*(own-other)/len(denominator),
                          comparedMetric='Advertised NODE_COMPACT_FILTERS among matched version-responding address:port endpoints',
                          denominator=len(denominator), winnowCount=own, sourceCount=other,
                          reason='Both counts use the same endpoint denominator; differences remain subject to scan timing. Service advertisements do not prove filter responses.')
            if source['source'] == 'btcnodes': result['reason'] += ' Shared input source; not independent confirmation.'
    return result

def compare(out):
    manifest = json.loads((out/'manifest.json').read_text())
    if manifest['schemaVersion'] != 1: raise ValueError('Unknown evidence schema')
    normalized = {}; raw_records = None
    for name, entry in manifest['sources'].items():
        if entry['status'] != 'captured':
            normalized[name] = {'source': name, 'status': 'unavailable', 'reason': entry.get('error')}; continue
        try:
            raw = gzip.decompress((out/entry['file']).read_bytes())
            if sha(raw) != entry['sha256']: raise ValueError('Evidence hash mismatch')
            if name == 'winnow_records': raw_records = [json.loads(line) for line in raw.splitlines() if line]; continue
            normalized[name] = normalize(name, raw, entry)
        except Exception as error: normalized[name] = {'source': name, 'status': 'unavailable', 'reason': str(error)}
    winnow = normalized.get('winnow', {'source': 'winnow', 'status': 'unavailable'})
    if raw_records is not None and 'stages' in winnow:
        summary = json.loads(gzip.decompress((out/manifest['sources']['winnow']['file']).read_bytes()))
        raw_hash = manifest['sources']['winnow_records']['sha256']
        if summary.get('recordsSHA256') != raw_hash: raise ValueError('Raw records do not match the summary hash')
        winnow['endpoints'] = sorted({endpoint(f"{r['host']}:{r['port']}") for r in raw_records})
        winnow['overlays'] = population(winnow['endpoints'])
        responders = [r for r in raw_records if r.get('services') is not None and r.get('userAgent') is not None]
        winnow['versionEndpoints'] = sorted({endpoint(f"{r['host']}:{r['port']}") for r in responders})
        winnow['compactFilterEndpoints'] = sorted({endpoint(f"{r['host']}:{r['port']}") for r in responders if int(r['services']) & 64})
    comparisons = [comparison(winnow, s) for name, s in normalized.items() if name not in ['winnow', '21ninja_services'] and 'stages' in s]
    report = {'schemaVersion': 1, 'manifestSHA256': sha((out/'manifest.json').read_bytes()), 'processingRevision': revision(),
              'toolSHA256': sha(Path(__file__).read_bytes()), 'sources': normalized, 'comparisons': comparisons,
              'limitations': ['Count and percentage differences remain null where definitions or denominators are unmatched.', 'Missing sources do not block the production census pipeline.', 'Similar totals do not establish measurement correctness.']}
    write(out/'report.json', report)
    lines = ['# Preserved cross-census observations', '', 'Evidence captured: '+manifest['capturedAt'], '', '| Source | Observation window | Definition | Results | Independence |', '|---|---|---|---|---|']
    for name, s in normalized.items():
        def cell(value): return str(value).replace('|', '\\|').replace('\n', ' ')
        values = [name, (s.get('observationStart') or 'Unavailable')+' — '+(s.get('observationEnd') or 'Unavailable'), s.get('definition', s.get('reason')), json.dumps(s.get('stages', {}), sort_keys=True), s.get('independence', 'Unavailable')]
        lines.append('| '+' | '.join(cell(v) for v in values)+' |')
    lines += ['', '## Comparison limits', ''] + ['- '+c['source']+': '+c['reason'] for c in comparisons]
    lines += ['', 'Replay: `python3 scripts/census_compare.py compare '+str(out)+'`.', 'Raw source snapshots, hashes, URLs and retrieval details are in this directory. No private correspondence is included.', '']
    (out/'report.md').write_text('\n'.join(lines))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    cap = commands.add_parser('capture'); cap.add_argument('--out', required=True)
    cap.add_argument('--btcnodes'); cap.add_argument('--winnow-summary'); cap.add_argument('--winnow-records')
    replay = commands.add_parser('compare'); replay.add_argument('directory')
    args = parser.parse_args()
    if args.command == 'capture': capture(args)
    else: compare(Path(args.directory))
