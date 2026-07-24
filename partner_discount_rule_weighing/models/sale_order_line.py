from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _discount_rule_extra(self):
        extra = super()._discount_rule_extra()
        if self.product_id.is_weighed_product:
            # Peso estimado de la línea (piezas x peso estándar), en la UdM
            # de pesaje del producto. A la cotización aún no hay pesaje real.
            extra["weight"] = self.total_planned_weight
        return extra
