import XCTest
@testable import Macfix

final class GroqTests: XCTestCase {
    func testValidExplanation() throws {
        let data = Data(#"{"meaning":"Unclear error","severity":"Unknown","causes":["Not enough context"],"steps":["Record the exact message"],"avoid":"Do not erase anything"}"#.utf8)
        XCTAssertEqual(try Explanation.parse(data).severity, "Unknown")
    }
    func testInvalidExplanation() {
        XCTAssertThrowsError(try Explanation.parse(Data(#"{"meaning":"x","severity":"Critical","causes":[],"steps":[],"avoid":"x"}"#.utf8)))
        XCTAssertThrowsError(try Explanation.parse(Data("not json".utf8)))
    }
    func testTextAndImageRouting() throws {
        let text = try JSONSerialization.jsonObject(with: Groq.payload(message: "Error", image: nil)) as! [String: Any]
        XCTAssertEqual(text["model"] as? String, "openai/gpt-oss-120b")
        let vision = try JSONSerialization.jsonObject(with: Groq.payload(message: "Error", image: Data([1, 2]))) as! [String: Any]
        XCTAssertEqual(vision["model"] as? String, "qwen/qwen3.6-27b")
        let messages = vision["messages"] as! [[String: Any]]
        let parts = messages[1]["content"] as! [[String: Any]]
        XCTAssertEqual((parts[1]["image_url"] as? [String: String])?["url"], "data:image/png;base64,AQI=")
    }
    func testEmptyAndOversizedInputRejected() {
        XCTAssertThrowsError(try Groq.payload(message: "  ", image: nil))
        XCTAssertThrowsError(try Groq.payload(message: String(repeating: "x", count: 8001), image: nil))
    }
}
