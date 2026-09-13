import Darwin
import Foundation

/// The permanent per-node artifact: `census/peers.json`, a wallet-grade
/// verified peer list the wallet repo consumes at release time to render its
/// bundled fallback peers. Derived from one run's JSON lines; the schema is a
/// contract with another repository and must not drift.
struct PeerEntry: Codable, Equatable {
    var host: String
    var port: UInt16
    var userAgent: String
    var startHeight: Int32
}

struct PeerList: Codable {
    struct Networks: Codable {
        var clearnet: [PeerEntry]
        var tor: [PeerEntry]
        var i2p: [PeerEntry]
    }
    var schemaVersion: Int
    var date: String
    var tip: Int32
    var networks: Networks
}

/// The overlays are capped so a flood of one-off hidden services cannot make
/// the artifact unbounded; the survivors are the quickest to answer.
let peerListOverlayCap = 2_000

/// The census's own at-tip rule, both directions: "behind" and "ahead of tip"
/// (a peer on another chain claims thousands more blocks) share the 100-block
/// margin the snapshot accumulates over an hour-long dial.
func atTip(_ record: Record, tip: Int32) -> Bool {
    guard let height = record.startHeight else { return false }
    return abs(height - tip) <= 100
}

private func ipv4Bytes(_ host: String) -> [UInt8]? {
    var addr = in_addr()
    guard host.withCString({ inet_pton(AF_INET, $0, &addr) }) == 1 else { return nil }
    return withUnsafeBytes(of: &addr) { Array($0) }
}

private func ipv6Bytes(_ host: String) -> [UInt8]? {
    var addr = in6_addr()
    guard host.withCString({ inet_pton(AF_INET6, $0, &addr) }) == 1 else { return nil }
    return withUnsafeBytes(of: &addr) { Array($0) }
}

private func isPublicIPv4(_ b: [UInt8]) -> Bool {
    switch b[0] {
    case 0, 10, 127: return false                    // "this net", private, loopback
    case 100: return b[1] & 0xC0 != 64               // CGNAT 100.64/10
    case 169: return b[1] != 254                     // link-local
    case 172: return b[1] & 0xF0 != 16               // private 172.16/12
    case 192:
        if b[1] == 168 { return false }              // private
        if b[1] == 0, b[2] == 0 || b[2] == 2 { return false } // IETF protocol assignments, TEST-NET-1
        return true
    case 198:
        if b[1] & 0xFE == 18 { return false }        // benchmarking 198.18/15
        if b[1] == 51, b[2] == 100 { return false }  // TEST-NET-2
        return true
    case 203: return !(b[1] == 0 && b[2] == 113)     // TEST-NET-3
    case 224...255: return false                     // multicast + reserved
    default: return true
    }
}

private func isPublicIPv6(_ b: [UInt8]) -> Bool {
    if b.allSatisfy({ $0 == 0 }) { return false }                       // unspecified
    if b.dropLast().allSatisfy({ $0 == 0 }), b[15] == 1 { return false } // loopback ::1
    if b[0] == 0xFF { return false }                                     // multicast
    if b[0] & 0xFE == 0xFC { return false }                              // unique local fc00/7
    if b[0] == 0xFE, b[1] & 0xC0 == 0x80 { return false }                // link-local fe80/10
    if b[0] == 0x20, b[1] == 0x01, b[2] == 0x0D, b[3] == 0xB8 { return false } // documentation
    if b.prefix(10).allSatisfy({ $0 == 0 }), b[10] == 0xFF, b[11] == 0xFF {
        return isPublicIPv4(Array(b.suffix(4)))                          // v4-mapped
    }
    return true
}

/// Clearnet entries are IP literals the wallet can dial without DNS; names
/// are for the overlays, where they are the address.
func isPublicIPLiteral(_ host: String) -> Bool {
    if let v4 = ipv4Bytes(host) { return isPublicIPv4(v4) }
    if let v6 = ipv6Bytes(host) { return isPublicIPv6(v6) }
    return false
}

/// The spread rule the wallet's PeerPolicyTests enforce: at most one peer per
/// IPv4 /16 (or IPv6 /32), so the fallback list cannot be one netblock's
/// opinion of the network. Returns nil for non-literals.
func netblock(_ host: String) -> String? {
    if let v4 = ipv4Bytes(host) { return "v4:\(v4[0]).\(v4[1])" }
    if let v6 = ipv6Bytes(host) {
        return "v6:" + v6.prefix(4).map { String(format: "%02x", $0) }.joined()
    }
    return nil
}

private func entry(_ record: Record) -> PeerEntry? {
    guard let userAgent = record.userAgent, let startHeight = record.startHeight else { return nil }
    return PeerEntry(host: record.host, port: record.port, userAgent: userAgent, startHeight: startHeight)
}

private func byHostPort(_ a: PeerEntry, _ b: PeerEntry) -> Bool {
    a.host == b.host ? a.port < b.port : a.host < b.host
}

/// Keeps the quickest `limit` records; deterministic on equal latency.
private func cappedByLatency(_ records: [Record], limit: Int) -> [Record] {
    guard records.count > limit else { return records }
    return Array(records
        .sorted { ($0.latencyMs, $0.host, $0.port) < ($1.latencyMs, $1.host, $1.port) }
        .prefix(limit))
}

/// Filters one run's records into the artifact. Clearnet must satisfy the
/// wallet's fallback-peer invariants (public IP literal, port 8333, one per
/// netblock); the overlays keep hostnames and any port, capped at
/// `peerListOverlayCap` each by handshake latency. Only outcome "ok" counts:
/// the handshake succeeded and the peer advertised NODE_COMPACT_FILTERS.
func makePeerList(_ records: [Record], tip: Int32, date: String) -> PeerList {
    let usable = records.filter { $0.outcome == "ok" && atTip($0, tip: tip) }
    var clearnet: [PeerEntry] = []
    var tor: [Record] = []
    var i2p: [Record] = []
    var claimedBlocks: Set<String> = []
    for record in usable.sorted(by: { ($0.host, $0.port) < ($1.host, $1.port) }) {
        switch OverlayNetwork(host: record.host) {
        case .clearnet:
            guard record.port == 8333, isPublicIPLiteral(record.host),
                  let block = netblock(record.host), claimedBlocks.insert(block).inserted,
                  let peer = entry(record) else { continue }
            clearnet.append(peer)
        case .tor: tor.append(record)
        case .i2p: i2p.append(record)
        }
    }
    return PeerList(
        schemaVersion: 1, date: date, tip: tip,
        networks: PeerList.Networks(
            clearnet: clearnet.sorted(by: byHostPort),
            tor: cappedByLatency(tor, limit: peerListOverlayCap).compactMap(entry).sorted(by: byHostPort),
            i2p: cappedByLatency(i2p, limit: peerListOverlayCap).compactMap(entry).sorted(by: byHostPort)))
}

func writePeerList(_ records: [Record], tip: Int32, to url: URL) throws -> PeerList {
    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd"
    formatter.timeZone = TimeZone(identifier: "UTC")
    formatter.locale = Locale(identifier: "en_US_POSIX")
    let list = makePeerList(records, tip: tip, date: formatter.string(from: Date()))
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    try encoder.encode(list).write(to: url)
    return list
}
