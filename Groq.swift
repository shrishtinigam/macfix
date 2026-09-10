import Foundation

struct Explanation: Decodable {
    let meaning: String
    let severity: String
    let causes: [String]
    let steps: [String]
    let avoid: String

    static func parse(_ data: Data) throws -> Explanation {
        let result = try JSONDecoder().decode(Self.self, from: data)
        func valid(_ text: String, limit: Int) -> Bool {
            !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && text.count <= limit
        }
        guard valid(result.meaning, limit: 6000), valid(result.avoid, limit: 6000),
              ["Low", "Medium", "High", "Unknown"].contains(result.severity),
              (1...5).contains(result.causes.count), (1...5).contains(result.steps.count),
              (result.causes + result.steps).allSatisfy({ valid($0, limit: 3000) }) else {
            throw MacfixError.message("Groq returned an invalid explanation. Try again.")
        }
        return result
    }
}

enum MacfixError: LocalizedError {
    case message(String)
    var errorDescription: String? { if case .message(let text) = self { return text }; return nil }
}

final class NoRedirect: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest,
                    completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
}

enum Groq {
    static func payload(message: String, image: Data?) throws -> Data {
        guard !message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, message.count <= 8000 else {
            throw MacfixError.message("Describe the problem in 1–8,000 characters.")
        }
        #if SWIFT_PACKAGE
        let resourceBundle = Bundle.module
        #else
        let resourceBundle = Bundle.main
        #endif
        guard let url = resourceBundle.url(forResource: "system-prompt", withExtension: "txt") else {
            throw MacfixError.message("The app is missing its prompt resource. Rebuild it.")
        }
        let prompt = try String(contentsOf: url, encoding: .utf8)
        let content: Any = image.map { data -> Any in
            [["type": "text", "text": message],
             ["type": "image_url", "image_url": ["url": "data:image/png;base64," + data.base64EncodedString()]]]
        } ?? message
        return try JSONSerialization.data(withJSONObject: [
            "model": image == nil ? "openai/gpt-oss-120b" : "qwen/qwen3.6-27b",
            "messages": [["role": "system", "content": prompt], ["role": "user", "content": content]],
            "response_format": ["type": "json_object"],
            "reasoning_effort": image == nil ? "low" : "none",
            "max_completion_tokens": 3000, "temperature": 0.2
        ])
    }

    static func explain(message: String, image: Data?, key: String) async throws -> Explanation {
        guard !key.isEmpty, key.utf8.allSatisfy({ $0 > 32 && $0 < 127 }) else {
            throw MacfixError.message("Save a valid Groq API key in Settings first.")
        }
        var request = URLRequest(url: URL(string: "https://api.groq.com/openai/v1/chat/completions")!)
        request.httpMethod = "POST"
        request.setValue("Bearer " + key, forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try payload(message: message, image: image)
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 45
        config.timeoutIntervalForResource = 60
        let session = URLSession(configuration: config, delegate: NoRedirect(), delegateQueue: nil)
        defer { session.invalidateAndCancel() }
        let (bytes, response) = try await session.bytes(for: request)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard status == 200 else {
            let detail = [401: "Groq rejected the key. Update it in Settings.",
                          403: "Groq denied access. Check your account permissions.",
                          429: "Groq's usage limit was reached. Wait before trying again."]
            throw MacfixError.message(detail[status] ?? "Groq request failed (HTTP \(status)). Try again later.")
        }
        var data = Data()
        for try await byte in bytes {
            guard data.count < 128000 else { throw MacfixError.message("Groq returned an oversized response.") }
            data.append(byte)
        }
        struct Envelope: Decodable {
            struct Choice: Decodable {
                struct Message: Decodable { let content: String }
                let message: Message
                let finish_reason: String
            }
            let choices: [Choice]
        }
        do {
            let envelope = try JSONDecoder().decode(Envelope.self, from: data)
            guard let choice = envelope.choices.first, choice.finish_reason == "stop" else {
                throw MacfixError.message("Incomplete answer")
            }
            return try Explanation.parse(Data(choice.message.content.utf8))
        } catch { throw MacfixError.message("Groq returned an incomplete or invalid explanation. Try again.") }
    }
}
