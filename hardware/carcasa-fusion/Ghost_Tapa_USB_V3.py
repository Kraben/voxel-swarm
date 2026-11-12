"""Tapa posterior Ghost V3 con hueco USB-C estimado de 10.34 x 4.56 mm.
Genera SOLO la tapa en otro documento. Ejecutar dentro de Autodesk Fusion.
Conserva la geometría de unión, guía, clips, rejilla y cuna de Ghost_Audio_V3.
Compatible geométricamente con V3 de 90 mm a escala 100 %, sin ajustes manuales.
El tamaño del conector se estimó por el usuario; no está medido.
Hueco paralelo a Z, situado en Y=-30 mm: sin saliente ni alojamiento de tuerca.
No incluye soporte de batería ni sujeción del cable. No modifica el frontal.
Las dimensiones del hueco son su proyección perpendicular al eje de inserción.
"""
import math
import traceback
import adsk.core
import adsk.fusion


CONFIG = {
    'diametro_nucleo': 90.0,
    'pared': 2.4,
    'z_union_tapa': -12.0,
    'holgura_union': 0.30,       # Separación axial y radial; probar impresión.
    'alto_guia_tapa': 4.0,      # Guía de centrado, NO cierre a presión validado.
    'espesor_guia': 1.5,
    'diametro_ojo': 33.0,       # Apertura provisional; confirmar área visible.
    'radio_bisel': 23.0,
    'z_frente': 38.0,
    'alto_bisel': 2.0,
    'gap_corazas': 6.0,
    'espesor_corazas': 3.0,
    'ancho_coraza': 36.0,
    'profundidad_coraza': 30.0,
    'separacion_vista': 0.0,   # 0 = ensamblado; 20 = piezas separadas, en mm.
    'holgura_bisel': 0.30,     # Holgura radial del alojamiento provisional.
    # ESP32 confirmado por usuario (no incluye la PCB personalizada).
    'esp32_x': 21.0,
    'esp32_y': 17.8,
    # Dimensiones exteriores confirmadas por el usuario.
    'pcb_x': 30.92,
    'pcb_y': 27.56,
    'pcb_alto': 12.0,           # NO medido: incluye reserva para pines.
    'pcb_z': 2.0,
    # 36.4 procede del script original; NO confirma dimensiones del módulo.
    'pantalla_pcb_x': 36.4,
    'pantalla_pcb_y': 36.4,
    'pantalla_alto': 10.0,
    'pantalla_z': 22.0,
    'holgura_electronica': 0.5,
    'pcb_espesor': 1.6,
    'altavoz_diametro': 40.0,
    'altavoz_fondo': 18.0,
    'altavoz_frente_z': -35.0,
    'micro_ancho': 14.0,
    'micro_alto_reserva': 6.0,   # Provisional, con conexiones.
    'amplificador_x': 22.0,     # Reserva, NO dimensiones confirmadas.
    'amplificador_y': 22.0,
    'amplificador_alto': 12.0,
    'usb_ancho': 10.34,
    'usb_alto': 4.56,
    'usb_radio': 1.0,
    'usb_centro_y': -30.0,  # Fuera de la bocina, en el sector inferior.
    'clip_saliente': 0.15,     # Encaje provisional: requiere probeta en PLA.

}


def run(context):
    ui = None
    paso = 'Inicio'
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        c = CONFIG
        r = c['diametro_nucleo'] / 2
        ri = r - c['pared']
        eye = c['diametro_ojo'] / 2
        cut = c['z_union_tapa']
        gap = c['holgura_union']
        assert 0 < ri < r, 'Revisa pared y diámetro.'
        assert -ri < cut < 0, 'La unión debe quedar en la mitad trasera.'
        assert 0 < eye < c['radio_bisel'] < r, 'Revisa el bisel.'
        assert 0 < c['z_frente'] < r, 'Revisa el plano frontal.'
        assert gap > 0, 'Usa una holgura positiva.'

        # Se construye todo en memoria antes de abrir el nuevo documento.
        mgr = adsk.fusion.TemporaryBRepManager.get()
        B = adsk.fusion.BooleanTypes

        def p(x, y, z):
            return adsk.core.Point3D.create(x / 10, y / 10, z / 10)

        def sphere(radius):
            return mgr.createSphere(p(0, 0, 0), radius / 10)

        def box(x, y, z, sx, sy, sz):
            obb = adsk.core.OrientedBoundingBox3D.create(
                p(x, y, z), adsk.core.Vector3D.create(1, 0, 0),
                adsk.core.Vector3D.create(0, 1, 0), sx / 10, sy / 10, sz / 10)
            return mgr.createBox(obb)

        def cylinder(a, b, radius):
            return mgr.createCylinderOrCone(p(*a), radius / 10,
                                           p(*b), radius / 10)

        def boolean(target, tool, operation):
            if target is None or tool is None:
                raise RuntimeError('No se pudo crear un sólido en: ' + paso)
            if not mgr.booleanOperation(target, tool, operation):
                raise RuntimeError('Falló una operación geométrica en: ' + paso)
            return target

        def sub(target, tool):
            return boolean(target, tool, B.DifferenceBooleanType)

        def join(target, tool):
            return boolean(target, tool, B.UnionBooleanType)

        def intersect(target, tool):
            return boolean(target, tool, B.IntersectionBooleanType)

        def slab(body, zmin, zmax):
            return intersect(body, box(0, 0, (zmin + zmax) / 2,
                                       4 * r, 4 * r, zmax - zmin))

        def ring(ro, rin, z0, z1):
            return sub(cylinder((0, 0, z0), (0, 0, z1), ro),
                       cylinder((0, 0, z0 - 1), (0, 0, z1 + 1), rin))

        paso = 'Núcleo hueco y tapa'
        shell = sub(sphere(r), sphere(ri))
        rear = slab(mgr.copy(shell), -r - 1, cut - gap / 2)

        # Guía de centrado original V3, con clips añadidos más abajo.
        guide_r = math.sqrt(ri * ri - (cut - gap / 2) ** 2) - gap
        assert guide_r > c['espesor_guia'], 'Guía demasiado pequeña.'
        guide_bottom = cut - 3.0
        guide_top = cut + c['alto_guia_tapa']
        assert guide_top < 0, 'La guía debe quedar detrás del ecuador.'
        rear = join(rear, ring(guide_r, guide_r - c['espesor_guia'],
                               guide_bottom, guide_top))

        def rotated_z(body, angle):
            result = mgr.copy(body)
            matrix = adsk.core.Matrix3D.create()
            matrix.setToRotation(angle, adsk.core.Vector3D.create(0, 0, 1), p(0, 0, 0))
            if not mgr.transform(result, matrix):
                raise RuntimeError('Fallo al girar pieza: ' + paso)
            return result

        def ball(x, y, z, radius):
            return mgr.createSphere(p(x, y, z), radius / 10)

        paso = 'Clips de tapa: cuatro dedos ranurados y alojamientos'
        # Bolitas de retención en la guía, con dos ranuras por dedo.
        # El encaje es provisional, no equivale a una prueba de fatiga en PLA.
        bz = guide_top - 1.2
        br = 0.85
        inner_at_bump = math.sqrt(ri * ri - bz * bz)
        bump_y = inner_at_bump + c['clip_saliente'] - br
        for n in range(4):
            a = math.pi / 4 + n * math.pi / 2
            bump = ball(0, bump_y, bz, br)
            rear = join(rear, rotated_z(bump, a))
            for x in [-3.0, 3.0]:
                slit = box(x, guide_r, guide_top - 3, 0.8, 6, 6.4)
                rear = sub(rear, rotated_z(slit, a))

        paso = 'Bocina: cuna circular y rejilla trasera'
        sr = c['altavoz_diametro'] / 2
        sz = c['altavoz_frente_z']
        # El aro delantero apoya exclusivamente el borde; abertura libre 36 mm.
        cup = ring(sr+2.2, sr-2, sz-2, sz)
        cup = join(cup, ring(sr+2.2, sr+0.4, sz-0.2, sz+3))
        rear = join(rear, cup)
        for x in [-12, -6, 0, 6, 12]:
            length = 2 * math.sqrt((sr-3)**2 - x*x)
            rear = sub(rear, box(x, 0, -r+5, 2.5, length, 16))
        # Dos orejetas para una abrazadera flexible sobre el borde del altavoz.
        # Las ranuras admiten una brida; no se presiona el cono ni el imán.
        for sign in [-1, 1]:
            ear = box(sign*(sr+2.0), 0, sz+1, 5, 7, 4)
            ear = sub(ear, box(sign*(sr+2.8), 0, sz+1, 1.6, 4, 6))
            rear = join(rear, ear)

        paso = 'Hueco USB-C redondeado en la tapa posterior'
        uw, uh, ur = c['usb_ancho'], c['usb_alto'], c['usb_radio']
        uy = c['usb_centro_y']
        if not 0 < ur < min(uw, uh) / 2:
            raise ValueError('Radio USB inválido.')
        # Límites conservadores: evita cuna, orejetas y guía de encaje V3.
        if abs(uy) - uh/2 <= sr + 5:
            raise ValueError('El hueco USB queda demasiado cerca de la bocina.')
        radial_max = math.hypot(uw/2, abs(uy)+uh/2)
        if radial_max >= guide_r - c['espesor_guia'] - 2:
            raise ValueError('El hueco USB queda demasiado cerca de la guía.')
        z0, z1 = -r - 5, cut - 4
        if radial_max**2 + z1**2 >= ri**2:
            raise ValueError('El cortador no alcanza la cavidad interior.')
        zc, depth = (z0+z1)/2, z1-z0
        hole = box(0, uy, zc, uw-2*ur, uh, depth)
        hole = join(hole, box(0, uy, zc, uw, uh-2*ur, depth))
        for x in [-(uw/2-ur), uw/2-ur]:
            for y in [uy-(uh/2-ur), uy+(uh/2-ur)]:
                hole = join(hole, cylinder((x,y,z0), (x,y,z1), ur))
        rear = sub(rear, hole)

        paso = 'Creación de documento con la tapa únicamente'
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError('No se pudo crear un diseño Fusion.')
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        occ = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = '02_Tapa_bocina_USB_compatible_V3'
        body = occ.component.bRepBodies.add(rear)
        if not body:
            raise RuntimeError('No se pudo añadir el cuerpo de la tapa.')
        body.name = 'Tapa_posterior_USB'
        app.activeViewport.fit()
        ui.messageBox(
            'Tapa posterior con hueco USB creada en otro documento.\n\n'
            'Se conserva la unión V3: núcleo 90 mm, pared 2.4 mm,\n'
            'guía y cuatro clips originales.\n'
            'Hueco estimado: {usb_ancho} x {usb_alto} mm, radio {usb_radio} mm.\n'
            'Exporta solo esta tapa, en milímetros y a escala 100 %.\n\n'
            'Comprobar encaje del cable antes de fijarlo.\n'
            'Esta versión añade el paso; no incluye abrazadera USB\n'
            'ni alojamiento de batería.'.format(**c))
    except Exception:
        if ui:
            ui.messageBox('Error en: ' + paso + '\n\n' + traceback.format_exc())
        else:
            raise
