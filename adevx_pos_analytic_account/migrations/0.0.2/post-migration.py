# -*- coding: utf-8 -*-


def migrate(cr, version):
    # Speeds up pos.session related move resolution by reference lookups.
    cr.execute("""
        CREATE INDEX IF NOT EXISTS account_move_line_ref_not_null_idx
        ON account_move_line (ref)
        WHERE ref IS NOT NULL
    """)
