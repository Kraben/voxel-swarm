import SwiftUI

struct ContentView: View {
    @ObservedObject var service: CoreService
    var body: some View {
            Group {
                if let url = service.url {
                    CoreWebView(url:url).id(url)
                } else {
                    VStack(spacing:18) {
                        Image("voxels_core").resizable().scaledToFit().frame(width:112,height:112).clipShape(Circle()).accessibilityLabel("Enjambre de Vóxeles holográfico")
                        Text("Enjambre de Vóxeles").font(.largeTitle.bold())
                        if let error = service.error {
                            Text(error).multilineTextAlignment(.center).frame(maxWidth:440)
                            Button("Reintentar") { service.start() }
                            Button("Abrir registro") { NSWorkspace.shared.open(service.support.appendingPathComponent("server.log")) }
                        } else { ProgressView(); Text("Enlace de telemetría activo…").foregroundStyle(.secondary) }
                    }.frame(maxWidth:.infinity,maxHeight:.infinity)
                }
            }.frame(minWidth:800,minHeight:700).background(Color.black).preferredColorScheme(.dark)

    }
}
