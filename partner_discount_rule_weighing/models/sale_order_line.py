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

    def _get_weighed_invoice_vals(self, *args, **kwargs):
        """En la factura manda el peso REAL: si la regla que otorgó el
        descuento exigía un mínimo en peso y lo entregado quedó por debajo,
        el descuento se quita de la línea de factura. Si el pesaje se corrige
        y vuelve a superar el mínimo (re-sync de factura borrador), el
        descuento se restablece.

        Se reciben los argumentos sin nombrarlos y se reenvían tal cual: este
        override solo agrega el descuento y no necesita conocer la firma de
        sale_stock_weighing, que ya cambió una vez al sumarse el parámetro
        cumulative y dejó este método rompiendo con TypeError."""
        vals = super()._get_weighed_invoice_vals(*args, **kwargs)
        rule = self.discount_rule_id.sudo()
        if (
            rule
            and rule.min_qty
            and rule.min_qty_mode == "weight"
            and self.product_id.is_weighed_product
        ):
            below_min = self.total_delivered_weight < rule.min_qty
            vals["discount"] = 0.0 if below_min else self.discount
        return vals
