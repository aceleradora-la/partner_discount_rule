from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PartnerDiscountRule(models.Model):
    _name = "partner.discount.rule"
    _description = "Regla de descuento por cliente"
    _order = "sequence, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(
        default=10,
        help="Menor secuencia gana ante empate de especificidad.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    discount = fields.Float(
        string="Descuento (%)",
        required=True,
        digits="Discount",
    )
    combine_mode = fields.Selection(
        [
            ("best", "Mayor beneficio al cliente"),
            ("sum", "Acumulado"),
            ("override", "Sobreescribir"),
        ],
        string="Con descuento de tarifa",
        default="override",
        required=True,
        help="Cómo combinar con el descuento que la lista de precios ya haya "
             "puesto en la columna Descuento de la línea:\n"
             "- Mayor beneficio al cliente: aplica el mayor de los dos.\n"
             "- Acumulado: suma ambos porcentajes (tope 100%).\n"
             "- Sobreescribir: la regla pisa el descuento de la tarifa.",
    )
    date_start = fields.Date(string="Desde")
    date_end = fields.Date(string="Hasta")

    # --- Aplicabilidad: cliente ---
    partner_ids = fields.Many2many(
        "res.partner",
        "partner_discount_rule_partner_rel",
        "rule_id",
        "partner_id",
        string="Clientes",
        domain="[('parent_id', '=', False)]",
    )
    partner_category_ids = fields.Many2many(
        "res.partner.category",
        "partner_discount_rule_tag_rel",
        "rule_id",
        "category_id",
        string="Etiquetas de cliente",
    )

    # --- Aplicabilidad: producto ---
    applied_on = fields.Selection(
        [
            ("0_product_variant", "Variante de producto"),
            ("1_product", "Producto"),
            ("2_product_category", "Categoría de producto"),
            ("3_global", "Todos los productos"),
        ],
        string="Aplicar sobre",
        default="3_global",
        required=True,
    )
    product_id = fields.Many2one("product.product", string="Variante")
    product_tmpl_id = fields.Many2one("product.template", string="Producto")
    categ_id = fields.Many2one(
        "product.category",
        string="Categoría de producto",
        help="Aplica también a las categorías hijas.",
    )

    @api.constrains("discount")
    def _check_discount(self):
        for rule in self:
            if not (0.0 <= rule.discount <= 100.0):
                raise ValidationError("El descuento debe estar entre 0 y 100.")

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rule in self:
            if rule.date_start and rule.date_end and rule.date_start > rule.date_end:
                raise ValidationError("La fecha 'Desde' no puede ser posterior a 'Hasta'.")

    @api.constrains("partner_ids", "partner_category_ids")
    def _check_partner_applicability(self):
        for rule in self:
            if not rule.partner_ids and not rule.partner_category_ids:
                raise ValidationError(
                    "Definí al menos un cliente o una etiqueta de cliente. "
                    "Una regla sin destinatario aplicaría a todos."
                )

    @api.onchange("applied_on")
    def _onchange_applied_on(self):
        if self.applied_on != "0_product_variant":
            self.product_id = False
        if self.applied_on != "1_product":
            self.product_tmpl_id = False
        if self.applied_on != "2_product_category":
            self.categ_id = False

    # ------------------------------------------------------------------
    # Resolución
    # ------------------------------------------------------------------
    def _combine_discount(self, base_discount):
        """Combina el descuento de la regla con el que ya tenga la línea
        (típicamente el de la lista de precios), según combine_mode."""
        self.ensure_one()
        base_discount = base_discount or 0.0
        if self.combine_mode == "best":
            return max(base_discount, self.discount)
        if self.combine_mode == "sum":
            return min(100.0, base_discount + self.discount)
        return self.discount

    def _matches_partner(self, partner):
        """El partner matchea por sí mismo, por su comercial_partner, o por etiqueta."""
        self.ensure_one()
        if not partner:
            return False
        candidates = partner | partner.commercial_partner_id
        if self.partner_ids & candidates:
            return True
        if self.partner_category_ids & candidates.category_id:
            return True
        return False

    def _matches_product(self, product):
        """Devuelve el nivel de especificidad (menor = más específico) o None."""
        self.ensure_one()
        if self.applied_on == "0_product_variant":
            return 0 if product == self.product_id else None
        if self.applied_on == "1_product":
            return 1 if product.product_tmpl_id == self.product_tmpl_id else None
        if self.applied_on == "2_product_category":
            categ = product.categ_id
            while categ:
                if categ == self.categ_id:
                    return 2
                categ = categ.parent_id
            return None
        return 3  # global

    @api.model
    def _get_applicable_rule(self, partner, product, date, company):
        """Devuelve la regla ganadora o un recordset vacío."""
        if not partner or not product:
            return self.browse()

        date = date or fields.Date.context_today(self)
        domain = [
            ("company_id", "in", [company.id, False]),
            "|", ("date_start", "=", False), ("date_start", "<=", date),
            "|", ("date_end", "=", False), ("date_end", ">=", date),
        ]
        rules = self.search(domain)

        scored = []
        for rule in rules:
            if not rule._matches_partner(partner):
                continue
            specificity = rule._matches_product(product)
            if specificity is None:
                continue
            scored.append((specificity, rule.sequence, rule.id, rule))

        if not scored:
            return self.browse()
        scored.sort(key=lambda t: (t[0], t[1], t[2]))
        return scored[0][3]
