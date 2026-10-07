# -*- coding: utf-8 -*-
import base64
import csv
import io
from odoo import fields, models, _
from odoo.exceptions import UserError


class DSInventoryAdjustmentImport(models.TransientModel):
    """Mini-wizard para importar cantidades contadas desde Excel/CSV."""
    _name = 'ds.inventory.adjustment.import'
    _description = 'Importar Conteo de Inventario'

    adjustment_id = fields.Many2one(
        'ds.inventory.adjustment',
        string='Ajuste',
        required=True,
    )
    import_file = fields.Binary(
        string='Archivo',
        required=True,
        help='Archivo Excel (.xlsx) o CSV (.csv) con dos columnas: '
             'Referencia Interna y Cantidad Contada.',
    )
    import_filename = fields.Char(string='Nombre del Archivo')

    def action_go_back(self):
        """Volver al ajuste sin importar."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ds.inventory.adjustment',
            'res_id': self.adjustment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_import(self):
        """Procesa el archivo importado y llena las cantidades contadas."""
        self.ensure_one()
        if not self.import_file:
            raise UserError(_('Por favor seleccione un archivo para importar.'))

        filename = (self.import_filename or '').lower()
        file_data = base64.b64decode(self.import_file)

        if filename.endswith('.csv'):
            data_map = self._parse_csv(file_data)
        elif filename.endswith(('.xlsx', '.xls')):
            data_map = self._parse_xlsx(file_data)
        else:
            raise UserError(_('Formato de archivo no soportado. Use .csv o .xlsx'))

        if not data_map:
            raise UserError(_(
                'No se encontraron datos válidos en el archivo. '
                'Verifique que tenga dos columnas: Referencia Interna y Cantidad Contada.'
            ))

        lines = self.adjustment_id.line_ids
        matched = 0
        not_found = []

        for ref, qty in data_map.items():
            line = lines.filtered(
                lambda l, r=ref: l.product_id.default_code and
                l.product_id.default_code.strip().upper() == r
            )
            if line:
                line[0].counted_qty = qty
                matched += 1
            else:
                not_found.append(ref)

        msg = _('Importación completada: %(matched)s productos actualizados.', matched=matched)
        if not_found:
            msg += _('\n\nReferencias no encontradas (%(count)s): %(refs)s',
                     count=len(not_found), refs=', '.join(not_found[:20]))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ds.inventory.adjustment',
            'res_id': self.adjustment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _parse_csv(self, file_data):
        data_map = {}
        for encoding in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
            try:
                text = file_data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise UserError(_('No se pudo decodificar el archivo CSV.'))

        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(text[:2048])
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ','
            if ';' in text[:500]:
                delimiter = ';'
            elif '\t' in text[:500]:
                delimiter = '\t'

        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        header_skipped = False
        for row in reader:
            if len(row) < 2:
                continue
            ref = row[0].strip()
            qty_str = row[1].strip().replace(',', '.')
            if not header_skipped:
                try:
                    float(qty_str)
                except ValueError:
                    header_skipped = True
                    continue
                header_skipped = True
            try:
                qty = float(qty_str)
                if ref:
                    data_map[ref.upper()] = qty
            except ValueError:
                continue
        return data_map

    def _parse_xlsx(self, file_data):
        data_map = {}
        try:
            import openpyxl
        except ImportError:
            raise UserError(_('La librería openpyxl no está disponible. Use CSV.'))

        wb = openpyxl.load_workbook(io.BytesIO(file_data), read_only=True, data_only=True)
        ws = wb.active
        header_skipped = False
        for row in ws.iter_rows(min_col=1, max_col=2, values_only=True):
            if len(row) < 2 or row[0] is None:
                continue
            ref = str(row[0]).strip()
            qty_raw = row[1]
            if not header_skipped:
                if isinstance(qty_raw, str):
                    try:
                        float(qty_raw.replace(',', '.'))
                    except ValueError:
                        header_skipped = True
                        continue
                header_skipped = True
            try:
                qty = float(str(qty_raw).strip().replace(',', '.')) if isinstance(qty_raw, str) else float(qty_raw)
                if ref:
                    data_map[ref.upper()] = qty
            except (ValueError, TypeError):
                continue
        wb.close()
        return data_map
