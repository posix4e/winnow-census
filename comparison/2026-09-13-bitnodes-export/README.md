# Supplementary public Bitnod.es export

The September 13 CSV contains 54,187 distinct address:port rows: 24,484 IPv4,
6,983 IPv6 and 22,720 Tor. 13,501 rows advertise compact-filter service bit 64.
These are retained export records, not a fresh reachable-node count. The rows have mixed `export_date` values. The maintainer later clarified, in
the permitted attributed correspondence, that these are last-connection dates.
For the September 13 reference day, the published retention rule keeps September
5–13 inclusive: 25,820 addresses, including 6,283 compact-filter advertisements.
The separately captured dashboard has 26,170 addresses and 6,377 advertisements,
so the descriptive export-minus-dashboard differences are −350 and −94. Exact
scan windows remain unmatched and no percentage-point comparison is calculated.
See [the dated methodology clarification](../bitnodes-methodology-2026-09-13.md).

Against Winnow’s 26,691 full-run attempted endpoints, 21,310 overlap, 5,381
appear only in Winnow’s attempted set and 32,877 only in this retained export.
The exact lists, and a separately labeled retention-filtered overlap, are in `report.json`. The unmatched observation windows and
populations make reachability and service percentage comparisons inconclusive.
This export and the Bitnod.es dashboard count as one source, not two.

The manifest preserves the public URL, download completion timestamp and SHA256.
Earlier source evidence is referenced without modifying its original manifest.
Replay from the repository root:

```sh
python3 scripts/census_compare.py compare comparison/2026-09-13-bitnodes-export
```

For a future capture, pass `--bitnodes-export-url` with a public dated CSV URL.
No private correspondence is included.
