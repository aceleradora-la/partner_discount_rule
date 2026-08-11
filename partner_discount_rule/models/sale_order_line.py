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

    # Depends acotado a la PROPIA linea, como el estandar de Odoo: asi un
    # descuento tipeado a mano no se borra al tocar OTRAS lineas del pedido.
    # Cambiar la cantidad o el producto de ESTA linea si dispara el recalculo
    # y pisa el descuento (comportamiento estandar).
    #
    # Consecuencia: una regla por monto minimo del pedido se evalua cuando
    # cambia esta linea (o al crearla) contra el total del momento, no cuando
    # cambian otras lineas. Es el precio de respetar el descuento manual.
    #
    # No agregar order_id.date_order: action_confirm() lo reescribe y
    # dispararia un recomputo al confirmar.
    @api.depends(
        "order_id.partner_id",
        "product_id",
        "product_uom_qty",
    )
    def _compute_discount(self):
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
