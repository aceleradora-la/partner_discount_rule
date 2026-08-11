{
    "name": "Reglas de Descuento por Cliente",
    "summary": "Descuentos por cliente, etiqueta o categoría de partner "
               "sobre producto o categoría de producto, con vigencia por fechas.",
    "description": """
Reglas de descuento por cliente
===============================
Descuentos (%) por cliente o etiqueta de cliente, aplicables a variante,
producto, categoría de producto (incluye hijas) o todos los productos,
con vigencia opcional por fechas y modo de convivencia configurable con
el descuento de la lista de precios (mayor beneficio, acumulado o
sobreescribir).
""",
    "version": "19.0.1.5.0",
    "category": "Sales/Sales",
    "author": "Aceleradora",
    "maintainer": "Aceleradora",
    "website": "https://aceleradora.la",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/partner_discount_rule_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
