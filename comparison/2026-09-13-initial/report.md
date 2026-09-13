# Preserved cross-census observations

Evidence captured: 2026-09-13T15:05:42Z

| Source | Observation window | Definition | Results | Independence |
|---|---|---|---|---|
| 21ninja | 2025-11-04T00:00:00Z — 2025-11-04T23:59:59Z | Daily reachable endpoints measured by 21 Ninja p2p-crawler; date-only observation window. | {"reachable": 34943} | Independent crawler implementation (virtu/p2p-crawler); discovery upstream may overlap. |
| 21ninja_services | 2025-11-04T00:00:00Z — 2025-11-04T23:59:59Z | Daily reachable endpoints measured by 21 Ninja p2p-crawler; date-only observation window. | {"advertisedCompactFilters": 8236} | Same 21 Ninja observation series; not another independent source. |
| bitnodes | Unavailable — Unavailable | Endpoint dashboard retaining unresponsive endpoints for eight days; discovery hourly. | {"advertisedCompactFilters": 6375, "retainedReachable": 26154} | Separate published dashboard; shared Bitnodes crawler lineage, upstream observation independence unconfirmed. |
| btcnodes | 2026-09-13T14:30:02Z — 2026-09-13T14:30:02Z | Reachable endpoint snapshot (address and port), with advertised version service bits. | {"advertisedCompactFilters": 8387, "reachable": 26697} | Winnow input source; shared endpoint data. BTCNodes and Bitnod.es link to related crawler software; observation independence is unconfirmed. |
| coindance | Unavailable — Unavailable | Public listening nodes deduplicated by address, rather than address and port. | {"reachableAddresses": 25885} | Separate dashboard; implementation and upstream observation independence unconfirmed. |
| winnow | 2026-09-13T07:08:08Z — Unavailable | New Winnow attempts against supported BTCNodes input endpoints. Version responses and successful compact-filter handshakes are distinct stages. | {"attempted": 26139, "nearTipCandidatesBeforeDiversity": null, "successfulWinnowHandshakes": 6453, "versionResponses": 20361} | Winnow observation, with BTCNodes input endpoints. |

## Comparison limits

- 21ninja: Observation windows exceed the configured six-hour proximity bound; no confirmation claimed.
- bitnodes: Exact observation window unavailable; no comparable percentage calculated.
- btcnodes: Observation windows exceed the configured six-hour proximity bound; no confirmation claimed. BTCNodes is the input source, so agreement is not independent confirmation.
- coindance: Exact observation window unavailable; no comparable percentage calculated.

Replay: `python3 scripts/census_compare.py compare comparison/2026-09-13-initial`.
Raw source snapshots, hashes, URLs and retrieval details are in this directory. No private correspondence is included.
