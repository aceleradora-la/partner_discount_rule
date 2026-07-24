"""Migra los campos de producto Many2one (product_id, product_tmpl_id,
categ_id) a sus reemplazos Many2many, preservando la configuracion de las
reglas existentes. Las columnas viejas quedan huerfanas en la tabla; no
molestan y sirven de respaldo."""


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    mapping = [
        ("product_id", "partner_discount_rule_product_rel", "product_id"),
        ("product_tmpl_id", "partner_discount_rule_tmpl_rel", "tmpl_id"),
        ("categ_id", "partner_discount_rule_categ_rel", "categ_id"),
    ]
    for old_col, rel_table, rel_col in mapping:
        if not _column_exists(cr, "partner_discount_rule", old_col):
            continue
        cr.execute(
            """
            INSERT INTO {rel} (rule_id, {col})
            SELECT id, {old}
            FROM partner_discount_rule
            WHERE {old} IS NOT NULL
            ON CONFLICT DO NOTHING
            """.format(rel=rel_table, col=rel_col, old=old_col)
        )
