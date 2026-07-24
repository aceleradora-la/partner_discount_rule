from . import models

from odoo.exceptions import UserError


def pre_init_hook(env):
    """Instalar este puente con partner_discount_rule desactualizado rompe
    con un ParseError criptico (la vista del formulario guardada en la base
    referencia campos que el modelo nuevo ya no tiene). Cortamos antes, con
    instrucciones claras."""
    module = env["ir.module.module"].search(
        [("name", "=", "partner_discount_rule")], limit=1
    )
    version = module.latest_version or ""
    # latest_version es la version INSTALADA (ej: 19.0.1.2.0). Vacia cuando
    # el modulo base se instala recien en esta misma transaccion: en ese caso
    # no hay vistas viejas y no hace falta chequear nada.
    if not version:
        return
    try:
        functional = tuple(int(p) for p in version.split(".")[2:5])
    except ValueError:
        return
    if functional < (1, 3, 0):
        raise UserError(
            "Antes de instalar 'Reglas de Descuento por Cliente - Pesaje' "
            "hay que ACTUALIZAR el módulo 'Reglas de Descuento por Cliente': "
            "Apps → Reglas de Descuento por Cliente → Actualizar. "
            "La versión instalada (%s) es anterior a la selección múltiple "
            "de productos, y sus vistas guardadas son incompatibles con el "
            "código nuevo. Al actualizarlo, este módulo se instala solo." % version
        )
