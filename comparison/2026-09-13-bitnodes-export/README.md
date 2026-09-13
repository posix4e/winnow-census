# Supplementary public Bitnod.es export

The September 13 CSV contains 54,187 distinct address:port rows: 24,484 IPv4,
6,983 IPv6 and 22,720 Tor. 13,501 rows advertise compact-filter service bit 64.
These are retained export records, not a fresh reachable-node count. The rows
have mixed `export_date` values; their meaning is not inferred from the filename.
No guessed eight-day cutoff is applied.

Against Winnow’s 26,691 full-run attempted endpoints, 21,310 overlap, 5,381
appear only in Winnow’s attempted set and 32,877 only in this retained export.
The exact lists are in `report.json`. The unmatched observation windows and
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
