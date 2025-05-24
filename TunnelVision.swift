import Foundation
import Network
import CryptoKit

let targetHost = "httpbin.org"
let targetPort: NWEndpoint.Port = 443
let httpRequest = """
GET /ip HTTP/1.1\r
Host: \(targetHost)\r
Connection: close\r
\r
"""

enum LogicGate: String {
    case and = "AND", or = "OR", xor = "XOR"
    case nand = "NAND", nor = "NOR", xnor = "XNOR"
    case not = "NOT"
}

func sha256(_ input: String) -> String {
    let digest = SHA256.hash(data: Data(input.utf8))
    return digest.map { String(format: "%02x", $0) }.joined()
}

func connectViaInterface(interface: String, label: String, completion: @escaping (String?) -> Void) {
    let params = NWParameters.tls
    params.requiredInterfaceType = .other
    if let iface = NWInterface(interfaceName: interface, type: .other) {
        params.requiredInterface = iface
    }

    let conn = NWConnection(host: NWEndpoint.Host(targetHost), port: targetPort, using: params)

    conn.stateUpdateHandler = { state in
        switch state {
        case .ready:
            print("[\(label)] Connected. Sending request...")
            conn.send(content: httpRequest.data(using: .utf8), completion: .contentProcessed({ error in
                if let error = error {
                    print("[\(label)] Send error: \(error)")
                    completion(nil)
                    conn.cancel()
                }
            }))
        case .failed(let error):
            print("[\(label)] Connection failed: \(error)")
            completion(nil)
        default:
            break
        }
    }

    conn.start(queue: .global())

    conn.receive(minimumIncompleteLength: 1, maximumLength: 65536) { data, _, _, error in
        if let data = data, let response = String(data: data, encoding: .utf8) {
            print("[\(label)] Received response.")
            completion(response)
        } else {
            print("[\(label)] Receive error: \(String(describing: error))")
            completion(nil)
        }
        conn.cancel()
    }
}

func evaluateGate(_ gate: LogicGate, hash1: String?, hash2: String?) -> Bool {
    let a = hash1 != nil
    let b = hash2 != nil
    let match = (hash1 == hash2)

    switch gate {
    case .and:   return a && b && match
    case .or:    return a || b
    case .xor:   return a != b
    case .nand:  return !(a && b && match)
    case .nor:   return !(a || b)
    case .xnor:  return a == b && match
    case .not:   return !a // special: NOT VPN1
    }
}

func runLogicGateTest(_ gate: LogicGate) {
    let group = DispatchGroup()
    var res1: String?
    var res2: String?

    if gate == .not {
        // Unary test
        group.enter()
        connectViaInterface(interface: "utun0", label: "VPN1") { result in
            res1 = result
            group.leave()
        }
    } else {
        group.enter()
        connectViaInterface(interface: "utun0", label: "VPN1") { result in
            res1 = result
            group.leave()
        }

        group.enter()
        connectViaInterface(interface: "utun1", label: "VPN2") { result in
            res2 = result
            group.leave()
        }
    }

    group.notify(queue: .main) {
        let h1 = res1.map(sha256)
        let h2 = res2.map(sha256)

        print("\n--- Logic Gate: \(gate.rawValue) ---")
        print("VPN1 Hash: \(h1 ?? "nil")")
        print("VPN2 Hash: \(h2 ?? "nil")")

        if evaluateGate(gate, hash1: h1, hash2: h2) {
            print("\n✅ \(gate.rawValue) condition passed.\n")
            if let output = res1 ?? res2 {
                print(output)
            }
        } else {
            print("\n❌ \(gate.rawValue) condition failed.\n")
        }

        exit(0)
    }
}

// Change the logic gate here
let selectedGate: LogicGate = .and // Options: .or, .xor, .nand, .nor, .xnor, .not

print("🔐 Starting dual-VPN \(selectedGate.rawValue) logic test...")
runLogicGateTest(selectedGate)
RunLoop.main.run()
