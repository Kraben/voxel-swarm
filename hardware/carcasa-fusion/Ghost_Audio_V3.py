"""Ghost Audio V3: montaje preliminar, componentes independientes y cierres.

Todas las medidas de CONFIG están en mm. Cambiar CONFIG y volver a ejecutar
crea OTRO documento; no modifica el diseño abierto. Geometría directa, sin
historial paramétrico: los parámetros se editan aquí, no en la tabla de Fusion.
Incluye bandeja PCB, soportes de paneles, clips de tapa/bisel y audio.
No validado para impresión. Las alturas de módulos y sus fijaciones son provisionales.
Esta distribución usa un núcleo de 90 mm. No reducir sin revisar interferencias.
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
            front = sub(front, rotated_z(ball(0, bump_y, bz, br + gap), a))
            for x in [-3.0, 3.0]:
                slit = box(x, guide_r, guide_top - 3, 0.8, 6, 6.4)
                rear = sub(rear, rotated_z(slit, a))

        paso = 'Clips del aro del ojo'
        bz = c['z_frente'] - 2
        br = 0.75
        bump_y = c['radio_bisel'] + c['holgura_bisel'] + c['clip_saliente'] - br
        for n in range(3):
            a = n * 2 * math.pi / 3
            bezel = join(bezel, rotated_z(ball(0, bump_y, bz, br), a))
            front = sub(front, rotated_z(ball(0, bump_y, bz, br + gap), a))
            for x in [-3.0, 3.0]:
                bezel = sub(bezel, rotated_z(box(x, (eye+c['radio_bisel'])/2,
                    c['z_frente'] - 2.1, 0.8, c['radio_bisel']-eye+3, 4.4), a))

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

        paso = 'Bandeja PCB con canales de 1.6 mm y tope'
        w, d = c['pcb_x'], c['pcb_y']
        # PCB desnuda: Z=-4..-2.4; componentes hacia +Z.
        zbase = -5.0
        tray = box(0, 0, zbase, w+5, d+4, 2)
        for sign in [-1, 1]:
            rail = box(sign*(w/2+0.35), 0, -3.0, 3.1, d+4, 4)
            groove = box(sign*(w/2-0.6), -1, -4+c['pcb_espesor']/2,
                         1.8, d+7, c['pcb_espesor']+0.5)
            tray = join(tray, sub(rail, groove))
        tray = join(tray, box(0, d/2+1, -3.0, w+4, 2, 4))
        # Cuatro orejas y apoyos en el núcleo. Pilotos 2.0, paso 2.5 mm.
        for sign in [-1, 1]:
            for y in [-10, 10]:
                x = sign*(w/2+8)
                ear = box(sign*(w/2+4), y, -5, 11, 6, 2)
                tray = join(tray, ear)
                tray = sub(tray, cylinder((x,y,-8),(x,y,-2),1.25))
                arm = box(sign*(abs(x)+(r-abs(x))/2), y, -8,
                          r-abs(x)+5, 6, 4)
                arm = intersect(arm, sphere(r))
                front = join(front, arm)
                front = sub(front, cylinder((x,y,-11),(x,y,-5.8),1.0))

        paso = 'Cuna abierta para MAX98357A'
        aw = c['amplificador_x']
        ah = c['amplificador_y']
        # Reserva orientada X-Z; conexiones salen hacia +Y.
        amp = box(0, 19, 0, aw+4, 4, ah+4)
        for sign in [-1, 1]:
            amp = join(amp, box(sign*(aw/2+1.3), 23, 0, 2, 8, ah+4))
        amp = join(amp, box(0, 23, -ah/2-1, aw+4, 8, 2))
        # Ranuras para brida en la espalda de la cuna.
        for x in [-7, 7]:
            amp = sub(amp, box(x, 19, 0, 2, 6, 8))
        brace = box(0, 32, -ah/2+1, 6, 26, 2)
        brace = intersect(brace, sphere(r))
        amp = join(amp, brace)
        front = join(front, amp)

        paso = 'Cuna de micrófono y conducto lateral provisional'
        mw = c['micro_ancho']
        mic = box(-30, 0, 8, mw+4, mw+4, 2)
        for y in [-mw/2-1.3, mw/2+1.3]:
            mic = join(mic, box(-30,y,10,mw+4,2,4))
        brace = intersect(box(-38,0,8,16,6,4), sphere(r))
        mic = join(mic,brace)
        front = join(front,mic)
        # Puerto inferior supuesto en el centro del módulo: confirmar su posición.
        front = sub(front,cylinder((-30,0,7),(-30,0,12),1.5))
        front = sub(front,cylinder((-r-1,0,8),(-29.5,0,8),1.5))

        paso = 'Paneles con brazos, alojamientos y pasadores'
        ra = r + c['gap_corazas']
        ro = ra + c['espesor_corazas']
        petal = sub(sphere(ro), sphere(ra))
        petal = intersect(petal, box(0,ro/2,0,c['ancho_coraza'],ro,c['profundidad_coraza']))
        # Macho rectangular en el núcleo; hembra en cada panel, sin solapamiento.
        peg = box(0,r+2,5,6,10,6)
        boss = box(0,ra+0.5,5,10,7,10)
        petal = join(petal,boss)
        petal = sub(petal,box(0,r+2,5,6.6,11,6.6))
        # Paso transversal para pasador/tornillo de 2 mm (agujero 2.4 mm).
        hole = cylinder((-8,ra-1,5),(8,ra-1,5),1.2)
        peg = sub(peg,mgr.copy(hole))
        petal = sub(petal,mgr.copy(hole))
        spread = c['separacion_vista']
        panel_parts = []
        names = ['04_Coraza_superior','05_Coraza_izquierda',
                 '06_Coraza_inferior','07_Coraza_derecha']
        for n,name in enumerate(names):
            a=n*math.pi/2
            front=join(front,rotated_z(peg,a))
            panel_parts.append((name,rotated_z(petal,a),
                                (-spread*math.sin(a),spread*math.cos(a),0)))
        parts=[('01_Nucleo_soportes_audio',front,(0,0,0)),
               ('02_Tapa_bocina',rear,(0,0,-spread)),
               ('03_Bisel_clips',bezel,(0,0,spread)),
               ('08_Bandeja_PCB',tray,(0,0,-2*spread))]+panel_parts

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
        audio_refs = [
            ('REF_Altavoz_40x18', cylinder((0,0,sz),(0,0,sz+c['altavoz_fondo']),sr)),
            ('REF_MAX98357A_reserva_NO_MEDIDA', box(0,27,0,
                 c['amplificador_x'],c['amplificador_alto'],c['amplificador_y'])),
            ('REF_INMP441', box(-30,0,12,c['micro_ancho'],c['micro_ancho'],
                                c['micro_alto_reserva'])),
            ('REF_PCB_desnuda_1_6', box(0,0,-4+c['pcb_espesor']/2,
                                      c['pcb_x'],c['pcb_y'],c['pcb_espesor'])),
        ]
        for name, body in audio_refs:
            result = refs.bRepBodies.add(body)
            result.name = name
            result.isLightBulbOn = False
        # Contorno del ESP32 dentro de la reserva de la placa personalizada.
        result = refs.bRepBodies.add(box(0, 0, c['pcb_z'],
                                        c['esp32_x'], c['esp32_y'], 1.0))
        result.name = 'REF_ESP32_21x17_8_solo_contorno_NO_IMPRIMIR'
        result.isLightBulbOn = False

        app.activeViewport.fit()
        summary = ('Ghost Audio V3 creado en documento nuevo.\n'
                   'Núcleo {diametro_nucleo} mm. Componentes separados.\n'
                   'Tapa y ojo con clips de prueba; paneles con brazos y pasadores.\n'
                   'Bandeja PCB, cuna de altavoz, amplificador y micrófono.\n\n'
                   'Prototipo: validar en Fusion antes de imprimir.\n'
                   'Alturas de módulos, puerto del micrófono y fijaciones pendientes.\n'
                   'Probar los encajes en PLA antes de imprimir el conjunto.\n'
                   'La pantalla aún requiere sujeción adaptada al módulo real.'
                   ).format(**c)
        if warnings:
            summary += '\n\nREVISAR:\n' + '\n'.join(warnings)
        ui.messageBox(summary)
    except Exception:
        if ui:
            ui.messageBox('Error en: ' + paso + '\n\n' + traceback.format_exc())
        else:
            raise
