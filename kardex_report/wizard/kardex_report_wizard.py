# -*- coding: utf-8 -*-

import base64
import io
import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.debug('Cannot import xlsxwriter.')


class KardexReportWizard(models.TransientModel):
    _name = 'kardex.report.wizard'
    _description = 'Kardex - Reporte de Existencias'

    date_from = fields.Datetime(
        string='Fecha Inicio',
        required=True,
    )
    date_to = fields.Datetime(
        string='Fecha Fin',
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
    )
    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        string='Almacén',
    )
    location_ids = fields.Many2many(
        'stock.location',
        string='Ubicación',
        domain="[('usage', '=', 'internal')]",
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Productos',
    )
    product_categ_ids = fields.Many2many(
        'product.category',
        string='Categorías',
    )
    filter_by = fields.Selection([
        ('warehouse', 'Almacén'),
        ('location', 'Ubicación'),
    ], default='warehouse', string='Agrupar por', required=True)
    filter_product = fields.Selection([
        ('all', 'Todos los productos'),
        ('product', 'Productos específicos'),
        ('category', 'Categoría'),
    ], default='all', string='Filtro de producto', required=True)
    report_mode = fields.Selection([
        ('detailed', 'Detallado (todos los tipos de movimiento)'),
        ('summary', 'Resumido (Inicial, Entradas, Salidas, Final)'),
    ], default='detailed', string='Tipo de Kardex', required=True)

    # Campo para descarga
    document = fields.Binary('Archivo', readonly=True)
    file_name = fields.Char('Nombre archivo', readonly=True)

    @api.onchange('filter_by')
    def _onchange_filter_by(self):
        if self.filter_by == 'warehouse':
            self.location_ids = False
        else:
            self.warehouse_ids = False

    @api.onchange('filter_product')
    def _onchange_filter_product(self):
        if self.filter_product != 'product':
            self.product_ids = False
        if self.filter_product != 'category':
            self.product_categ_ids = False

    # =====================================================================
    # LÓGICA PRINCIPAL: Cálculo del Kardex
    # =====================================================================

    def _get_internal_locations(self):
        """Obtiene los IDs de ubicaciones internas según filtro."""
        if self.filter_by == 'location' and self.location_ids:
            return self.location_ids.ids
        elif self.filter_by == 'warehouse' and self.warehouse_ids:
            # lot_stock_id y todas las child locations internas
            Location = self.env['stock.location']
            locs = Location
            for wh in self.warehouse_ids:
                locs |= Location.search([
                    ('id', 'child_of', wh.lot_stock_id.id),
                    ('usage', '=', 'internal'),
                    ('company_id', '=', self.company_id.id),
                ])
            return locs.ids
        else:
            # Todas las internas de la compañía
            return self.env['stock.location'].search([
                ('usage', '=', 'internal'),
                ('company_id', '=', self.company_id.id),
            ]).ids

    def _get_product_domain(self):
        """Retorna dominio de productos según filtro."""
        domain = [('is_storable', '=', True)]
        if self.filter_product == 'product' and self.product_ids:
            domain.append(('id', 'in', self.product_ids.ids))
        elif self.filter_product == 'category' and self.product_categ_ids:
            domain.append(('categ_id', 'child_of', self.product_categ_ids.ids))
        return domain

    def _get_qty_at_date(self, product_ids, location_ids, to_date):
        """
        Calcula existencias a una fecha dada usando el MISMO approach nativo
        del reporte de existencias de Odoo:

        1) Toma la cantidad ACTUAL de stock.quant (ya pre-calculada en la tabla)
        2) Resta los movimientos POSTERIORES a to_date (que ya están hechos
           pero no deberían contar para la fecha solicitada)

        Esto es rápido porque:
        - stock.quant es una tabla de saldos actuales (pocos registros)
        - Solo recorre movimientos DESPUÉS de la fecha (generalmente pocos)

        Retorna dict: {product_id: qty}
        """
        if not product_ids or not location_ids:
            return {}

        # PASO 1: Cantidad actual en stock.quant (es un simple SUM agrupado)
        self.env.cr.execute("""
            SELECT product_id, COALESCE(SUM(quantity), 0) AS qty
            FROM stock_quant
            WHERE product_id = ANY(%(products)s)
              AND location_id = ANY(%(locs)s)
              AND company_id = %(company)s
            GROUP BY product_id
        """, {
            'products': product_ids,
            'locs': location_ids,
            'company': self.company_id.id,
        })
        current_qty = {row[0]: (row[1] or 0.0) for row in self.env.cr.fetchall()}

        # PASO 2: Restar movimientos POSTERIORES a to_date
        # (movimientos que ya pasaron pero no deberían contar)
        # Entradas posteriores → restar (no habían entrado aún)
        # Salidas posteriores → sumar (no habían salido aún)
        self.env.cr.execute("""
            SELECT
                sm.product_id,
                -- Entradas posteriores a la fecha (hacia ubicaciones del filtro)
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_dest.id = ANY(%(locs)s)
                      AND NOT (sl_src.id = ANY(%(locs)s))
                ), 0) AS qty_in_after,
                -- Salidas posteriores a la fecha (desde ubicaciones del filtro)
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_src.id = ANY(%(locs)s)
                      AND NOT (sl_dest.id = ANY(%(locs)s))
                ), 0) AS qty_out_after
            FROM stock_move sm
            JOIN stock_location sl_src  ON sl_src.id  = sm.location_id
            JOIN stock_location sl_dest ON sl_dest.id = sm.location_dest_id
            WHERE sm.state = 'done'
              AND sm.product_id = ANY(%(products)s)
              AND sm.company_id = %(company)s
              AND sm.date > %(to_date)s
              AND (sl_src.id = ANY(%(locs)s) OR sl_dest.id = ANY(%(locs)s))
            GROUP BY sm.product_id
        """, {
            'products': product_ids,
            'locs': location_ids,
            'company': self.company_id.id,
            'to_date': to_date,
        })

        # Ajustar: qty_at_date = current - entradas_posteriores + salidas_posteriores
        adjustments = {}
        for row in self.env.cr.fetchall():
            adjustments[row[0]] = (row[1], row[2])  # (in_after, out_after)

        result = {}
        all_pids = set(list(current_qty.keys()) + list(adjustments.keys()))
        for pid in all_pids:
            qty = current_qty.get(pid, 0.0)
            in_after, out_after = adjustments.get(pid, (0.0, 0.0))
            result[pid] = qty - in_after + out_after

        return result

    def _classify_movements(self, product_ids, location_ids, date_from, date_to):
        """
        Clasifica todos los stock.move del período en las categorías del Kardex.
        Usa SQL directo para máxima performance.

        Los desperdicios/scrap se calculan aparte usando stock_scrap.date_done
        porque sm.date puede diferir de la fecha real del scrap.

        Retorna dict: {product_id: {category: qty, ...}}
        """
        if not product_ids or not location_ids:
            return {}

        # ─── Query principal: todo excepto scraps ───
        self.env.cr.execute("""
            SELECT
                sm.product_id,
                -- ============ ENTRADAS ============
                -- Compras: supplier → internal
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_src.usage = 'supplier'
                      AND sl_dest.usage = 'internal'
                      AND sl_dest.id = ANY(%(locs)s)
                ), 0) AS in_purchase,

                -- Manufactura IN: production → internal
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_src.usage = 'production'
                      AND sl_dest.usage = 'internal'
                      AND sl_dest.id = ANY(%(locs)s)
                ), 0) AS in_manufacturing,

                -- Ajustes (+): inventory → internal
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_src.usage = 'inventory'
                      AND sl_dest.usage = 'internal'
                      AND sl_dest.id = ANY(%(locs)s)
                      AND COALESCE(sl_src.scrap_location, FALSE) = FALSE
                ), 0) AS in_adjustment,

                -- Devoluciones de cliente: customer → internal
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_src.usage = 'customer'
                      AND sl_dest.usage = 'internal'
                      AND sl_dest.id = ANY(%(locs)s)
                ), 0) AS in_customer_return,

                -- ============ SALIDAS ============
                -- Ventas: internal → customer
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_src.usage = 'internal'
                      AND sl_src.id = ANY(%(locs)s)
                      AND sl_dest.usage = 'customer'
                ), 0) AS out_sales,

                -- Manufactura OUT: internal → production
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_src.usage = 'internal'
                      AND sl_src.id = ANY(%(locs)s)
                      AND sl_dest.usage = 'production'
                ), 0) AS out_manufacturing,

                -- Ajustes (-): internal → inventory (que NO sea scrap)
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_src.usage = 'internal'
                      AND sl_src.id = ANY(%(locs)s)
                      AND sl_dest.usage = 'inventory'
                      AND COALESCE(sl_dest.scrap_location, FALSE) = FALSE
                ), 0) AS out_adjustment,

                -- Devoluciones a proveedor: internal → supplier
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_src.usage = 'internal'
                      AND sl_src.id = ANY(%(locs)s)
                      AND sl_dest.usage = 'supplier'
                ), 0) AS out_supplier_return,

                -- ============ TRANSFERENCIAS INTERNAS ============
                -- Entradas internas (de otra interna que NO está en el filtro)
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_src.usage = 'internal'
                      AND sl_dest.usage = 'internal'
                      AND sl_dest.id = ANY(%(locs)s)
                      AND NOT (sl_src.id = ANY(%(locs)s))
                ), 0) AS in_internal,

                -- Salidas internas (hacia otra interna que NO está en el filtro)
                COALESCE(SUM(sm.quantity) FILTER (
                    WHERE sl_src.usage = 'internal'
                      AND sl_src.id = ANY(%(locs)s)
                      AND sl_dest.usage = 'internal'
                      AND NOT (sl_dest.id = ANY(%(locs)s))
                ), 0) AS out_internal

            FROM stock_move sm
            JOIN stock_location sl_src  ON sl_src.id  = sm.location_id
            JOIN stock_location sl_dest ON sl_dest.id = sm.location_dest_id
            WHERE sm.state = 'done'
              AND sm.product_id = ANY(%(products)s)
              AND sm.company_id = %(company)s
              AND sm.date >= %(date_from)s
              AND sm.date <= %(date_to)s
              AND COALESCE(sm.scrapped, FALSE) = FALSE
              AND (
                  sl_src.id = ANY(%(locs)s) OR sl_dest.id = ANY(%(locs)s)
              )
            GROUP BY sm.product_id
        """, {
            'locs': location_ids,
            'products': product_ids,
            'company': self.company_id.id,
            'date_from': date_from,
            'date_to': date_to,
        })

        result = {}
        for row in self.env.cr.fetchall():
            result[row[0]] = {
                'in_purchase': row[1],
                'in_manufacturing': row[2],
                'in_adjustment': row[3],
                'in_customer_return': row[4],
                'out_sales': row[5],
                'out_manufacturing': row[6],
                'out_scrap': 0.0,
                'out_adjustment': row[7],
                'out_supplier_return': row[8],
                'in_internal': row[9],
                'out_internal': row[10],
            }

        # ─── Query separada: Desperdicios desde stock_move_line ───
        # Usa sml.date (fecha real) en vez de sm.date (fecha validación)
        # Captura tanto el producto principal del scrap como los componentes
        # de la receta (BOM) que Odoo descarga automáticamente
        self.env.cr.execute("""
            SELECT
                sml.product_id,
                SUM(sml.quantity) AS scrap_qty
            FROM stock_move_line sml
            JOIN stock_location sl_dest ON sl_dest.id = sml.location_dest_id
            WHERE sml.state = 'done'
              AND sml.product_id = ANY(%(products)s)
              AND sml.company_id = %(company)s
              AND sml.date >= %(date_from)s
              AND sml.date <= %(date_to)s
              AND sml.location_id = ANY(%(locs)s)
              AND COALESCE(sl_dest.scrap_location, FALSE) = TRUE
            GROUP BY sml.product_id
        """, {
            'products': product_ids,
            'company': self.company_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'locs': location_ids,
        })

        for row in self.env.cr.fetchall():
            pid = row[0]
            scrap_qty = row[1]
            if pid in result:
                result[pid]['out_scrap'] = scrap_qty
            else:
                result[pid] = {
                    'in_purchase': 0.0, 'in_manufacturing': 0.0,
                    'in_adjustment': 0.0, 'in_customer_return': 0.0,
                    'out_sales': 0.0, 'out_manufacturing': 0.0,
                    'out_scrap': scrap_qty,
                    'out_adjustment': 0.0, 'out_supplier_return': 0.0,
                    'in_internal': 0.0, 'out_internal': 0.0,
                }

        return result

    def _get_kardex_data(self):
        """
        Método principal: genera la data completa del Kardex.
        Retorna lista de dicts agrupada por categoría.
        """
        self.ensure_one()

        location_ids = self._get_internal_locations()
        if not location_ids:
            raise UserError(_('No se encontraron ubicaciones internas para el filtro seleccionado.'))

        # Obtener productos
        product_domain = self._get_product_domain()
        products = self.env['product.product'].search(product_domain, order='categ_id, default_code, name')
        if not products:
            raise UserError(_('No se encontraron productos con los filtros seleccionados.'))

        product_ids = products.ids

        # 1) Cantidad inicial: existencias a (date_from)
        #    Usamos date_from directamente — representa el "corte" al inicio del periodo
        qty_initial = self._get_qty_at_date(product_ids, location_ids, self.date_from)

        # 2) Movimientos clasificados en el período
        movements = self._classify_movements(product_ids, location_ids, self.date_from, self.date_to)

        # 3) Construir data agrupada por categoría
        categories = {}
        for product in products:
            categ = product.categ_id
            categ_key = categ.id
            if categ_key not in categories:
                categories[categ_key] = {
                    'category_name': categ.complete_name or categ.name,
                    'category_id': categ.id,
                    'products': [],
                    # Totales de categoría
                    'totals': {
                        'qty_initial': 0, 'qty_final': 0,
                        'in_purchase': 0, 'in_manufacturing': 0, 'in_adjustment': 0, 'in_customer_return': 0, 'in_internal': 0,
                        'out_sales': 0, 'out_manufacturing': 0, 'out_scrap': 0, 'out_adjustment': 0, 'out_supplier_return': 0, 'out_internal': 0,
                    }
                }

            pid = product.id
            initial = qty_initial.get(pid, 0.0)
            mvs = movements.get(pid, {})

            in_purchase = mvs.get('in_purchase', 0.0)
            in_manufacturing = mvs.get('in_manufacturing', 0.0)
            in_adjustment = mvs.get('in_adjustment', 0.0)
            in_customer_return = mvs.get('in_customer_return', 0.0)
            in_internal = mvs.get('in_internal', 0.0)

            out_sales = mvs.get('out_sales', 0.0)
            out_manufacturing = mvs.get('out_manufacturing', 0.0)
            out_scrap = mvs.get('out_scrap', 0.0)
            out_adjustment = mvs.get('out_adjustment', 0.0)
            out_supplier_return = mvs.get('out_supplier_return', 0.0)
            out_internal = mvs.get('out_internal', 0.0)

            total_in = in_purchase + in_manufacturing + in_adjustment + in_customer_return + in_internal
            total_out = out_sales + out_manufacturing + out_scrap + out_adjustment + out_supplier_return + out_internal
            qty_final = initial + total_in - total_out

            prod_data = {
                'product_id': pid,
                'product_name': product.display_name,
                'product_code': product.default_code or '',
                'uom': product.uom_id.name,
                'qty_initial': initial,
                'in_purchase': in_purchase,
                'in_manufacturing': in_manufacturing,
                'in_adjustment': in_adjustment,
                'in_customer_return': in_customer_return,
                'in_internal': in_internal,
                'total_in': total_in,
                'out_sales': out_sales,
                'out_manufacturing': out_manufacturing,
                'out_scrap': out_scrap,
                'out_adjustment': out_adjustment,
                'out_supplier_return': out_supplier_return,
                'out_internal': out_internal,
                'total_out': total_out,
                'qty_final': qty_final,
            }

            categories[categ_key]['products'].append(prod_data)

            # Acumular totales de categoría
            totals = categories[categ_key]['totals']
            for key in totals:
                totals[key] += prod_data.get(key, 0.0)

        # Ordenar categorías por nombre
        sorted_categories = sorted(categories.values(), key=lambda c: c['category_name'])
        return sorted_categories

    # =====================================================================
    # GENERACIÓN EXCEL
    # =====================================================================

    def print_excel_report(self):
        self.ensure_one()

        if self.date_from >= self.date_to:
            raise UserError(_('La fecha inicio debe ser anterior a la fecha fin.'))

        kardex_data = self._get_kardex_data()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        if self.report_mode == 'summary':
            date_from_str, date_to_str = self._write_summary_sheet(workbook, kardex_data)
        else:
            date_from_str, date_to_str = self._write_detailed_sheet(workbook, kardex_data)

        workbook.close()
        output.seek(0)

        mode_label = 'Resumido' if self.report_mode == 'summary' else 'Detallado'
        file_name = f'Kardex_{mode_label}_{self.company_id.name}_{date_from_str[:10]}_{date_to_str[:10]}.xlsx'

        self.write({
            'document': base64.b64encode(output.read()),
            'file_name': file_name,
        })
        output.close()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'kardex.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('Descargar Kardex'),
        }

    def _get_header_info(self):
        """Retorna info común del encabezado."""
        if self.filter_by == 'warehouse' and self.warehouse_ids:
            label = 'Almacén:'
            value = ', '.join(self.warehouse_ids.mapped('name'))
        elif self.filter_by == 'location' and self.location_ids:
            label = 'Ubicación:'
            value = ', '.join(self.location_ids.mapped('complete_name'))
        else:
            label = 'Almacén:'
            value = 'Todos'
        date_from_str = fields.Datetime.context_timestamp(self, self.date_from).strftime('%Y-%m-%d %H:%M:%S')
        date_to_str = fields.Datetime.context_timestamp(self, self.date_to).strftime('%Y-%m-%d %H:%M:%S')
        return label, value, date_from_str, date_to_str

    # ─────────────────────────────────────────────────────────
    # EXCEL RESUMIDO
    # ─────────────────────────────────────────────────────────

    def _write_summary_sheet(self, workbook, kardex_data):
        worksheet = workbook.add_worksheet('Kardex Resumido')

        # ─── Formatos ───
        fmt_title = workbook.add_format({
            'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#1F4E79', 'font_color': '#FFFFFF', 'border': 1,
        })
        fmt_header_main = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#1F4E79', 'font_color': '#FFFFFF', 'border': 1, 'text_wrap': True,
        })
        fmt_header_in = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#C6EFCE', 'border': 1, 'text_wrap': True,
        })
        fmt_header_out = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#FFC7CE', 'border': 1, 'text_wrap': True,
        })
        fmt_categ = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'left', 'valign': 'vcenter',
            'bg_color': '#F2F2F2', 'border': 1, 'bottom': 2,
        })
        fmt_categ_num = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#F2F2F2', 'border': 1, 'bottom': 2, 'num_format': '#,##0.00',
        })
        fmt_text = workbook.add_format({
            'font_size': 9, 'align': 'left', 'valign': 'vcenter', 'border': 1,
        })
        fmt_num = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter', 'border': 1,
            'num_format': '#,##0.00',
        })
        fmt_num_initial = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter', 'border': 1,
            'num_format': '#,##0.00', 'bg_color': '#E2EFDA',
        })
        fmt_num_final = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter', 'border': 1,
            'num_format': '#,##0.00', 'bg_color': '#DDEBF7', 'bold': True,
        })
        fmt_total_label = workbook.add_format({
            'bold': True, 'font_size': 11, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#1F4E79', 'font_color': '#FFFFFF', 'border': 1,
        })
        fmt_total_num = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#1F4E79', 'font_color': '#FFFFFF', 'border': 1,
            'num_format': '#,##0.00',
        })
        fmt_info = workbook.add_format({
            'font_size': 10, 'align': 'left', 'valign': 'vcenter',
        })
        fmt_info_bold = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'left', 'valign': 'vcenter',
        })

        # Columnas: 0:Código 1:Producto 2:UdM 3:Cant.Inicial 4:Total Entradas 5:Total Salidas 6:Cant.Final
        last_col = 6
        col_widths = [14, 45, 8, 16, 16, 16, 16]
        for i, w in enumerate(col_widths):
            worksheet.set_column(i, i, w)

        row = 0
        loc_label, loc_value, date_from_str, date_to_str = self._get_header_info()

        worksheet.merge_range(row, 0, row, last_col, 'KARDEX DE INVENTARIO - RESUMIDO', fmt_title)
        row += 1
        worksheet.merge_range(row, 0, row, 1, 'Compañía:', fmt_info_bold)
        worksheet.merge_range(row, 2, row, 4, self.company_id.name, fmt_info)
        row += 1
        worksheet.merge_range(row, 0, row, 1, loc_label, fmt_info_bold)
        worksheet.merge_range(row, 2, row, 4, loc_value, fmt_info)
        row += 1
        worksheet.merge_range(row, 0, row, 1, 'Período:', fmt_info_bold)
        worksheet.merge_range(row, 2, row, 4, f'{date_from_str}  →  {date_to_str}', fmt_info)
        row += 2

        # Headers
        header_row = row
        worksheet.write(row, 0, 'Código', fmt_header_main)
        worksheet.write(row, 1, 'Producto', fmt_header_main)
        worksheet.write(row, 2, 'UdM', fmt_header_main)
        worksheet.write(row, 3, 'Cant.\nInicial', fmt_header_main)
        worksheet.write(row, 4, 'Total\nEntradas', fmt_header_in)
        worksheet.write(row, 5, 'Total\nSalidas', fmt_header_out)
        worksheet.write(row, 6, 'Cant.\nFinal', fmt_header_main)
        worksheet.set_row(row, 30)
        row += 1

        # Data
        grand_totals = {'qty_initial': 0, 'total_in': 0, 'total_out': 0, 'qty_final': 0}

        for categ_data in kardex_data:
            ct = categ_data['totals']
            total_in_categ = ct['in_purchase'] + ct['in_manufacturing'] + ct['in_adjustment'] + ct['in_customer_return'] + ct['in_internal']
            total_out_categ = ct['out_sales'] + ct['out_manufacturing'] + ct['out_scrap'] + ct['out_adjustment'] + ct['out_supplier_return'] + ct['out_internal']

            worksheet.merge_range(row, 0, row, 2, categ_data['category_name'], fmt_categ)
            worksheet.write(row, 3, ct['qty_initial'], fmt_categ_num)
            worksheet.write(row, 4, total_in_categ, fmt_categ_num)
            worksheet.write(row, 5, total_out_categ, fmt_categ_num)
            worksheet.write(row, 6, ct['qty_final'], fmt_categ_num)
            row += 1

            for p in categ_data['products']:
                worksheet.write(row, 0, p['product_code'], fmt_text)
                worksheet.write(row, 1, p['product_name'], fmt_text)
                worksheet.write(row, 2, p['uom'], fmt_text)
                worksheet.write(row, 3, p['qty_initial'], fmt_num_initial)
                worksheet.write(row, 4, p['total_in'], fmt_num)
                worksheet.write(row, 5, p['total_out'], fmt_num)
                worksheet.write(row, 6, p['qty_final'], fmt_num_final)
                row += 1

            grand_totals['qty_initial'] += ct['qty_initial']
            grand_totals['total_in'] += total_in_categ
            grand_totals['total_out'] += total_out_categ
            grand_totals['qty_final'] += ct['qty_final']

        # Gran Total
        row += 1
        worksheet.merge_range(row, 0, row, 2, 'TOTAL GENERAL', fmt_total_label)
        worksheet.write(row, 3, grand_totals['qty_initial'], fmt_total_num)
        worksheet.write(row, 4, grand_totals['total_in'], fmt_total_num)
        worksheet.write(row, 5, grand_totals['total_out'], fmt_total_num)
        worksheet.write(row, 6, grand_totals['qty_final'], fmt_total_num)

        worksheet.freeze_panes(header_row + 1, 3)
        worksheet.autofilter(header_row, 0, row, last_col)

        return date_from_str, date_to_str

    # ─────────────────────────────────────────────────────────
    # EXCEL DETALLADO
    # ─────────────────────────────────────────────────────────

    def _write_detailed_sheet(self, workbook, kardex_data):
        worksheet = workbook.add_worksheet('Kardex Detallado')

        # ─── Formatos ───
        fmt_title = workbook.add_format({
            'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#1F4E79', 'font_color': '#FFFFFF', 'border': 1,
        })
        fmt_subtitle = workbook.add_format({
            'bold': True, 'font_size': 11, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#D6E4F0', 'border': 1,
        })
        fmt_header_main = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#1F4E79', 'font_color': '#FFFFFF', 'border': 1,
            'text_wrap': True,
        })
        fmt_header_in = workbook.add_format({
            'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#C6EFCE', 'border': 1, 'text_wrap': True,
        })
        fmt_header_out = workbook.add_format({
            'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#FFC7CE', 'border': 1, 'text_wrap': True,
        })
        fmt_categ = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'left', 'valign': 'vcenter',
            'bg_color': '#F2F2F2', 'border': 1, 'bottom': 2,
        })
        fmt_categ_num = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#F2F2F2', 'border': 1, 'bottom': 2, 'num_format': '#,##0.00',
        })
        fmt_text = workbook.add_format({
            'font_size': 9, 'align': 'left', 'valign': 'vcenter', 'border': 1,
        })
        fmt_num = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter', 'border': 1,
            'num_format': '#,##0.00',
        })
        fmt_num_bold = workbook.add_format({
            'bold': True, 'font_size': 9, 'align': 'right', 'valign': 'vcenter', 'border': 1,
            'num_format': '#,##0.00',
        })
        fmt_num_initial = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter', 'border': 1,
            'num_format': '#,##0.00', 'bg_color': '#E2EFDA',
        })
        fmt_num_final = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter', 'border': 1,
            'num_format': '#,##0.00', 'bg_color': '#DDEBF7', 'bold': True,
        })
        fmt_total_label = workbook.add_format({
            'bold': True, 'font_size': 11, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#1F4E79', 'font_color': '#FFFFFF', 'border': 1,
        })
        fmt_total_num = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#1F4E79', 'font_color': '#FFFFFF', 'border': 1,
            'num_format': '#,##0.00',
        })
        fmt_info = workbook.add_format({
            'font_size': 10, 'align': 'left', 'valign': 'vcenter',
        })
        fmt_info_bold = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'left', 'valign': 'vcenter',
        })

        # ─── Anchos de columna ───
        #  0: Código  1: Producto  2: UdM  3: Cant.Inicial
        #  ENTRADAS: 4: Compras  5: Manuf.(IN)  6: Ajustes(+)  7: Dev.Cliente  8: Transf.(IN)  9: Total Entradas
        #  SALIDAS: 10: Ventas  11: Manuf.(OUT)  12: Desperdicios  13: Ajustes(-)  14: Dev.Proveedor  15: Transf.(OUT)  16: Total Salidas
        #  17: Cant.Final
        last_col = 17
        col_widths = [14, 40, 8, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14]
        for i, w in enumerate(col_widths):
            worksheet.set_column(i, i, w)

        row = 0
        loc_label, loc_value, date_from_str, date_to_str = self._get_header_info()

        # ─── Encabezado del reporte ───
        worksheet.merge_range(row, 0, row, last_col, 'KARDEX DE INVENTARIO - DETALLADO', fmt_title)
        row += 1

        worksheet.merge_range(row, 0, row, 1, 'Compañía:', fmt_info_bold)
        worksheet.merge_range(row, 2, row, 5, self.company_id.name, fmt_info)
        row += 1

        worksheet.merge_range(row, 0, row, 1, loc_label, fmt_info_bold)
        worksheet.merge_range(row, 2, row, 5, loc_value, fmt_info)
        row += 1

        worksheet.merge_range(row, 0, row, 1, 'Período:', fmt_info_bold)
        worksheet.merge_range(row, 2, row, 5, f'{date_from_str}  →  {date_to_str}', fmt_info)
        row += 2

        # ─── Headers de tabla ───
        header_row = row
        worksheet.write(header_row, 0, 'Código', fmt_header_main)
        worksheet.write(header_row, 1, 'Producto', fmt_header_main)
        worksheet.write(header_row, 2, 'UdM', fmt_header_main)
        worksheet.write(header_row, 3, 'Cant.\nInicial', fmt_header_main)

        worksheet.merge_range(header_row, 4, header_row, 9, 'ENTRADAS', fmt_header_in)
        worksheet.merge_range(header_row, 10, header_row, 16, 'SALIDAS', fmt_header_out)

        worksheet.write(header_row, 17, 'Cant.\nFinal', fmt_header_main)
        row += 1

        # Fila 2: Subencabezados
        worksheet.write(row, 0, '', fmt_header_main)
        worksheet.write(row, 1, '', fmt_header_main)
        worksheet.write(row, 2, '', fmt_header_main)
        worksheet.write(row, 3, '', fmt_header_main)

        # Entradas
        worksheet.write(row, 4, 'Compras\n(Recepciones)', fmt_header_in)
        worksheet.write(row, 5, 'Manufactura', fmt_header_in)
        worksheet.write(row, 6, 'Ajustes (+)', fmt_header_in)
        worksheet.write(row, 7, 'Dev.\nCliente', fmt_header_in)
        worksheet.write(row, 8, 'Transf.\nInternas (+)', fmt_header_in)
        worksheet.write(row, 9, 'Total\nEntradas', fmt_header_in)

        # Salidas
        worksheet.write(row, 10, 'Ventas', fmt_header_out)
        worksheet.write(row, 11, 'Manufactura', fmt_header_out)
        worksheet.write(row, 12, 'Desperdicios', fmt_header_out)
        worksheet.write(row, 13, 'Ajustes (-)', fmt_header_out)
        worksheet.write(row, 14, 'Dev.\nProveedor', fmt_header_out)
        worksheet.write(row, 15, 'Transf.\nInternas (-)', fmt_header_out)
        worksheet.write(row, 16, 'Total\nSalidas', fmt_header_out)

        worksheet.write(row, 17, '', fmt_header_main)
        row += 1

        worksheet.set_row(header_row, 25)
        worksheet.set_row(header_row + 1, 35)

        # ─── Data ───
        grand_totals = {
            'qty_initial': 0, 'qty_final': 0,
            'in_purchase': 0, 'in_manufacturing': 0, 'in_adjustment': 0, 'in_customer_return': 0, 'in_internal': 0, 'total_in': 0,
            'out_sales': 0, 'out_manufacturing': 0, 'out_scrap': 0, 'out_adjustment': 0, 'out_supplier_return': 0, 'out_internal': 0, 'total_out': 0,
        }

        for categ_data in kardex_data:
            # Fila de categoría
            worksheet.merge_range(row, 0, row, 2, categ_data['category_name'], fmt_categ)
            ct = categ_data['totals']

            total_in_categ = ct['in_purchase'] + ct['in_manufacturing'] + ct['in_adjustment'] + ct['in_customer_return'] + ct['in_internal']
            total_out_categ = ct['out_sales'] + ct['out_manufacturing'] + ct['out_scrap'] + ct['out_adjustment'] + ct['out_supplier_return'] + ct['out_internal']

            worksheet.write(row, 3, ct['qty_initial'], fmt_categ_num)
            worksheet.write(row, 4, ct['in_purchase'], fmt_categ_num)
            worksheet.write(row, 5, ct['in_manufacturing'], fmt_categ_num)
            worksheet.write(row, 6, ct['in_adjustment'], fmt_categ_num)
            worksheet.write(row, 7, ct['in_customer_return'], fmt_categ_num)
            worksheet.write(row, 8, ct['in_internal'], fmt_categ_num)
            worksheet.write(row, 9, total_in_categ, fmt_categ_num)
            worksheet.write(row, 10, ct['out_sales'], fmt_categ_num)
            worksheet.write(row, 11, ct['out_manufacturing'], fmt_categ_num)
            worksheet.write(row, 12, ct['out_scrap'], fmt_categ_num)
            worksheet.write(row, 13, ct['out_adjustment'], fmt_categ_num)
            worksheet.write(row, 14, ct['out_supplier_return'], fmt_categ_num)
            worksheet.write(row, 15, ct['out_internal'], fmt_categ_num)
            worksheet.write(row, 16, total_out_categ, fmt_categ_num)
            worksheet.write(row, 17, ct['qty_final'], fmt_categ_num)
            row += 1

            # Productos de la categoría
            for p in categ_data['products']:
                worksheet.write(row, 0, p['product_code'], fmt_text)
                worksheet.write(row, 1, p['product_name'], fmt_text)
                worksheet.write(row, 2, p['uom'], fmt_text)
                worksheet.write(row, 3, p['qty_initial'], fmt_num_initial)
                worksheet.write(row, 4, p['in_purchase'], fmt_num)
                worksheet.write(row, 5, p['in_manufacturing'], fmt_num)
                worksheet.write(row, 6, p['in_adjustment'], fmt_num)
                worksheet.write(row, 7, p['in_customer_return'], fmt_num)
                worksheet.write(row, 8, p['in_internal'], fmt_num)
                worksheet.write(row, 9, p['total_in'], fmt_num_bold)
                worksheet.write(row, 10, p['out_sales'], fmt_num)
                worksheet.write(row, 11, p['out_manufacturing'], fmt_num)
                worksheet.write(row, 12, p['out_scrap'], fmt_num)
                worksheet.write(row, 13, p['out_adjustment'], fmt_num)
                worksheet.write(row, 14, p['out_supplier_return'], fmt_num)
                worksheet.write(row, 15, p['out_internal'], fmt_num)
                worksheet.write(row, 16, p['total_out'], fmt_num_bold)
                worksheet.write(row, 17, p['qty_final'], fmt_num_final)
                row += 1

            # Acumular grand totals
            for key in grand_totals:
                if key in ct:
                    grand_totals[key] += ct[key]
            grand_totals['total_in'] += total_in_categ
            grand_totals['total_out'] += total_out_categ

        # ─── Gran Total ───
        row += 1
        worksheet.merge_range(row, 0, row, 2, 'TOTAL GENERAL', fmt_total_label)
        worksheet.write(row, 3, grand_totals['qty_initial'], fmt_total_num)
        worksheet.write(row, 4, grand_totals['in_purchase'], fmt_total_num)
        worksheet.write(row, 5, grand_totals['in_manufacturing'], fmt_total_num)
        worksheet.write(row, 6, grand_totals['in_adjustment'], fmt_total_num)
        worksheet.write(row, 7, grand_totals['in_customer_return'], fmt_total_num)
        worksheet.write(row, 8, grand_totals['in_internal'], fmt_total_num)
        worksheet.write(row, 9, grand_totals['total_in'], fmt_total_num)
        worksheet.write(row, 10, grand_totals['out_sales'], fmt_total_num)
        worksheet.write(row, 11, grand_totals['out_manufacturing'], fmt_total_num)
        worksheet.write(row, 12, grand_totals['out_scrap'], fmt_total_num)
        worksheet.write(row, 13, grand_totals['out_adjustment'], fmt_total_num)
        worksheet.write(row, 14, grand_totals['out_supplier_return'], fmt_total_num)
        worksheet.write(row, 15, grand_totals['out_internal'], fmt_total_num)
        worksheet.write(row, 16, grand_totals['total_out'], fmt_total_num)
        worksheet.write(row, 17, grand_totals['qty_final'], fmt_total_num)

        # ─── Congelar paneles ───
        worksheet.freeze_panes(header_row + 2, 3)

        # ─── Autofilter ───
        worksheet.autofilter(header_row + 1, 0, row, last_col)

        return date_from_str, date_to_str
