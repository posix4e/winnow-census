# A full run that did not publish

The [full run ending September 14](https://github.com/winnowwallet/census/actions/runs/34788082855)
attempted all 26,856 supported endpoints in its BTCNodes input. Publication was
refused because the Tor response rate was **40.45%**, below the existing 50%
per-overlay floor. The previous accepted catalog and aggregate stayed live;
their downloaded bytes were checked against the recorded SHA256 hashes.

The guard counts a completed compact-filter-capable handshake or a version
response that lacks the compact-filter bit. The table therefore calls these
**version responders**. Neither outcome verifies returned compact filters.

| Overlay | Earlier accepted run: responders / attempted | Later rejected run: responders / attempted | Difference |
|---|---:|---:|---:|
| Clearnet | 8,279 / 9,721 (85.1661%) | 8,307 / 9,752 (85.1825%) | +0.0164 percentage points |
| Tor | 10,610 / 12,694 (83.5828%) | 5,161 / 12,759 (40.4499%) | −43.1329 percentage points |
| I2P | 4,172 / 4,276 (97.5678%) | 4,271 / 4,345 (98.2969%) | +0.7291 percentage points |

These are fractions of each run's own attempted endpoints, at different times.
The endpoint sets and observation windows do not match exactly. The differences
describe the observations; they are not estimates of a change in Bitcoin-wide
availability or proof that the nodes themselves became unhealthy.

- Earlier accepted window: September 13, 15:28:48–16:29:42 UTC.
- Rejected window: September 13, 23:05:40–September 14, 00:45:46 UTC.
- Rejected input snapshot: BTCNodes timestamp `1789338358`, retrieved within
  22:53:13–22:53:15 UTC on September 13. The original compressed input and hash
  are preserved here. Four CJDNS endpoints are unsupported and were not attempted.

Tor stayed running throughout. Of its 7,546 timeouts, 7,519 completed between
30 and 35 seconds. The fraction of responders stayed low throughout the run;
this was not a single late collapse. Three Tor warnings about unknown requested
exit points do not explain the thousands of timeouts. The full logs are retained
in the linked workflow and local release evidence.

## Bounded follow-up

We selected 32 Tor endpoints that answered in the earlier run and timed out in
the rejected run, plus 16 endpoints that answered in both. Within each group,
selection uses the lowest SHA256 hashes of `host:port`; it is reproducible from
the preserved raw records. It is a deliberately selected diagnostic cohort,
not a random network sample.

The final census binary probed those 48 endpoints on September 14,
00:52:11–00:53:27 UTC, through a fresh local Tor client. **27 of the 32 earlier
timeouts answered, and 15 of 16 controls answered.** The hidden-service timeout
remained 30 seconds; concurrency was eight rather than the hosted run's 48.
The diagnostic is marked `sample=48`, `completeRun=false` and cannot publish.

The observations show that many failed endpoints could answer the final binary
under later conditions. Timing, observer location, Tor paths and concurrency all
changed, so they do not identify the cause of the hosted failure. No publication
threshold was lowered, and no diagnostic response was inserted into production
data. These are related Winnow observations, not independent implementations.

## Reproduce the calculations

From the census repository root:

```sh
python3 comparison/2026-09-14-publication-guard/reproduce.py --check
python3 comparison/2026-09-14-publication-guard/reproduce.py > /tmp/publication-report.json
```

The script checks source hashes, raw counts against both full-run aggregates,
the deterministic cohort, and the saved report. The earlier accepted raw data
is reused from its immutable hash-named `health-evidence/runs/` archive. The
rejected full run's records and upstream input are compressed here, alongside
the diagnostic records. `metadata.json` records run URLs, source revisions,
retrieval bounds, policy parameters and the diagnostic binary hash.

To repeat the selected network measurement with a separately bootstrapped Tor
client listening on loopback port 19050, use the pinned census build:

```sh
.build/release/WinnowCensus \
  --input comparison/2026-09-14-publication-guard/nodes.txt \
  --sample 48 --tor-socks 127.0.0.1:19050 --tor-parallel 8 \
  --hidden-timeout 30 --tip 966878 \
  --out /tmp/publication-diagnostic.jsonl \
  --summary-json /tmp/publication-diagnostic-summary.json
```

That command intentionally retains the original reference tip to reproduce the
recorded diagnostic policy. A later availability check needs its own observation
time and reference tip; do not interpret the old tip as today's chain state.
The source revisions and SHA256 hashes identify this evidence even when later
production runs update the live website.
