# -*- coding: utf-8 -*-


def migrate(cr, version):
    # Unified migration for stock/picking performance indexes.
    # Keep only the final partial index variant for free_reservation.
    cr.execute("""
        DROP INDEX IF EXISTS sml_free_reservation_partial_idx
    """)
    cr.execute("""
        DROP INDEX IF EXISTS sml_free_reservation_partial_idx_v2
    """)
    cr.execute("""
        DROP INDEX IF EXISTS sml_free_reservation_partial_idx_v3
    """)

    cr.execute("""
        CREATE INDEX IF NOT EXISTS sml_result_package_id_idx
        ON stock_move_line (result_package_id)
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS sml_move_id_idx
        ON stock_move_line (move_id)
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS sml_product_loc_lot_owner_pkg_idx
        ON stock_move_line (product_id, location_id, lot_id, owner_id, package_id)
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS sml_picking_id_idx
        ON stock_move_line (picking_id)
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS sml_free_reservation_partial_idx
        ON stock_move_line (product_id, location_id, company_id, id)
        WHERE state NOT IN ('done', 'cancel')
          AND lot_id IS NULL
          AND owner_id IS NULL
          AND package_id IS NULL
          AND quantity_product_uom > 0
          AND (picked IS NULL OR picked = FALSE)
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS sqp_name_id_desc_idx
        ON stock_quant_package (name DESC, id)
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS stock_location_parent_path_tpo_idx
        ON stock_location (parent_path text_pattern_ops)
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS stock_move_state_product_company_dest_idx
        ON stock_move (state, product_id, company_id, location_dest_id)
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS stock_move_state_product_company_loc_idx
        ON stock_move (state, product_id, company_id, location_id)
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS stock_move_state_product_company_locfinal_idx
        ON stock_move (state, product_id, company_id, location_final_id)
    """)
