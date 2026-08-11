from odoo import api, fields, models
from odoo.tools import float_compare


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
    rule_discount_applied = fields.Float(
        string="Descuento aplicado por regla",
        digits="Discount",
        readonly=True,
        copy=False,
        help="Último % de descuento que escribió una regla en la línea. Si "
             "el descuento vigente difiere de este valor, el usuario lo "
             "sobreescribió a mano y su valor prima sobre la regla.",
    )

    def _discount_manually_overridden(self):
        """El usuario sobreescribió el descuento que había puesto una regla."""
        self.ensure_one()
        prec = self.env["decimal.precision"].precision_get("Discount")
        return bool(self.discount_rule_id) and float_compare(
            self.discount, self.rule_discount_applied, precision_digits=prec
        ) != 0

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
        # Estado previo a que super() reescriba el descuento. Se usa para:
        # 1) no pisar un descuento manual en una linea sin regla (super() lo
        #    resetea a 0 y hay que reponerlo);
        # 2) respetar la sobreescritura manual de un descuento de regla: si el
        #    usuario cambio el valor que la regla habia puesto, prima el manual
        #    hasta que cambie el producto (reset natural, como en Odoo).
        empty_rule = self.env["partner.discount.rule"].browse()
        previous = {
            line: (
                line.discount,
                line.rule_discount_applied,
                line.discount_rule_id or empty_rule,
                line.product_id,
            )
            for line in self
        }
        super()._compute_discount()
        # sudo(): la resolucion de reglas no debe fallar para usuarios sin
        # permiso de lectura sobre partner.discount.rule (portal, website).
        rule_model = self.env["partner.discount.rule"].sudo()
        order_amounts = {}
        for line in self:
            prev_discount, prev_applied, prev_rule, prev_product = previous.get(
                line, (0.0, 0.0, empty_rule, line.product_id)
            )
            line.discount_rule_id = False
            line.rule_discount_applied = 0.0
            if line.display_type or not line.product_id or not line.order_id.partner_id:
                continue

            # Sobreescritura manual: mientras no cambie el producto, si antes
            # gobernaba una regla y el descuento vigente difiere del que la
            # regla habia aplicado, el usuario lo cambio a mano -> prima.
            if prev_product == line.product_id and prev_rule and float_compare(
                prev_discount,
                prev_applied,
                precision_digits=self.env["decimal.precision"].precision_get(
                    "Discount"
                ),
            ) != 0:
                line.discount = prev_discount
                line.discount_rule_id = prev_rule.id
                line.rule_discount_applied = prev_applied
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
                line.rule_discount_applied = line.discount
                continue
            # Sin regla: si el descuento anterior era manual (no lo puso una
            # regla) y super() lo dejo en cero, se restablece. Un descuento
            # que antes venia de una regla se deja como lo dejo super() —
            # corresponde que caiga si la regla ya no aplica.
            if not prev_rule and prev_discount and not line.discount:
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
