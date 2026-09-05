// swift-tools-version: 6.0
import PackageDescription

// The census dials with Winnow's own PeerConnection, consumed here as an
// ordinary package dependency. It follows the branch that carries the SOCKS5
// proxy support (posix4e/winnow#177); switch to "main" once that merges.
let package = Package(
    name: "winnow-census",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "WinnowCensus", targets: ["WinnowCensus"]),
    ],
    dependencies: [
        .package(url: "https://github.com/posix4e/winnow", branch: "feat/socks-proxy"),
    ],
    targets: [
        .executableTarget(
            name: "WinnowCensus",
            dependencies: [
                .product(name: "BitcoinCore", package: "winnow"),
                .product(name: "BitcoinP2P", package: "winnow"),
            ]
        ),
    ]
)
