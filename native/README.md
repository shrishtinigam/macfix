# macfix for Mac

A native SwiftUI/AppKit menu-bar app. Requires macOS 13+ and Apple's Command
Line Tools (Swift 5.9+) to build. No Python or third-party Swift dependencies.

From this folder:

```bash
xcode-select --install  # once; finish the installer before continuing
bash build.sh
```

The script runs tests, builds and opens `dist/macfix.app`. You can drag this app
to Applications. It is locally signed for development, not notarized for distribution.

1. Open Settings and save your Groq key in Keychain. The CLI's `.env` is separate.
2. Type the problem; optionally choose an image or capture a region.
3. Review the screenshot for private information, then click **Explain**.

**Control–Option–M** shows/hides the window while the app is running. Escape or
close hides it; the menu-bar **Quit macfix** stops the app. Open the app normally
to start it again. It does not launch at login automatically.

Capture may require permission in System Settings → Privacy & Security → Screen
Recording. Restart the app after granting permission. Escape cancels selection.

Only clicking Explain sends the description and attached image to Groq. Screenshots
are prepared without metadata; captures use temporary files deleted after loading.
Answers and attachments stay in memory until quitting. The app never executes advice.
There is no offline fallback. Internet access and your own Groq account are required.

Run compiler-only checks separately with `bash test.sh`, or the XCTest suite with
`swift test` when Swift Package Manager is working. The build script uses `swiftc`
directly and keeps its module cache in the project. Manual checks after building: key save/reopen,
shortcut and Escape, capture approval/denial/cancellation, image preview/removal,
text/image replies, request cancellation, and menu-bar quit.
