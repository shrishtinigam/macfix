#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if ! xcrun --find swift >/dev/null 2>&1; then
  echo "Install Apple's Command Line Tools first: xcode-select --install" >&2
  exit 1
fi
APP="$PWD/dist/macfix.app"
bash test.sh
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
SDK_PATH="${MACFIX_SDK_PATH:-$(xcode-select -p)/SDKs/MacOSX.sdk}"
mkdir -p .build/module-cache
xcrun swiftc -sdk "$SDK_PATH" -module-cache-path "$PWD/.build/module-cache" -swift-version 5 -O -parse-as-library Sources/Macfix/*.swift -o "$APP/Contents/MacOS/Macfix"
cp Sources/Macfix/Resources/system-prompt.txt "$APP/Contents/Resources/"
cp Info.plist "$APP/Contents/Info.plist"
codesign --force --deep --sign - "$APP"
echo "Built $APP"
echo "Open it from Finder: $APP"
