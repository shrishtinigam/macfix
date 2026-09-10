import SwiftUI
import AppKit
import Carbon
import ImageIO
import UniformTypeIdentifiers

@MainActor final class Model: ObservableObject {
    @Published var problem = ""
    @Published var screenshot: Data?
    @Published var answer: Explanation?
    @Published var error = ""
    @Published var busy = false
    @Published var capturing = false
    @Published var settings = false
    @Published var keyDraft = ""
    private var task: Task<Void, Never>?
    var hide: () -> Void = {}
    var show: () -> Void = {}

    func explain() {
        error = ""
        do {
            let key = try KeyStore.read()
            if key.isEmpty { settings = true; return }
            let text = problem
            let image = screenshot
            busy = true
            answer = nil
            task = Task {
                defer { busy = false; task = nil }
                do {
                    let result = try await Groq.explain(message: text, image: image, key: key)
                    try Task.checkCancellation()
                    answer = result
                } catch {
                    if !Task.isCancelled { self.error = (error as? MacfixError)?.localizedDescription ?? "Could not reach Groq. Check your connection and try again." }
                }
            }
        } catch { self.error = error.localizedDescription }
    }
    func cancel() { task?.cancel() }
    func saveKey() {
        do { try KeyStore.save(keyDraft); keyDraft = ""; settings = false; error = "" }
        catch { self.error = error.localizedDescription }
    }
    func loadImage(_ url: URL) {
        do {
            let size = try url.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0
            guard size <= 8 * 1024 * 1024 else { throw MacfixError.message("Choose a PNG or JPEG smaller than 8 MB.") }
            let data = try Data(contentsOf: url)
            guard let source = CGImageSourceCreateWithData(data as CFData, nil),
                  let type = CGImageSourceGetType(source) as String?,
                  [UTType.png.identifier, UTType.jpeg.identifier].contains(type),
                  let props = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [String: Any],
                  let width = props[kCGImagePropertyPixelWidth as String] as? Int,
                  let height = props[kCGImagePropertyPixelHeight as String] as? Int,
                  width > 0, height > 0, Double(width) * Double(height) <= 20_000_000,
                  let image = CGImageSourceCreateThumbnailAtIndex(source, 0, [
                    kCGImageSourceCreateThumbnailFromImageAlways: true,
                    kCGImageSourceCreateThumbnailWithTransform: true,
                    kCGImageSourceThumbnailMaxPixelSize: 2400
                  ] as CFDictionary) else { throw MacfixError.message("Choose a valid PNG or JPEG of at most 20 megapixels.") }
            let output = NSMutableData()
            guard let destination = CGImageDestinationCreateWithData(output, UTType.png.identifier as CFString, 1, nil) else {
                throw MacfixError.message("Could not prepare the image.")
            }
            CGImageDestinationAddImage(destination, image, nil)
            guard CGImageDestinationFinalize(destination), output.length <= 8 * 1024 * 1024 else {
                throw MacfixError.message("Image is too large. Select a smaller region.")
            }
            screenshot = output as Data
            error = ""
        } catch { self.error = error.localizedDescription }
    }
    func chooseImage() {
        let picker = NSOpenPanel()
        picker.allowedContentTypes = [.png, .jpeg]
        picker.canChooseDirectories = false
        picker.allowsMultipleSelection = false
        if picker.runModal() == .OK, let url = picker.url { loadImage(url) }
    }
    func capture() {
        guard CGPreflightScreenCaptureAccess() else {
            _ = CGRequestScreenCaptureAccess()
            error = "Allow macfix in System Settings → Privacy & Security → Screen Recording, then reopen the app and try again."
            return
        }
        capturing = true
        error = ""
        hide()
        Task {
            let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            defer { try? FileManager.default.removeItem(at: directory); capturing = false; show() }
            do {
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
                let url = directory.appendingPathComponent("capture.png")
                try await Task.sleep(nanoseconds: 250_000_000)
                let status: Int32 = try await withCheckedThrowingContinuation { continuation in
                    let process = Process()
                    process.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
                    process.arguments = ["-i", "-s", "-x", "-t", "png", url.path]
                    process.standardError = FileHandle.nullDevice
                    process.terminationHandler = { finished in continuation.resume(returning: finished.terminationStatus) }
                    do { try process.run() } catch { continuation.resume(throwing: error) }
                }
                if FileManager.default.fileExists(atPath: url.path) { loadImage(url) }
                else if status != 0 { error = "Screenshot cancelled or unavailable. Try again or choose an image." }
            } catch { self.error = "Could not capture the screen. Try choosing an image instead." }
        }
    }
}

struct MainView: View {
    @ObservedObject var model: Model
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Image(systemName: "wrench.and.screwdriver")
                Text("macfix").font(.title2.bold())
                Spacer()
                Button("Settings") { model.settings.toggle() }.disabled(model.busy)
                Button { model.hide() } label: { Image(systemName: "xmark") }.help("Hide (Escape)")
            }
            if model.settings {
                Text("Save your Groq API key once in macOS Keychain.")
                SecureField("Groq API key", text: $model.keyDraft)
                HStack {
                    Link("Get a key", destination: URL(string: "https://console.groq.com/keys")!)
                    Spacer()
                    Button("Cancel") { model.keyDraft = ""; model.settings = false }
                    Button("Save key") { model.saveKey() }
                }
            } else {
                Text("What’s going wrong?").font(.headline)
                TextEditor(text: $model.problem)
                    .font(.body).frame(height: 85).padding(6)
                    .background(.quaternary, in: RoundedRectangle(cornerRadius: 8))
                    .disabled(model.busy)
                    .accessibilityLabel("Describe the error or problem")
                HStack {
                    Button("Capture region") { model.capture() }
                    Button("Choose image…") { model.chooseImage() }
                    Spacer()
                    Text("⌃⌥M to show / hide").font(.caption).foregroundStyle(.secondary)
                }.disabled(model.busy || model.capturing)
                if let data = model.screenshot, let image = NSImage(data: data) {
                    HStack {
                        Image(nsImage: image).resizable().scaledToFit().frame(maxWidth: 440, maxHeight: 130)
                        Button("Remove") { model.screenshot = nil }.disabled(model.busy)
                    }
                }
                Text("Explain sends your description and attached image to Groq. Check for private details first.")
                    .font(.caption).foregroundStyle(.secondary)
                HStack {
                    if model.busy { ProgressView().controlSize(.small); Text("Asking Groq…"); Button("Cancel") { model.cancel() } }
                    Spacer()
                    Button("Explain") { model.explain() }.buttonStyle(.borderedProminent)
                        .disabled(model.busy || model.capturing || model.problem.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
            if !model.error.isEmpty { Text(model.error).foregroundStyle(.red).textSelection(.enabled) }
            if let result = model.answer {
                Divider()
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        section("Meaning", result.meaning)
                        section("Severity", result.severity)
                        section("Likely causes", result.causes.map { "• " + $0 }.joined(separator: "\n"))
                        section("What to try", result.steps.enumerated().map { "\($0.offset + 1). \($0.element)" }.joined(separator: "\n"))
                        section("Avoid", result.avoid)
                        Text("AI advice can be wrong. macfix does not execute repairs.").font(.caption).foregroundStyle(.secondary)
                    }.frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled)
                }
            }
            Spacer(minLength: 0)
        }.padding(22).frame(minWidth: 560, minHeight: 580)
    }
    private func section(_ title: String, _ text: String) -> some View {
        VStack(alignment: .leading, spacing: 4) { Text(title).font(.headline); Text(text) }
    }
}

final class FloatingPanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override func cancelOperation(_ sender: Any?) { orderOut(nil) }
}

@MainActor final class AppDelegate: NSObject, NSApplicationDelegate {
    let model = Model()
    var panel: FloatingPanel!
    var status: NSStatusItem!
    var hotKey: EventHotKeyRef?
    var eventHandler: EventHandlerRef?
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        panel = FloatingPanel(contentRect: NSRect(x: 0, y: 0, width: 600, height: 740),
                              styleMask: [.titled, .closable, .resizable, .fullSizeContentView], backing: .buffered, defer: false)
        panel.title = "macfix"
        panel.titleVisibility = .hidden
        panel.titlebarAppearsTransparent = true
        panel.isReleasedWhenClosed = false
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.contentView = NSHostingView(rootView: MainView(model: model))
        panel.center()
        model.hide = { [weak self] in self?.panel.orderOut(nil) }
        model.show = { [weak self] in self?.showPanel() }
        status = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        status.button?.image = NSImage(systemSymbolName: "wrench.and.screwdriver", accessibilityDescription: "macfix")
        let menu = NSMenu()
        menu.addItem(withTitle: "Show macfix (⌃⌥M)", action: #selector(showPanel), keyEquivalent: "")
        menu.addItem(withTitle: "Settings…", action: #selector(settings), keyEquivalent: "")
        menu.addItem(.separator())
        menu.addItem(withTitle: "Quit macfix", action: #selector(quit), keyEquivalent: "q")
        for item in menu.items { item.target = self }
        status.menu = menu
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        let pointer = Unmanaged.passUnretained(self).toOpaque()
        let handlerStatus = InstallEventHandler(GetApplicationEventTarget(), { _, _, context in
            guard let context = context else { return noErr }
            let delegate = Unmanaged<AppDelegate>.fromOpaque(context).takeUnretainedValue()
            Task { @MainActor in delegate.toggle() }
            return noErr
        }, 1, &spec, pointer, &eventHandler)
        let keyStatus = RegisterEventHotKey(UInt32(kVK_ANSI_M), UInt32(controlKey | optionKey),
                                          EventHotKeyID(signature: 0x4D464958, id: 1), GetApplicationEventTarget(), 0, &hotKey)
        if handlerStatus != noErr || keyStatus != noErr { model.error = "Could not register ⌃⌥M. Use the menu-bar icon to open macfix." }
        showPanel()
    }
    @objc func showPanel() { NSApp.activate(ignoringOtherApps: true); panel.makeKeyAndOrderFront(nil) }
    @objc func settings() { model.settings = true; showPanel() }
    @objc func quit() { model.cancel(); NSApp.terminate(nil) }
    func toggle() { if panel.isVisible { panel.orderOut(nil) } else { showPanel() } }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { showPanel(); return true }
    func applicationWillTerminate(_ notification: Notification) {
        if let hotKey { UnregisterEventHotKey(hotKey) }
        if let eventHandler { RemoveEventHandler(eventHandler) }
    }
}

@main struct Launcher {
    @MainActor static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        withExtendedLifetime(delegate) { app.run() }
    }
}
