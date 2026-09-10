#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
SDK_PATH="${MACFIX_SDK_PATH:-$(xcode-select -p)/SDKs/MacOSX.sdk}"
mkdir -p .build/module-cache .build/smoke
xcrun swiftc -sdk "$SDK_PATH" -module-cache-path "$PWD/.build/module-cache" -swift-version 5 -parse-as-library Sources/Macfix/Groq.swift Sources/Macfix/KeyStore.swift Tests/Smoke.swift -o .build/smoke/MacfixTests
cp Sources/Macfix/Resources/system-prompt.txt .build/smoke/
.build/smoke/MacfixTests
