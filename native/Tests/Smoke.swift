// Compiler-only checks for installations where Swift Package Manager is unavailable.
import Foundation

@main struct SmokeTests {
    static func main() throws {
        func expect(_ condition: Bool, _ label: String) throws {
            guard condition else { throw MacfixError.message("FAIL: " + label) }
            print("PASS: " + label)
        }
        func rejects(_ action: () throws -> Void) -> Bool {
            do { try action(); return false } catch { return true }
        }
        let valid = Data(#"{"meaning":"Unclear error","severity":"Unknown","causes":["More context needed"],"steps":["Record the exact message"],"avoid":"Do not erase data"}"#.utf8)
        try expect(try Explanation.parse(valid).severity == "Unknown", "valid answer")
        try expect(rejects { _ = try Explanation.parse(Data("not json".utf8)) }, "malformed answer rejected")
        try expect(rejects { _ = try Explanation.parse(Data(#"{"meaning":"x","severity":"Critical","causes":[],"steps":[],"avoid":"x"}"#.utf8)) }, "invalid fields rejected")
        try expect(rejects { _ = try Groq.payload(message: " ", image: nil) }, "empty description rejected")
        try expect(rejects { _ = try Groq.payload(message: String(repeating: "x", count: 8001), image: nil) }, "oversized description rejected")
        let text = try JSONSerialization.jsonObject(with: Groq.payload(message: "Error", image: nil)) as! [String: Any]
        try expect(text["model"] as? String == "openai/gpt-oss-120b", "text model routing")
        let vision = try JSONSerialization.jsonObject(with: Groq.payload(message: "Error", image: Data([1, 2]))) as! [String: Any]
        let messages = vision["messages"] as! [[String: Any]]
        let parts = messages[1]["content"] as! [[String: Any]]
        try expect(vision["model"] as? String == "qwen/qwen3.6-27b" &&
                   (parts[1]["image_url"] as? [String: String])?["url"] == "data:image/png;base64,AQI=", "vision model and attachment routing")
    }
}
