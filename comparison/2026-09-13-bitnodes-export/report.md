# Preserved cross-census observations

Evidence captured: 2026-09-13T17:57:08.161481+00:00

| Source | Observation window | Definition | Results | Independence |
|---|---|---|---|---|
| 21ninja | 2025-11-04T00:00:00Z — 2025-11-04T23:59:59Z | Daily reachable endpoints measured by 21 Ninja p2p-crawler; date-only observation window. | {"reachable": 34943} | Independent crawler implementation (virtu/p2p-crawler); discovery upstream may overlap. |
| 21ninja_seeds | Unavailable — Unavailable | Retained seed-export records with per-endpoint last-success times and exporter good flags; not a simultaneous reachable census. | {"exportGoodFlag": 25239, "retainedAdvertisedCompactFilters": 14373, "retainedSeedEndpoints": 66162} | 21 Ninja seed export; same project as the CSV series, not an additional independent observer. |
| 21ninja_services | 2025-11-04T00:00:00Z — 2025-11-04T23:59:59Z | Daily reachable endpoints measured by 21 Ninja p2p-crawler; date-only observation window. | {"advertisedCompactFilters": 8236} | Same 21 Ninja observation series; not another independent source. |
| bitnodes | Unavailable — Unavailable | Address-deduplicated active dashboard; excludes nodes last connected nine or more UTC calendar days ago. | {"advertisedCompactFilters": 6377, "retainedReachable": 26170} | Maintainer confirms own measurements using shared ayeowch/bitnodes crawler; discovery inputs may overlap. |
| bitnodes_export | Unavailable — Unavailable | Public dated CSV containing retained address:port rows with mixed export_date values; not a simultaneous reachable population. | {"retainedAdvertisedCompactFilters": 13501, "retainedExportEndpoints": 54187} | Maintainer confirms own measurements using shared ayeowch/bitnodes crawler; discovery inputs may overlap. Same project as dashboard, not another independent source. |
| btcnodes | 2026-09-13T14:53:18Z — 2026-09-13T14:53:18Z | Reachable endpoint snapshot (address and port), with advertised version service bits. | {"advertisedCompactFilters": 8376, "reachable": 26695} | Winnow input source; shared endpoint data. BTCNodes and Bitnod.es link to related crawler software; observation independence is unconfirmed. |
| coindance | Unavailable — Unavailable | Public listening nodes deduplicated by address, rather than address and port. | {"reachableAddresses": 25896} | Separate dashboard; implementation and upstream observation independence unconfirmed. |
| winnow | 2026-09-13T15:28:48Z — 2026-09-13T16:29:42Z | New Winnow attempts against supported BTCNodes input endpoints. Version responses and successful compact-filter handshakes are distinct stages. | {"attempted": 26691, "nearTipCandidatesBeforeDiversity": 6831, "successfulWinnowHandshakes": 7524, "versionResponses": 23061} | Winnow observation, with BTCNodes input endpoints. |

## Comparison limits

- 21ninja: Observation windows exceed the configured six-hour proximity bound; no confirmation claimed.
- 21ninja_seeds: Exact observation window unavailable; no comparable percentage calculated.
- bitnodes: Exact observation window unavailable; no comparable percentage calculated.
- bitnodes_export: Exact observation window unavailable; no comparable percentage calculated.
- btcnodes: Both counts use the same endpoint denominator; differences remain subject to scan timing. Service advertisements do not prove filter responses. Shared input source; not independent confirmation.
- coindance: Exact observation window unavailable; no comparable percentage calculated.

Replay: `python3 scripts/census_compare.py compare comparison/2026-09-13-bitnodes-export`.
Raw source snapshots, hashes, URLs and retrieval details are in this directory. No private correspondence is included.
