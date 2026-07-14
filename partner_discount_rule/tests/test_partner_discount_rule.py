from datetime import date, timedelta

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerDiscountRule(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.tag_mayorista = cls.env["res.partner.category"].create(
            {"name": "Mayorista (test)"}
        )
        cls.partner = cls.env["res.partner"].create({"name": "ACME (test)"})
        cls.partner_tagged = cls.env["res.partner"].create(
            {"name": "Tagged (test)", "category_id": [(6, 0, cls.tag_mayorista.ids)]}
        )
        cls.partner_other = cls.env["res.partner"].create({"name": "Otro (test)"})
        cls.child = cls.env["res.partner"].create(
            {"name": "Sucursal (test)", "parent_id": cls.partner.id, "type": "invoice"}
        )
        cls.categ_parent = cls.env["product.category"].create({"name": "Bebidas (test)"})
        cls.categ_child = cls.env["product.category"].create(
            {"name": "Gaseosas (test)", "parent_id": cls.categ_parent.id}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Coca (test)", "categ_id": cls.categ_child.id, "list_price": 100}
        )
        cls.product_other = cls.env["product.product"].create(
            {"name": "Agua (test)", "categ_id": cls.categ_parent.id, "list_price": 50}
        )
        cls.Rule = cls.env["partner.discount.rule"]
        cls.today = date.today()

    def _rule(self, **vals):
        base = {
            "name": "Regla test",
            "discount": 10.0,
            "partner_ids": [(6, 0, self.partner.ids)],
        }
        base.update(vals)
        return self.Rule.create(base)

    def _resolve(self, partner=None, product=None):
        return self.Rule._get_applicable_rule(
            partner or self.partner,
            product or self.product,
            self.today,
            self.company,
        )

    def test_specificity_order(self):
        """Variante gana a producto, producto a categoria, categoria a global."""
        r_glob = self._rule(name="global", discount=5)
        r_cat = self._rule(
            name="categ",
            discount=10,
            applied_on="2_product_category",
            categ_id=self.categ_parent.id,
        )
        r_tmpl = self._rule(
            name="tmpl",
            discount=15,
            applied_on="1_product",
            product_tmpl_id=self.product.product_tmpl_id.id,
        )
        r_var = self._rule(
            name="variante",
            discount=20,
            applied_on="0_product_variant",
            product_id=self.product.id,
        )
        self.assertEqual(self._resolve(), r_var)
        r_var.active = False
        self.assertEqual(self._resolve(), r_tmpl)
        r_tmpl.active = False
        self.assertEqual(self._resolve(), r_cat)
        r_cat.active = False
        self.assertEqual(self._resolve(), r_glob)

    def test_category_matches_children(self):
        """Una regla sobre la categoria padre aplica a productos de la hija."""
        rule = self._rule(
            applied_on="2_product_category", categ_id=self.categ_parent.id
        )
        self.assertEqual(self._resolve(product=self.product), rule)

    def test_category_does_not_match_siblings(self):
        """Una regla sobre la categoria hija no aplica a productos del padre."""
        self._rule(
            name="hija", applied_on="2_product_category", categ_id=self.categ_child.id
        )
        self.assertFalse(self._resolve(product=self.product_other))

    def test_sequence_breaks_ties(self):
        self._rule(name="A", discount=10, sequence=5)
        r_b = self._rule(name="B", discount=30, sequence=1)
        self.assertEqual(self._resolve(), r_b)

    def test_match_by_tag(self):
        rule = self._rule(
            partner_ids=False,
            partner_category_ids=[(6, 0, self.tag_mayorista.ids)],
        )
        self.assertEqual(self._resolve(partner=self.partner_tagged), rule)
        self.assertFalse(self._resolve(partner=self.partner_other))

    def test_child_inherits_commercial_partner(self):
        rule = self._rule()
        self.assertEqual(self._resolve(partner=self.child), rule)

    def test_date_range(self):
        past = self._rule(
            name="pasada",
            date_start=self.today - timedelta(days=60),
            date_end=self.today - timedelta(days=30),
        )
        self.assertFalse(self._resolve())
        alive = self._rule(
            name="viva",
            date_start=self.today,
            date_end=self.today,
        )
        self.assertEqual(self._resolve(), alive)
        self.assertNotEqual(self._resolve(), past)

    def test_constraints(self):
        with self.assertRaises(ValidationError):
            self._rule(discount=150)
        with self.assertRaises(ValidationError):
            self._rule(
                date_start=self.today, date_end=self.today - timedelta(days=1)
            )
        with self.assertRaises(ValidationError):
            self._rule(partner_ids=False)

    def test_combine_modes(self):
        """Combinacion con el descuento ya presente en la linea (tarifa)."""
        rule = self._rule(discount=15)
        # override (default): pisa siempre
        self.assertEqual(rule._combine_discount(10), 15)
        self.assertEqual(rule._combine_discount(40), 15)
        # best: gana el mayor
        rule.combine_mode = "best"
        self.assertEqual(rule._combine_discount(10), 15)
        self.assertEqual(rule._combine_discount(40), 40)
        # sum: acumula con tope 100
        rule.combine_mode = "sum"
        self.assertEqual(rule._combine_discount(10), 25)
        rule.discount = 90
        self.assertEqual(rule._combine_discount(20), 100)

    def test_sale_order_line_gets_discount(self):
        self._rule(discount=15)
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": 1,
            }
        )
        self.assertEqual(line.discount, 15)

    def test_sale_order_line_no_rule(self):
        order = self.env["sale.order"].create({"partner_id": self.partner_other.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": 1,
            }
        )
        self.assertEqual(line.discount, 0)

    def test_min_qty(self):
        """La regla con cantidad minima aplica solo desde esa cantidad."""
        self._rule(discount=10, min_qty=10)
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": 5,
            }
        )
        self.assertEqual(line.discount, 0)
        line.product_uom_qty = 12
        self.assertEqual(line.discount, 10)

    def test_min_amount_reevaluates_all_lines(self):
        """El monto minimo mira el total bruto del pedido, y al superarlo
        todas las lineas (incluso las cargadas antes) reciben el descuento."""
        # product: lista $100, product_other: lista $50
        self._rule(discount=10, min_amount=1000)
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line1 = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": 5,  # total pedido: 500 < 1000
            }
        )
        self.assertEqual(line1.discount, 0)
        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product_other.id,
                "product_uom_qty": 10,  # total pedido: 500 + 500 = 1000
            }
        )
        self.assertEqual(line1.discount, 10, "la primera linea debe re-evaluarse")

    def test_discount_survives_confirmation(self):
        """Confirmar la orden no debe pisar el descuento de la regla."""
        self._rule(discount=25)
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": 1,
            }
        )
        self.assertEqual(line.discount, 25)
        order.action_confirm()
        self.assertEqual(line.discount, 25)
