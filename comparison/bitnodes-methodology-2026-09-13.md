# Bitnod.es methodology clarification

Jonathan Bier replied to Winnow's inquiry on September 13, 2026 at 17:29 UTC,
then explicitly permitted use of the reply's information at 17:59 UTC. This
is an attributed paraphrase, not a publication of the email or its signature.

- Bitnod.es makes its own measurements using [ayeowch/bitnodes](https://github.com/ayeowch/bitnodes).
  This establishes separately operated observations using shared crawler
  software. It does not establish disjoint discovery inputs or an independent
  implementation.
- The crawler runs continuously. A cycle takes roughly four to six hours.
  This duration is not an exact observation window for our captured dashboard.
- A node whose last successful connection was nine or more calendar days ago
  is excluded from the active population. The daily boundary is midnight UTC.
- Uniqueness is by address, rather than address and port. IPv4, IPv6 and Tor
  addresses are represented; multiple addresses belonging to one machine are
  not deduplicated into a single physical node.
- I2P is not measured.
- Compact-filter support is not tested with filter requests. A service
  advertisement must not be described as a validated filter response.
- Daily CSVs are published through the [node explorer](https://www.bitnod.es/node_explorer.php).
  The approximate export time was given tentatively as 02:00 UTC; we do not
  promote that estimate into an exact observation timestamp.

In the same attributed follow-up, Jonathan clarified at 18:10 UTC that each
CSV row's `export_date` is its last connection date. The September 13 export
contains 54,187 retained addresses, with last-connection dates from May 23
through September 13. Applying the active rule for the September 13 reference
day keeps September 5–13 inclusive: 25,820 addresses, of which 6,283 advertise
compact filters. The later dashboard capture had 26,170 addresses and 6,377
advertisements, differences of −350 and −94 respectively. These are descriptive
same-project snapshot differences, not matched-window validation. Exact scan
windows and export time remain unavailable. The filename selects the reference
day for this calculation; it does not become an observation timestamp.
See the [preserved export comparison](2026-09-13-bitnodes-export/README.md).

Older captured reports retain the independence information available at capture
time. This dated clarification supersedes their unanswered methodology labels;
it does not change their raw snapshots, measured counts or unmatched windows.
This response is not an endorsement of Winnow's measurements.
