from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # No agregar order_id.date_order a los depends: action_confirm() reescribe
    # date_order y dispararia un recomputo al confirmar, donde el super()
    # pisaria el descuento de la regla con el de la tarifa.
    @api.depends("order_id.partner_id", "product_id")
    def _compute_discount(self):
        super()._compute_discount()
        # sudo(): la resolucion de reglas no debe fallar para usuarios sin
        # permiso de lectura sobre partner.discount.rule (portal, website).
        rule_model = self.env["partner.discount.rule"].sudo()
        for line in self:
            if line.display_type or not line.product_id or not line.order_id.partner_id:
                continue
            if line.order_id.state not in ("draft", "sent"):
                continue
            order = line.order_id
            date = order.date_order and order.date_order.date() or None
            rule = rule_model._get_applicable_rule(
                order.partner_id,
                line.product_id,
                date,
                order.company_id,
            )
            if rule:
                line.discount = rule.discount
