# Winnow peer census

Every reachable Bitcoin endpoint, dialled daily with the same handshake the
[Winnow](https://github.com/posix4e/winnow) wallet uses, and published at
**https://census.winnowwallet.com/**.

A peer that fails Winnow's handshake, which requires `NODE_COMPACT_FILTERS`, is
one the wallet could never seat. So the numbers here describe a compact-filter
wallet's world, not the abstract network: how many endpoints serve filters at
all, how many of those are at the tip, how many are stuck on a dead chain, and
how many claim a chain that is not Bitcoin's.

## What is here

- `Sources/WinnowCensus` — the tool. Dials a node list (a btcnodes.io snapshot
  or a plain `host:port` file) with Winnow's `PeerConnection`, records what each
  peer reports in its handshake, waits a moment for the BIP133 fee filter, and
  disconnects. Read-only: version, verack, disconnect. Tor and I2P addresses go
  through local SOCKS5 proxies when `--tor-socks` / `--i2p-socks` are given,
  each overlay on its own queue with its own ceiling (`--parallel`,
  `--tor-parallel`, `--i2p-parallel`): a Tor client saturates, rather than
  queues, past a few dozen concurrent rendezvous.
- `scripts/census-publish` — files a run's summary under `census/<date>.json`
  and rebuilds `census/index.json`.
- `scripts/census-tables` — Markdown tables from a run's JSON lines, for a
  write-up.
- `.github/workflows/peer-census.yml` — the daily run on a GitHub-hosted macOS
  runner, which installs Tor and i2pd itself, commits the aggregate here, and
  deploys the site.
- `.github/workflows/site.yml` and `wrangler.jsonc` — deploy `index.html` and
  `census/` as a Cloudflare Worker with static assets on every push to main.
  The Worker's custom domain, census.winnowwallet.com, gets its DNS record and
  certificate from Cloudflare on deploy. Needs the `CF_API_TOKEN` and
  `CF_ACCOUNT_ID` secrets; see "Deploying" below.
- `index.html` — the page.
- `census/` — one aggregate per day. Per-node detail is a two-week workflow
  artifact; btcnodes already publishes the per-IP view.

## Run it yourself

```sh
curl -sL -A winnow-census -o snapshot.json https://btcnodes.io/api/v1/snapshots/latest/
swift run -c release WinnowCensus --input snapshot.json --sample 3000 --out census.jsonl
# with local routers: brew install tor i2pd, then
swift run -c release WinnowCensus --input snapshot.json \
    --tor-socks 127.0.0.1:9050 --i2p-socks 127.0.0.1:4447 \
    --tip "$(python3 -c 'import json;print(json.load(open("snapshot.json"))["latest_height"])')" \
    --out census.jsonl --summary-json summary.json
scripts/census-tables census.jsonl
```

## Reading the numbers

**Endpoints, not nodes.** One node can listen on clearnet, Tor and I2P at once,
and Bitcoin Core deliberately makes linking a node's addresses across networks
hard, so the census cannot tell how many endpoints are doors into the same node.
Distinct usable nodes lie somewhere between the clearnet count and the total.

**Heights are claims.** A `version.startHeight` is whatever the peer says. The
tool judges peers against the snapshot's `latest_height` (or the median of
what usable peers report) rather than any top percentile, because nodes on
other chains claim heights well above Bitcoin's.

The first run, 2026-09-04, and the stall in the wallet that prompted it, are
written up in [One in Twelve Peers Is on a Dead Chain](https://apnewman.com/p/dead-chain-peers/).
The tool began life as posix4e/winnow#176 and moved here so the wallet's
history never carries a daily data commit.

## Deploying

The site is a Cloudflare Worker that serves static assets; `wrangler deploy`
uploads `site/` and creates the custom domain. GitHub Actions does it on every
push to main and after every daily census. Two repository secrets are needed:

- `CF_ACCOUNT_ID` — the account ID, shown on the right of any zone's
  Overview page in the Cloudflare dashboard.
- `CF_API_TOKEN` — an API token made from the **Edit Cloudflare Workers**
  template (My Profile → API Tokens → Create Token), plus **Zone → DNS →
  Edit**, with **Zone Resources** set to include `winnowwallet.com` so the
  custom domain and its DNS record can be created. If a `census` DNS record
  already exists in the zone, delete it before the first deploy; wrangler will
  not overwrite one.

Nothing else is configured by hand: no DNS record, no Pages project.
