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

func sha256(_ input: String) -> String {
    let digest = SHA256.hash(data: Data(input.utf8))
    return digest.map { String(format: "%02x", $0) }.joined()
}

func connectViaInterface(interface: String, label: String, completion: @escaping (String?) -> Void) {
    let params = NWParameters.tls
    params.requiredInterfaceType = .other // avoid .wifi or .cellular
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

    conn.receive(minimumIncompleteLength: 1, maximumLength: 65536) { data, _, isComplete, error in
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

func runAndLogic() {
    let group = DispatchGroup()
    var res1: String?
    var res2: String?

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

    group.notify(queue: .main) {
        guard let r1 = res1, let r2 = res2 else {
            print("\n❌ One or both VPNs failed.")
            exit(1)
        }

        let h1 = sha256(r1)
        let h2 = sha256(r2)

        print("\nVPN1 Hash: \(h1)")
        print("VPN2 Hash: \(h2)")

        if h1 == h2 {
            print("\n✅ AND-Verified. Responses match.\n")
            print(r1)
        } else {
            print("\n❌ Responses do not match.\n")
        }
        exit(0)
    }
}

print("🔐 Starting dual-VPN AND logic test...")
runAndLogic()
RunLoop.main.run()
