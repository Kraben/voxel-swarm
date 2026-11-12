import AppKit
import Foundation
import MusicKit

// A persistent, signed macOS app owns playback. IPC is inherited stdin/stdout,
// not an exposed socket. Authorization is requested only from Settings.
struct Command: Decodable {
    let id: String
    let action: String
    let query: String?
}

@MainActor
final class Bridge: NSObject, NSApplicationDelegate {
    let player = ApplicationMusicPlayer.shared
    func applicationDidFinishLaunching(_ notification: Notification) {
        DispatchQueue.global(qos: .userInitiated).async {
            while let line = readLine() {
                guard line.utf8.count <= 4096, let data = line.data(using: .utf8),
                      let command = try? JSONDecoder().decode(Command.self, from: data) else { continue }
                let done = DispatchSemaphore(value: 0)
                Task { @MainActor in
                    let result = await self.execute(command)
                    var output = result
                    output["id"] = command.id
                    if let encoded = try? JSONSerialization.data(withJSONObject: output) {
                        FileHandle.standardOutput.write(encoded + Data([10]))
                    }
                    done.signal()
                }
                done.wait()
            }
            Task { @MainActor in
                self.player.pause()
                NSApplication.shared.terminate(nil)
            }
        }
    }
    func failure(_ code: String, _ message: String) -> [String: Any] {
        ["ok": false, "code": code, "message": message]
    }
    func status() async throws -> [String: Any] {
        let auth = MusicAuthorization.currentStatus
        let authValue: String
        switch auth {
        case .authorized: authValue = "authorized"
        case .denied: authValue = "denied"
        case .restricted: authValue = "restricted"
        case .notDetermined: authValue = "notDetermined"
        @unknown default: authValue = "unknown"
        }
        var result: [String: Any] = ["ok": true, "authorization": authValue]
        if auth == .authorized {
            result["canPlayCatalog"] = try await MusicSubscription.current.canPlayCatalogContent
        }
        return result
    }
    func execute(_ command: Command) async -> [String: Any] {
        guard ["status", "authorize", "play", "pause", "resume", "next", "previous", "disconnect"].contains(command.action),
              command.id.count <= 80 else { return failure("invalid", "Comando no válido.") }
        let query = (command.query ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        guard query.count <= 120, !query.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else {
            return failure("invalid", "Consulta no válida.")
        }
        do {
            if command.action == "disconnect" {
                player.stop()
                player.queue = ApplicationMusicPlayer.Queue(for: [Song]())
                return ["ok": true, "message": "Reproducción detenida. Puedes revocar el acceso en Ajustes del Sistema."]
            }
            if command.action == "authorize" {
                NSApplication.shared.activate(ignoringOtherApps: true)
                _ = await MusicAuthorization.request()
                return try await status()
            }
            if command.action == "status" { return try await status() }
            guard MusicAuthorization.currentStatus == .authorized else {
                return failure("authorization", "Conecta Apple Music desde Ajustes. Si denegaste el permiso, revísalo en Privacidad y seguridad → Contenido multimedia y Apple Music.")
            }
            if command.action == "pause" {
                player.pause()
                return ["ok": true, "message": "Música en pausa."]
            }
            guard try await MusicSubscription.current.canPlayCatalogContent else {
                return failure("subscription", "Tu cuenta necesita una suscripción activa de Apple Music para reproducir el catálogo.")
            }
            switch command.action {
            case "play":
                guard !query.isEmpty else { return failure("invalid", "Indica una canción o artista.") }
                var request = MusicCatalogSearchRequest(term: query, types: [Song.self, Artist.self])
                request.limit = 20
                let response = try await request.response()
                var songs = Array(response.songs)
                let normalized = query.folding(options: [.diacriticInsensitive, .caseInsensitive], locale: .current)
                if let artist = response.artists.first(where: {
                    $0.name.folding(options: [.diacriticInsensitive, .caseInsensitive], locale: .current) == normalized
                }) {
                    let detailed = try await artist.with([.topSongs])
                    songs = Array(detailed.topSongs ?? MusicItemCollection<Song>())
                }
                songs = songs.filter { $0.playParameters != nil }
                guard !songs.isEmpty else {
                    return failure("not_found", "No encontré canciones reproducibles para esa consulta en el catálogo de tu región.")
                }
                player.queue = ApplicationMusicPlayer.Queue(for: songs)
                try await player.play()
            case "resume": try await player.play()
            case "next": try await player.skipToNextEntry()
            case "previous": try await player.skipToPreviousEntry()
            default: return failure("invalid", "Comando no válido.")
            }
            for _ in 0..<10 {
                if player.state.playbackStatus == .playing { break }
                try await Task.sleep(nanoseconds: 200_000_000)
            }
            let title = player.queue.currentEntry?.title ?? "Apple Music"
            let subtitle = player.queue.currentEntry?.subtitle ?? ""
            let playing = player.state.playbackStatus == .playing
            return ["ok": true, "playing": playing,
                    "message": playing ? "Reproduciendo: \(title)\(subtitle.isEmpty ? "" : " — " + subtitle)" : "Apple Music recibió la solicitud; la reproducción todavía no está confirmada."]
        } catch {
            // Do not log tokens or return framework error bodies to a model.
            return failure("musickit", "MusicKit no pudo completar la acción. Revisa conexión, cuenta, suscripción y que el App ID firmado tenga MusicKit habilitado.")
        }
    }
}

@main
struct VoxelMusic {
    static func main() {
        let app = NSApplication.shared
        let delegate = Bridge()
        app.setActivationPolicy(.accessory)
        app.delegate = delegate
        withExtendedLifetime(delegate) { app.run() }
    }
}
