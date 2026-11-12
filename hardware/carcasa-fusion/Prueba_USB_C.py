"""Fusion: placa de prueba para el hueco USB-C del Ghost.
Medidas en mm. Crea un documento nuevo en cada ejecución.
El hueco es una estimación visual, no una dimensión confirmada del cable.
"""
import traceback
import adsk.core
import adsk.fusion

# AJUSTES EN MILIMETROS
ANCHO_HUECO = 10.34
ALTO_HUECO = 4.56
RADIO_ESQUINA = 1.0
ESPESOR_PLACA = 2.4
ANCHO_PLACA = 30.0
ALTO_PLACA = 20.0


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        w, h, r = ANCHO_HUECO, ALTO_HUECO, RADIO_ESQUINA
        if not (0 < r < min(w, h) / 2):
            raise ValueError('El radio debe ser menor que la mitad del hueco.')
        if not (ANCHO_PLACA > w + 4 and ALTO_PLACA > h + 4
                and ESPESOR_PLACA > 0):
            raise ValueError('Revisa el tamaño y espesor de la placa.')
        mgr = adsk.fusion.TemporaryBRepManager.get()
        B = adsk.fusion.BooleanTypes

        def point(x, y, z):
            return adsk.core.Point3D.create(x / 10, y / 10, z / 10)

        def box(sx, sy, sz):
            bounds = adsk.core.OrientedBoundingBox3D.create(
                point(0, 0, ESPESOR_PLACA / 2),
                adsk.core.Vector3D.create(1, 0, 0),
                adsk.core.Vector3D.create(0, 1, 0),
                sx / 10, sy / 10, sz / 10)
            return mgr.createBox(bounds)

        def boolean(target, tool, operation):
            if not mgr.booleanOperation(target, tool, operation):
                raise RuntimeError('No se pudo construir el hueco de prueba.')
            return target

        plate = box(ANCHO_PLACA, ALTO_PLACA, ESPESOR_PLACA)
        # Dos rectángulos y cuatro cilindros forman un hueco redondeado.
        hole = box(w - 2*r, h, ESPESOR_PLACA + 2)
        hole = boolean(hole, box(w, h - 2*r, ESPESOR_PLACA + 2),
                       B.UnionBooleanType)
        for x in [-(w/2-r), w/2-r]:
            for y in [-(h/2-r), h/2-r]:
                corner = mgr.createCylinderOrCone(
                    point(x, y, -1), r/10,
                    point(x, y, ESPESOR_PLACA+1), r/10)
                hole = boolean(hole, corner, B.UnionBooleanType)
        plate = boolean(plate, hole, B.DifferenceBooleanType)

        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError('No se pudo crear el documento Fusion.')
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        occ = design.rootComponent.occurrences.addNewComponent(
            adsk.core.Matrix3D.create())
        occ.component.name = 'Prueba_USB_C_{}x{}'.format(w, h)
        body = occ.component.bRepBodies.add(plate)
        body.name = 'Placa_prueba_USB_C'
        app.activeViewport.fit()
        ui.messageBox(
            'Placa de prueba creada.\n'
            'Exterior: {} x {} x {} mm.\n'
            'Hueco: {} x {} mm; radio {} mm.\n\n'
            'Exporta este componente como STL en milímetros.\n'
            'Prueba el conector hembra y que el macho entre completamente.'
            .format(ANCHO_PLACA, ALTO_PLACA, ESPESOR_PLACA, w, h, r))
    except Exception:
        if ui:
            ui.messageBox('Error:\n' + traceback.format_exc())
        else:
            raise
