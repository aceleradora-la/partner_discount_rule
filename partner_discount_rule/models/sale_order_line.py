from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Campo simple (no compute almacenado, a propósito: un compute stored
    # dispararía el recálculo masivo de descuentos históricos al actualizar
    # el módulo). Se asigna dentro de _compute_discount; las líneas previas
    # a esta versión quedan sin regla registrada.
    discount_rule_id = fields.Many2one(
        "partner.discount.rule",
        string="Regla de descuento aplicada",
        readonly=True,
        copy=False,
        help="Regla que determinó el descuento de la línea. Vacío si el "
             "descuento vino de la tarifa o fue manual.",
    )

    # El descuento se recalcula ante cambios de CANTIDAD (de esta linea o de
    # cualquier otra del pedido) y de producto/cliente, para que el monto
    # minimo del pedido se re-evalue. Cuando una REGLA aplica, la regla gobierna
    # y pisa el valor (incluido un descuento manual). Cuando NO aplica ninguna
    # regla, el modulo no toca el descuento: un valor tipeado a mano se conserva
    # (super() lo pone en 0 si no hay descuento de tarifa, y aca se restablece).
    # Asi, un cliente sin reglas se comporta como el estandar y no pierde sus
    # descuentos manuales al moverse de linea o guardar.
    #
    # Se depende de las cantidades pero NO de price_unit: price_unit se
    # recalcula solo (es computado) y dispararia recomputos fantasma que
    # borrarian el descuento manual sin que el usuario toque nada.
    #
    # No agregar order_id.date_order: action_confirm() lo reescribe y
    # dispararia un recomputo al confirmar.
    @api.depends(
        "order_id.partner_id",
        "product_id",
        "product_uom_qty",
        "order_id.order_line.product_uom_qty",
    )
    def _compute_discount(self):
        # Descuento y "tenia regla" previos a que super() los reescriba.
        previous = {
            line: (line.discount, bool(line.discount_rule_id)) for line in self
        }
        super()._compute_discount()
        # sudo(): la resolucion de reglas no debe fallar para usuarios sin
        # permiso de lectura sobre partner.discount.rule (portal, website).
        rule_model = self.env["partner.discount.rule"].sudo()
        order_amounts = {}
        for line in self:
            line.discount_rule_id = False
            if line.display_type or not line.product_id or not line.order_id.partner_id:
                continue
            order = line.order_id
            date = order.date_order and order.date_order.date() or None
            if order.id not in order_amounts:
                order_amounts[order.id] = self._get_order_gross_amount(order, date)
            rule = rule_model._get_applicable_rule(
                order.partner_id,
                line.product_id,
                date,
                order.company_id,
                qty=line.product_uom_qty,
                order_amount=order_amounts[order.id],
                extra=line._discount_rule_extra(),
            )
            if rule:
                line.discount = rule._combine_discount(line.discount)
                line.discount_rule_id = rule.id
                continue
            # Sin regla aplicable: preservar un descuento tipeado a mano que
            # super() haya reseteado a 0. Solo si antes NO lo gobernaba una
            # regla (un descuento que venia de una regla debe caer si la regla
            # dejo de aplicar, no restablecerse).
            prev_discount, had_rule = previous.get(line, (0.0, False))
            if not had_rule and prev_discount and not line.discount:
                line.discount = prev_discount

    def _discount_rule_extra(self):
        """Valores adicionales para la resolución de reglas. Los módulos
        puente lo extienden (ej: pesaje aporta el peso estimado)."""
        self.ensure_one()
        return {}

    @api.model
    def _get_order_gross_amount(self, order, date=None):
        """Total del pedido sin impuestos y antes de descuentos, en la moneda
        de la compañía. Se usa el precio bruto (no el descontado) para que las
        reglas con monto mínimo no se desactiven a sí mismas."""
        amount = sum(
            l.price_unit * l.product_uom_qty
            for l in order.order_line
            if not l.display_type
        )
        company_currency = order.company_id.currency_id
        if order.currency_id and order.currency_id != company_currency:
            amount = order.currency_id._convert(
                amount,
                company_currency,
                order.company_id,
                date or fields.Date.context_today(self),
            )
        return amount
