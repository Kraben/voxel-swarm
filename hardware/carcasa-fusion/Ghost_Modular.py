"""Ghost modular: siete componentes exteriores independientes para Fusion.

Todas las medidas de CONFIG están en mm. Cambiar CONFIG y volver a ejecutar
crea OTRO documento; no modifica el diseño abierto. Geometría directa, sin
historial paramétrico: los parámetros se editan aquí, no en la tabla de Fusion.
Primera etapa: piezas exteriores separadas, sin anclajes ni soporte interior.
No se han definido tornillos, alojamiento de bocina/micrófono ni paso USB.
"""
import math
import traceback
import adsk.core
import adsk.fusion


CONFIG = {
    'diametro_nucleo': 70.0,
    'pared': 2.4,
    'z_union_tapa': -12.0,
    'holgura_union': 0.30,       # Separación axial y radial; probar impresión.
    'alto_guia_tapa': 4.0,      # Guía de centrado, NO cierre a presión validado.
    'espesor_guia': 1.5,
    'diametro_ojo': 33.0,       # Apertura provisional; confirmar área visible.
    'radio_bisel': 23.0,
    'z_frente': 30.0,
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
    # Se supone provisionalmente que la captura mide la PCB personalizada.
    'pcb_x': 30.92,
    'pcb_y': 27.56,
    'pcb_alto': 12.0,           # NO medido: incluye reserva para pines.
    'pcb_z': -6.0,
    # 36.4 procede del script original; NO confirma dimensiones del módulo.
    'pantalla_pcb_x': 36.4,
    'pantalla_pcb_y': 36.4,
    'pantalla_alto': 10.0,
    'pantalla_z': 13.0,
    'holgura_electronica': 0.5,
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
        front = slab(mgr.copy(shell), cut + gap / 2, c['z_frente'])
        rear = slab(mgr.copy(shell), -r - 1, cut - gap / 2)

        # La guía cilíndrica entra en la mitad frontal. Su base solapa la
        # pared posterior; no hay rosca, imanes ni retén en este prototipo.
        guide_r = math.sqrt(ri * ri - (cut - gap / 2) ** 2) - gap
        assert guide_r > c['espesor_guia'], 'Guía demasiado pequeña.'
        guide_bottom = cut - 3.0
        guide_top = cut + c['alto_guia_tapa']
        assert guide_top < 0, 'La guía debe quedar detrás del ecuador.'
        rear = join(rear, ring(guide_r, guide_r - c['espesor_guia'],
                               guide_bottom, guide_top))

        paso = 'Ojo abierto hacia el exterior y bisel'
        # Corte real de la pared frontal, desde el centro hasta fuera.
        front = sub(front, cylinder((0, 0, 0), (0, 0, r + 10), eye))
        bezel = ring(c['radio_bisel'], eye, c['z_frente'] - 4,
                     c['z_frente'] + c['alto_bisel'])
        # Alojamiento para el bisel independiente: evita sólidos solapados.
        front = sub(front, cylinder(
            (0, 0, c['z_frente'] - 4), (0, 0, r + 10),
            c['radio_bisel'] + c['holgura_bisel']))

        paso = 'Cuatro corazas independientes'
        ra = r + c['gap_corazas']
        ro = ra + c['espesor_corazas']
        petal = sub(sphere(ro), sphere(ra))
        petal = intersect(petal, box(0, ro / 2, 0, c['ancho_coraza'],
                                     ro, c['profundidad_coraza']))
        spread = c['separacion_vista']
        assert spread >= 0, 'La separación de vista debe ser positiva o cero.'
        parts = [
            ('01_Nucleo_frontal', front, (0, 0, 0)),
            ('02_Tapa_trasera', rear, (0, 0, -spread)),
            ('03_Bisel_ojo', bezel, (0, 0, spread)),
        ]
        names = ['04_Coraza_superior', '05_Coraza_izquierda',
                 '06_Coraza_inferior', '07_Coraza_derecha']
        for n, name in enumerate(names):
            angle = n * math.pi / 2
            rotated = mgr.copy(petal)
            transform = adsk.core.Matrix3D.create()
            transform.setToRotation(angle, adsk.core.Vector3D.create(0, 0, 1),
                                    p(0, 0, 0))
            if not mgr.transform(rotated, transform):
                raise RuntimeError('No se pudo girar una coraza.')
            parts.append((name, rotated,
                          (-spread * math.sin(angle), spread * math.cos(angle), 0)))

        paso = 'Comprobación de reservas de electrónica'
        envelopes = [
            ('REF_PCB_personalizada_NO_IMPRIMIR', c['pcb_x'], c['pcb_y'],
             c['pcb_alto'], c['pcb_z']),
            ('REF_Modulo_pantalla_NO_IMPRIMIR', c['pantalla_pcb_x'],
             c['pantalla_pcb_y'], c['pantalla_alto'], c['pantalla_z']),
        ]
        warnings = []
        margin = c['holgura_electronica']
        for name, x, y, h, z in envelopes:
            assert min(x, y, h) > 0, 'Medidas de electrónica inválidas.'
            # El vértice más lejano debe quedar dentro de la cavidad.
            farthest = math.sqrt((x / 2 + margin) ** 2 +
                                 (y / 2 + margin) ** 2 +
                                 (abs(z) + h / 2 + margin) ** 2)
            if farthest > ri:
                warnings.append(name + ': excede la cavidad esférica.')
        board_top = c['pcb_z'] + c['pcb_alto'] / 2
        screen_bottom = c['pantalla_z'] - c['pantalla_alto'] / 2
        if board_top + 2 * margin > screen_bottom:
            warnings.append('Las reservas de pantalla y PCB se solapan.')
        pcb_radius = math.hypot(c['pcb_x'] / 2 + margin,
                                c['pcb_y'] / 2 + margin)
        if (c['pcb_z'] - c['pcb_alto'] / 2 - margin < guide_top
                and board_top + margin > guide_bottom
                and pcb_radius > guide_r - c['espesor_guia']):
            warnings.append('Revisar PCB contra la guía de la tapa.')

        paso = 'Publicación en un documento nuevo'
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError('El nuevo documento no es un diseño Fusion.')
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        root = design.rootComponent

        def component(name, offset=(0, 0, 0)):
            placement = adsk.core.Matrix3D.create()
            placement.translation = adsk.core.Vector3D.create(
                offset[0] / 10, offset[1] / 10, offset[2] / 10)
            occ = root.occurrences.addNewComponent(placement)
            occ.component.name = name
            return occ.component

        for name, body, offset in parts:
            comp = component(name, offset)
            result = comp.bRepBodies.add(body)
            if not result:
                raise RuntimeError('No se pudo añadir: ' + name)
            result.name = name

        refs = component('REFERENCIAS_ocultas_NO_IMPRIMIR')
        for name, x, y, h, z in envelopes:
            result = refs.bRepBodies.add(box(0, 0, z, x, y, h))
            result.name = name
            result.isLightBulbOn = False
        # Contorno del ESP32 dentro de la reserva de la placa personalizada.
        result = refs.bRepBodies.add(box(0, 0, c['pcb_z'],
                                        c['esp32_x'], c['esp32_y'], 1.0))
        result.name = 'REF_ESP32_21x17_8_solo_contorno_NO_IMPRIMIR'
        result.isLightBulbOn = False

        app.activeViewport.fit()
        summary = ('Prototipo creado en otro documento.\n\n'
                   'Núcleo: {diametro_nucleo} mm; pared: {pared} mm.\n'
                   '7 componentes: núcleo, tapa, bisel y 4 corazas.\n'
                   'Las referencias de electrónica están ocultas.\n\n'
                   'PENDIENTE: confirmar PCB, módulo de pantalla, alturas,\n'
                   'micrófono, bocina, cableado y fijaciones antes de imprimir.\n'
                   'Corazas y bisel separados, todavía sin tornillos ni anclajes.\n'
                   'La pantalla está retranqueada; ajustar su posición\n'
                   'y soportes al medir el módulo real.').format(**c)
        if warnings:
            summary += '\n\nREVISAR:\n' + '\n'.join(warnings)
        ui.messageBox(summary)
    except Exception:
        if ui:
            ui.messageBox('Error en: ' + paso + '\n\n' + traceback.format_exc())
        else:
            raise
