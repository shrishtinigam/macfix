// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "Macfix",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "Macfix", targets: ["Macfix"])],
    targets: [.executableTarget(name: "Macfix", resources: [.process("Resources")]),
              .testTarget(name: "MacfixTests", dependencies: ["Macfix"])]
)
