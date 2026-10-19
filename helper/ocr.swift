// Pure worker: reads length-prefixed image bytes on stdin, writes one JSON line per image.
// It never opens a path of its own, so the file-reading TCC grant stays with the Python
// entry point at a stable location instead of moving with every release.
import Foundation
import Vision
import AppKit

let stdin = FileHandle.standardInput
let stdout = FileHandle.standardOutput
var languages = ["en-US"]
if let i = CommandLine.arguments.firstIndex(of: "--langs"), i + 1 < CommandLine.arguments.count {
    languages = CommandLine.arguments[i + 1].split(separator: ",").map(String.init)
}

func readLine_() -> String? {
    var bytes = [UInt8]()
    while let b = try? stdin.read(upToCount: 1), let byte = b.first {
        if byte == 0x0A { return String(bytes: bytes, encoding: .utf8) }
        bytes.append(byte)
    }
    return bytes.isEmpty ? nil : String(bytes: bytes, encoding: .utf8)
}

func readExactly(_ n: Int) -> Data? {
    var out = Data()
    while out.count < n {
        guard let chunk = try? stdin.read(upToCount: n - out.count), !chunk.isEmpty
        else { return nil }
        out.append(chunk)
    }
    return out
}

while let header = readLine_(), !header.isEmpty {
    guard let length = Int(header.trimmingCharacters(in: .whitespaces)), length > 0,
          let data = readExactly(length) else { break }

    var text = ""
    var width = 0, height = 0
    if let image = NSImage(data: data),
       let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) {
        width = cg.width; height = cg.height
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = languages
        request.usesLanguageCorrection = false
        if (try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([request])) != nil,
           let results = request.results {
            text = results.compactMap { $0.topCandidates(1).first?.string }
                          .joined(separator: " | ")
        }
    }
    let payload: [String: Any] = ["t": text, "w": width, "h": height]
    if let line = try? JSONSerialization.data(withJSONObject: payload) {
        stdout.write(line); stdout.write(Data([0x0A]))
    }
}
