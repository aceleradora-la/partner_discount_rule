{
    "name": "Partner Discount Rules",
    "summary": "Descuentos por cliente / etiqueta / categoría de partner "
               "sobre producto o categoría de producto, con vigencia por fechas.",
    "version": "19.0.1.1.0",
    "category": "Sales/Sales",
    "author": "Aceleradora",
    "website": "https://aceleradora.la",
    "license": "LGPL-3",
    "depends": ["sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/partner_discount_rule_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
