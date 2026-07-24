from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # No agregar order_id.date_order a los depends: action_confirm() reescribe
    # date_order y dispararia un recomputo al confirmar. Los depends sobre las
    # lineas hermanas (order_id.order_line.*) permiten que las reglas con
    # monto minimo de pedido se re-evaluen en todas las lineas cuando
    # cualquiera cambia.
    @api.depends(
        "order_id.partner_id",
        "product_id",
        "product_uom_qty",
        "order_id.order_line.product_uom_qty",
        "order_id.order_line.price_unit",
    )
    def _compute_discount(self):
        super()._compute_discount()
        # sudo(): la resolucion de reglas no debe fallar para usuarios sin
        # permiso de lectura sobre partner.discount.rule (portal, website).
        rule_model = self.env["partner.discount.rule"].sudo()
        order_amounts = {}
        for line in self:
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
