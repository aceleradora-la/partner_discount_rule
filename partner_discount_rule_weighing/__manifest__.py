{
    "name": "Reglas de Descuento por Cliente - Pesaje",
    "summary": "Cantidad mínima de las reglas de descuento expresada en peso "
               "para productos pesables.",
    "description": """
Reglas de descuento + productos pesables
========================================
Módulo puente entre partner_discount_rule y sale_stock_weighing.
Se instala automáticamente cuando ambos están presentes y permite que la
cantidad mínima de una regla se interprete como peso (en la UdM de pesaje
de cada producto) para los productos pesables.
""",
    "version": "18.0.1.0.0",
    "category": "Sales/Sales",
    "author": "Aceleradora",
    "maintainer": "Aceleradora",
    "website": "https://aceleradora.la",
    "license": "LGPL-3",
    "depends": [
        "partner_discount_rule",
        "sale_stock_weighing",
    ],
    "data": [
        "views/partner_discount_rule_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": True,
}
