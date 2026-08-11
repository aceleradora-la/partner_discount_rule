"""Inicializa rule_discount_applied con el descuento vigente en las líneas
que ya tenían una regla registrada. Así una línea previa se considera
"no sobreescrita" (su descuento coincide con el aplicado por la regla) y la
regla puede seguir re-evaluándose; sin esto, quedarían marcadas como
sobreescritas y la regla no volvería a aplicar hasta reelegir el producto."""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE sale_order_line
        SET rule_discount_applied = discount
        WHERE discount_rule_id IS NOT NULL
        """
    )
