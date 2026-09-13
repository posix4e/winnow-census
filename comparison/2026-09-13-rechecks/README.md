# Bounded discrepancy checks — September 13, 2026

The accepted full run and BTCNodes input disagree on advertised compact-filter support at two of their 23,061 shared version-responding endpoints. The difference is **−2 endpoints, −0.0086726508 percentage points**, measured on that identical denominator. It is not independent confirmation: BTCNodes supplied Winnow's discovery input.

The four input endpoints omitted by Winnow are `fc00::/8` CJDNS addresses, an unsupported transport. All 26,691 supported input endpoints were attempted. The 3,630 endpoints without version responses remain failures at Winnow's observation times; no values are imputed from BTCNodes.

## Tor discrepancy

`6uhpsosiekl3a24kw6swl7s5epno7xzncp572lawwz2wwmtee4zxekqd.onion:8333`

- BTCNodes snapshot at 14:53:18 UTC: `/Satoshi:29.1.0/`, services 3145 (compact-filter bit present).
- Winnow at 15:29:38 UTC: `/Satoshi:29.3.0/`, services 3081 (bit absent), reported height 966837.
- First bounded recheck at 16:33 UTC: both target and prior-good control failed at the proxy; that batch cannot establish endpoint unavailability.
- Second recheck at 16:37:39 UTC: target returned `/Satoshi:29.3.0/`, services 3081, height 966846. The separate control failed. The target's actual response reproduces Winnow's service-bit observation, while the control failure limits any network-health inference.

## I2P discrepancy

`wnwudbb63q67t37w75olmdewxecxnairqsxyo3lyhn6u6sz5j65a.b32.i2p:8333`

- BTCNodes snapshot: `/Satoshi:31.1.0(21m node)/`, services 3145, height 966829.
- Winnow at 15:30:53 UTC: `/Satoshi:29.4.1/Knots:20260508/`, services 268438537 (compact-filter bit absent), height 971869.
- Recheck at 16:37:34 UTC: `/Satoshi:31.1.0(21m node)/`, services 3145, height 966846. A separate prior-good I2P control also completed its compact-filter-capable handshake.

The local I2P router reported 42% tunnel creation success and 244 known routers shortly before this diagnostic batch; these diagnostics are not a production full run. Different user agents and service flags were observed at the same destination. Timing, endpoint configuration, or routing behavior may explain it; these records alone do not distinguish the cause. Inspection of Winnow's probe confirms it creates a separate connection and captures its metadata per endpoint. No demonstrated Winnow defect warrants changing the accepted run or selection policy.

These are version/service checks, not validation of returned compact filters. Raw responses, timestamps and hashes are preserved alongside this note. Failed probes and unresolved causes are retained. No private correspondence is included.
