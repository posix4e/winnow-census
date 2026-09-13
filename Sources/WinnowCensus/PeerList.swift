import Foundation
import WalletCore

typealias PeerList = CensusCatalog
let peerListOverlayCap = CensusCatalog.overlayCap

func atTip(_ record: Record, tip: Int32) -> Bool {
    guard let height = record.startHeight else { return false }
    return CensusCatalog.nearTip(height, tip: tip)
}

/// Canonicalize before deduplication. Choose fastest duplicate deterministically,
/// then enforce address diversity and overlay caps. Source dates are never rebuilt.
func makePeerList(_ records: [Record], tip: Int32, date: String) throws -> PeerList {
    var networks: [String: [CensusCatalog.Entry]] = ["clearnet": [], "tor": [], "i2p": []]
    var candidates: [(CensusCatalog.Entry, Int, WalletCore.OverlayNetwork)] = []
    for record in records where record.outcome == "ok" && atTip(record, tip: tip) {
        let overlay = WalletCore.OverlayNetwork(ofHost: record.host)
        guard let host = CensusCatalog.canonicalHost(record.host, overlay: overlay),
              let ua = record.userAgent, ua.utf8.count <= 256,
              !ua.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 }),
              let height = record.startHeight, record.port > 0, record.latencyMs >= 0,
              let services = record.services, services & 64 != 0 else { continue }
        if overlay == .clearnet && record.port != 8333 { continue }
        candidates.append((.init(host: host, port: record.port, userAgent: ua, startHeight: height), record.latencyMs, overlay))
    }
    var seen = Set<PeerEndpoint>(), blocks = Set<String>()
    for (entry, _, overlay) in candidates.sorted(by: {
        ($0.1, $0.0.host, $0.0.port, $0.0.userAgent, $0.0.startHeight) <
        ($1.1, $1.0.host, $1.0.port, $1.0.userAgent, $1.0.startHeight)
    }) {
        guard networks[overlay.rawValue]!.count < peerListOverlayCap, seen.insert(entry.endpoint).inserted else { continue }
        if overlay == .clearnet {
            guard let block = entry.endpoint.netblock, blocks.insert(block).inserted else { continue }
        }
        networks[overlay.rawValue]!.append(entry)
    }
    return try CensusCatalog(date: date, tip: tip, networks: networks).validated(requireFresh: false)
}

func writePeerList(_ records: [Record], tip: Int32, observedAt: String, to url: URL) throws -> PeerList {
    let list = try makePeerList(records, tip: tip, date: String(observedAt.prefix(10)))
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    try encoder.encode(list).write(to: url, options: .atomic)
    return list
}
