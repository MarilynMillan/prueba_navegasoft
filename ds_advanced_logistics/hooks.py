# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Crea índice compuesto en stock_move_line para optimizar
    la consulta de reconstrucción de stock a fecha."""
    _logger.info(
        'DS Advanced Logistics: Creando índice idx_sml_ds_backdate_calc '
        'en stock_move_line para optimizar cálculo retroactivo...'
    )
    env.cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_sml_ds_backdate_calc
        ON stock_move_line (date, location_id, location_dest_id, product_id)
        WHERE state = 'done';
    """)
    _logger.info('DS Advanced Logistics: Índice creado exitosamente.')
