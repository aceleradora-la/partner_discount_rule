from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    discount_rule_count = fields.Integer(compute="_compute_discount_rule_count")

    def _discount_rule_domain(self):
        self.ensure_one()
        candidates = self | self.commercial_partner_id
        return [
            "|",
            ("partner_ids", "in", candidates.ids),
            ("partner_category_ids", "in", candidates.category_id.ids),
        ]

    def _compute_discount_rule_count(self):
        rule_model = self.env["partner.discount.rule"]
        for partner in self:
            partner.discount_rule_count = rule_model.search_count(
                partner._discount_rule_domain()
            )

    def action_view_discount_rules(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Reglas de descuento",
            "res_model": "partner.discount.rule",
            "view_mode": "list,form",
            "domain": self._discount_rule_domain(),
            "context": {"default_partner_ids": [(6, 0, self.ids)]},
        }
