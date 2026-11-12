import SwiftUI
import WebKit
import Darwin

struct CoreConfig: Codable {
    var host = "http://127.0.0.1:11434"
    var model = "ghost-heretic"
    var memoryModel = "ghost-heretic"
    var apiKey = ""
    var learning = true
    var skills = false
    var allowedApps = "calculator,notes"
    var searchRoot = "~/Documents"
}

@MainActor final class CoreService: ObservableObject {
    @Published var url: URL?
    @Published var error: String?
    @Published var starting = false
    @Published var config = CoreConfig()
    private var process: Process?
    private var output: FileHandle?
    private var generation = UUID()
    let support: URL

    init() {
        if let override = ProcessInfo.processInfo.environment["GHOST_APP_DATA"] {
            support = URL(fileURLWithPath: override)
        } else {
            support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("Ghost AI")
        }
        if let data = try? Data(contentsOf: support.appendingPathComponent("config.json")), let saved = try? JSONDecoder().decode(CoreConfig.self, from: data) { config = saved }
    }

    func stop() {
        generation = UUID()
        process?.terminate()
        process = nil
        try? output?.close()
        output = nil
        url = nil
    }

    func saveAndRestart() {
        do {
            guard let endpoint = URLComponents(string: config.host), ["http", "https"].contains(endpoint.scheme ?? ""), let hostname = endpoint.host, endpoint.user == nil, endpoint.password == nil, endpoint.query == nil, endpoint.fragment == nil, endpoint.path.isEmpty || endpoint.path == "/" else { throw CoreError.invalidHost }
            if endpoint.scheme == "http" && !["localhost", "127.0.0.1", "::1"].contains(hostname) { throw CoreError.remoteHTTPS }
            try FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
            let target = support.appendingPathComponent("config.json")
            try JSONEncoder().encode(config).write(to: target, options: .atomic)
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: target.path)
            start()
        } catch { self.error = error.localizedDescription }
    }

    func start() {
        stop()
        error = nil
        starting = true
        let current = UUID(); generation = current
        do {
            try FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
            guard let resource = Bundle.main.resourceURL else { throw CoreError.backendMissing }
            let executable = resource.appendingPathComponent("Backend/VoxelBackend")
            guard FileManager.default.isExecutableFile(atPath: executable.path) else { throw CoreError.backendMissing }
            let port = try availablePort()
            let token = UUID().uuidString + UUID().uuidString
            let origin = "http://127.0.0.1:\(port)"
            let sessionID = UserDefaults.standard.string(forKey: "ghostSession") ?? UUID().uuidString
            UserDefaults.standard.set(sessionID, forKey: "ghostSession")
            let task = Process(); task.executableURL = executable
            var env = ProcessInfo.processInfo.environment
            env["GHOST_DATA_DIR"] = support.appendingPathComponent("data").path
            env["GHOST_API_TOKEN"] = token
            env["GHOST_BIND"] = "127.0.0.1"
            env["GHOST_PORT"] = String(port)
            env["GHOST_PUBLIC"] = "0"
            env["GHOST_ALLOWED_HOSTS"] = "127.0.0.1,localhost"
            env["GHOST_ALLOWED_ORIGINS"] = origin
            env["OLLAMA_HOST"] = config.host
            env["OLLAMA_API_KEY"] = config.apiKey
            env["GHOST_MODEL"] = config.model
            env["GHOST_MEMORY_MODEL"] = config.memoryModel
            env["GHOST_LEARNING"] = config.learning ? "1" : "0"
            env["GHOST_ENABLE_SKILLS"] = config.skills ? "1" : "0"
            env["GHOST_ALLOWED_APPS"] = config.allowedApps
            env["GHOST_SEARCH_ROOT"] = config.searchRoot
            env["GHOST_WEB_SEARCH"] = "0"
            task.environment = env
            task.currentDirectoryURL = support
            let log = support.appendingPathComponent("server.log")
            if !FileManager.default.fileExists(atPath: log.path) { FileManager.default.createFile(atPath: log.path, contents: nil) }
            let handle = try FileHandle(forWritingTo: log); try handle.seekToEnd()
            task.standardOutput = handle; task.standardError = handle; output = handle
            try task.run(); process = task
            task.terminationHandler = { [weak self] task in
                Task { @MainActor in
                    guard let self, self.generation == current else { return }
                    self.error = "El motor del Núcleo se cerró (\(task.terminationStatus)). Revisa el registro o vuelve a iniciar."
                    self.url = nil; self.starting = false
                }
            }
            Task {
                let sessionConfig = URLSessionConfiguration.ephemeral
                sessionConfig.timeoutIntervalForRequest = 1
                let session = URLSession(configuration: sessionConfig)
                defer { session.invalidateAndCancel() }
                for _ in 0..<100 {
                    guard generation == current, task.isRunning else { return }
                    if let (_, response) = try? await session.data(from: URL(string: origin)!), (response as? HTTPURLResponse)?.statusCode == 200 {
                        url = URL(string: origin + "/#access=" + token + "&session=" + sessionID)
                        starting = false
                        return
                    }
                    try? await Task.sleep(nanoseconds: 150_000_000)
                }
                guard generation == current else { return }
                stop(); error = "Núcleo no pudo iniciar. Abre el registro para revisar el motivo."; starting = false
            }
        } catch { self.error = error.localizedDescription; starting = false }
    }

    func availablePort() throws -> UInt16 {
        let fd = socket(AF_INET, SOCK_STREAM, 0)
        guard fd >= 0 else { throw CoreError.port }
        defer { Darwin.close(fd) }
        var addr = sockaddr_in(); addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size); addr.sin_family = sa_family_t(AF_INET); addr.sin_addr.s_addr = inet_addr("127.0.0.1"); addr.sin_port = 0
        let result = withUnsafePointer(to: &addr) { ptr in ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) { Darwin.bind(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size)) } }
        guard result == 0 else { throw CoreError.port }
        var size = socklen_t(MemoryLayout<sockaddr_in>.size)
        let nameResult = withUnsafeMutablePointer(to: &addr) { ptr in ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) { getsockname(fd, $0, &size) } }
        guard nameResult == 0 else { throw CoreError.port }
        return UInt16(bigEndian: addr.sin_port)
    }
}

enum CoreError: LocalizedError {
    case backendMissing, port, invalidHost, remoteHTTPS
    var errorDescription: String? {
        switch self {
        case .backendMissing: "Falta el motor Python. Ejecuta Preparar-motor.command y vuelve a compilar la app."
        case .port: "No se pudo reservar un puerto local."
        case .invalidHost: "Usa una dirección de Ollama completa, sin rutas, credenciales ni parámetros."
        case .remoteHTTPS: "Para un servidor remoto utiliza HTTPS o un túnel local."
        }
    }
}

struct CoreWebView: NSViewRepresentable {
    let url: URL
    func makeCoordinator() -> Coordinator { Coordinator(origin: url) }
    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.userContentController.add(context.coordinator, name: "ghostSession")
        let view = WKWebView(frame: .zero, configuration: config)
        view.navigationDelegate = context.coordinator
        view.setValue(false, forKey: "drawsBackground")
        view.load(URLRequest(url: url))
        return view
    }
    func updateNSView(_ view: WKWebView, context: Context) {}
    class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler {
        let origin: URL
        init(origin: URL) { self.origin = origin }
        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard message.frameInfo.isMainFrame, message.frameInfo.securityOrigin.host == origin.host, message.frameInfo.securityOrigin.port == origin.port, let value = message.body as? String, UUID(uuidString: value) != nil else { return }
            UserDefaults.standard.set(value, forKey: "ghostSession")
        }
        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = navigationAction.request.url, url.scheme == origin.scheme, url.host == origin.host, url.port == origin.port else { decisionHandler(.cancel); return }
            decisionHandler(.allow)
        }
    }
}

struct CoreSettings: View {
    @ObservedObject var service: CoreService
    var body: some View {
        Form {
            Section("Motor de IA") {
                TextField("Servidor Ollama", text: $service.config.host)
                TextField("Modelo de chat", text: $service.config.model)
                TextField("Modelo de memoria", text: $service.config.memoryModel)
                SecureField("Clave API remota (opcional)", text: $service.config.apiKey)
                Toggle("Aprender recuerdos de las conversaciones", isOn: $service.config.learning)
            }
            Section("Skills de macOS") {
                Toggle("Permitir acciones locales con confirmación", isOn: $service.config.skills)
                TextField("Apps permitidas (nombres en inglés, separados por coma)", text: $service.config.allowedApps)
                TextField("Carpeta de búsqueda", text: $service.config.searchRoot)
                Text("Solo abre apps de la lista y busca dentro de esta carpeta. No ejecuta comandos de shell.").font(.caption).foregroundStyle(.secondary)
            }
            HStack {
                Button("Abrir datos") { NSWorkspace.shared.open(service.support) }
                Button("Ver registro") { NSWorkspace.shared.open(service.support.appendingPathComponent("server.log")) }
                Spacer()
                Button("Guardar y reiniciar") { service.saveAndRestart() }.buttonStyle(.borderedProminent)
            }
            if let error = service.error { Text(error).foregroundStyle(.red).font(.caption) }
            Text("La app guarda tu memoria en Application Support / Ghost AI. Un servidor remoto recibe los mensajes y la memoria incluida en el contexto. La clave se guarda en tu configuración local, protegida con permisos del usuario.").font(.caption).foregroundStyle(.secondary)
        }.formStyle(.grouped).frame(width:620, height:560)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var service: CoreService?
    func applicationWillTerminate(_ notification: Notification) { MainActor.assumeIsolated { service?.stop() } }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

@main struct VoxelApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var delegate
    @StateObject private var service = CoreService()
    var body: some Scene {
        WindowGroup("Enjambre de Vóxeles") {
            ContentView(service:service).onAppear { delegate.service = service; if !service.starting && service.url == nil { service.start() } }
        }.defaultSize(width:1220,height:920)
        .commands {
            CommandGroup(after:.appSettings) {
                Button("Reiniciar enlace") { service.start() }
            }
        }
        Settings { CoreSettings(service:service) }
    }
}
