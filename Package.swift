// swift-tools-version: 6.0
import PackageDescription

// The census dials with Winnow's own PeerConnection, consumed here as an
// ordinary package dependency. The rebuilt wallet (winnowwallet/winnow) folds
// the old BitcoinCore/BitcoinP2P products into one WalletCore library, with
// the SOCKS5 proxy support on main.
let package = Package(
    name: "winnow-census",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "WinnowCensus", targets: ["WinnowCensus"]),
    ],
    dependencies: [
        .package(url: "https://github.com/winnowwallet/winnow", revision: "8137afd7cc403a8fd424495f5f4f1601a30b2ab3"),
    ],
    targets: [
        .executableTarget(
            name: "WinnowCensus",
            dependencies: [
                .product(name: "WalletCore", package: "winnow"),
            ]
        ),
    ]
)
