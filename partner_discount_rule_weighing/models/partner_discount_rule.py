from odoo import fields, models


class PartnerDiscountRule(models.Model):
    _inherit = "partner.discount.rule"

    min_qty_mode = fields.Selection(
        [
            ("qty", "Cantidad de la línea"),
            ("weight", "Peso (UdM de pesaje del producto)"),
        ],
        string="Cantidad mínima en",
        default="qty",
        required=True,
        help="Cómo interpretar la cantidad mínima:\n"
             "- Cantidad de la línea: unidades vendidas (comportamiento "
             "estándar).\n"
             "- Peso: para productos pesables compara contra el peso estimado "
             "de la línea (piezas × peso estándar), expresado en la UdM de "
             "pesaje de cada producto (ej: kg). Para productos no pesables "
             "se sigue usando la cantidad de la línea.",
    )

    def _matches_min_qty(self, product, qty, extra):
        self.ensure_one()
        if (
            self.min_qty
            and self.min_qty_mode == "weight"
            and product.is_weighed_product
        ):
            return extra.get("weight", 0.0) >= self.min_qty
        return super()._matches_min_qty(product, qty, extra)
