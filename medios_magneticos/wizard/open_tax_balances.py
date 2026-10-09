# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
from datetime import date

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class OpenTaxBalances(models.TransientModel):
    _name = 'wizard.medios.magneticos'
    _description = 'Wizard de Conceptos'

    _MAX_DYNAMIC_FIELDS = 16
    _REMOTE_URL = "https://odoo15.navegasoft.com/admonclientes/medios/"

    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.user.company_id,
    )
    year = fields.Integer('Año', required=True, default=lambda self: date.today().year - 1)
    from_date = fields.Date('Fecha de inicio', compute='_compute_dates', store=True)
    to_date = fields.Date('Fecha final', compute='_compute_dates', store=True)
    target_move = fields.Selection(
        [('posted', 'All Posted Entries'), ('all', 'All Entries')],
        'Target Moves',
        required=True,
        default='posted',
    )
    formato = fields.Selection(
        [
            ('1001', '1001'),
            ('1003', '1003'),
            ('1004', '1004'),
            ('1005', '1005'),
            ('1006', '1006'),
            ('1007', '1007'),
            ('1008', '1008'),
            ('1009', '1009'),
            ('1010', '1010'),
            ('1011', '1011'),
            ('1012', '1012'),
            ('1647', '1647'),
            ('2275', '2275'),
            ('2276', '2276'),
        ],
        string='Formato',
        required=True,
        default='1001',
    )

    @api.depends('year')
    def _compute_dates(self):
        for record in self:
            if record.year:
                record.from_date = date(record.year, 1, 1)
                record.to_date = date(record.year, 12, 31)

    def open_taxes(self):
        self.ensure_one()
        self._clear_output()
        self._notify_remote_service()

        self._generate_from_asociacion_conceptos()

        generated_records = self.env['account.medios_magneticos'].search([])
        if not generated_records:
            raise UserError(
                "No se generaron datos para exportar. "
                "Revisa la configuración de exógena, el formato seleccionado y que existan movimientos contables en el periodo."
            )

        return self.env.ref('medios_magneticos.medios_magneticos_xlsx').report_action(generated_records)

    def _generate_from_asociacion_conceptos(self):
        association_records = self._get_asociacion_config()
        if not association_records:
            raise UserError(
                "No existe configuración en Asociación de Conceptos para el formato %s y el año %s."
                % (self.formato[:4], self.year)
            )

        category_names = self._ordered_unique(association_records.mapped('categoria.name'))
        field_map = self._build_field_map(category_names)
        output_model = self.env['account.medios_magneticos']

        for concept in self._ordered_unique(association_records.mapped('concepto')):
            concept_config = association_records.filtered(lambda rec: rec.concepto == concept)
            rows = {}

            for config in concept_config:
                account_ids = [config.cuenta.id]
                moves = self.env['account.move.line'].search(
                    self.get_move_line_partial_domain(
                        self.from_date,
                        self.to_date,
                        self.company_id.id,
                        account_ids,
                    )
                )

                partner_ids = moves.mapped('partner_id')
                for partner in partner_ids:
                    partner_moves = moves.filtered(lambda move: move.partner_id == partner)
                    if not partner_moves:
                        continue

                    secondary_partner = self._get_secondary_partner(partner_moves[0]) if self.formato[:4] == '1647' else False
                    key = (
                        partner.id,
                        secondary_partner.id if secondary_partner else 0,
                        concept.id,
                    )
                    if key not in rows:
                        rows[key] = self._build_base_output(
                            partner,
                            concept.name,
                            config,
                            secondary_partner=secondary_partner,
                        )

                    field_key = field_map.get(config.categoria.name)
                    if not field_key:
                        continue

                    initial_value = self._get_initial_amount(config.cuenta.id, partner.id)
                    debit_total = sum(partner_moves.mapped('debit'))
                    credit_total = sum(partner_moves.mapped('credit'))
                    rows[key][field_key] = rows[key].get(field_key, 0) + self._compute_value(
                        config.tipo_suma,
                        debit_total,
                        credit_total,
                        initial_value,
                    )

            for row in rows.values():
                if self._row_has_values(row, field_map.values()):
                    self._create_output_record(output_model, row)

    def _get_asociacion_config(self):
        return self.env['account.asoconcepto'].search([
            ('year', '=', str(self.year)),
            ('formaton', '=', self.formato[:4]),
        ])

    def _build_field_map(self, category_names):
        names = [name for name in category_names if name]
        if len(names) > self._MAX_DYNAMIC_FIELDS:
            raise UserError(
                "El formato %s tiene %s categorías y solo hay %s columnas dinámicas disponibles."
                % (self.formato[:4], len(names), self._MAX_DYNAMIC_FIELDS)
            )
        return {name: 'field_%s' % (index + 1) for index, name in enumerate(names)}

    def _ordered_unique(self, values):
        unique_values = []
        seen = set()
        for value in values:
            key = value.id if hasattr(value, 'id') else value
            if key in seen or not key:
                continue
            seen.add(key)
            unique_values.append(value)
        return unique_values

    def _build_base_output(self, partner, concept_name, config, secondary_partner=None):
        row = self._build_partner_values(partner)
        row.update(self._build_secondary_partner_values(secondary_partner))
        row.update({
            'account_id': config.cuenta.id,
            'concepto': concept_name,
        })
        row.update({'field_%s' % number: 0 for number in range(1, self._MAX_DYNAMIC_FIELDS + 1)})
        return row

    def _build_partner_values(self, partner, prefix=''):
        state_code = partner.state_id.code or ''
        state_department_code = (getattr(partner.state_id, 'code_department', '') or '').strip()
        city_code = ''
        if partner.city_id:
            city_code = str(getattr(partner.city_id, 'l10n_co_edi_code', '') or '').strip()
            if not city_code:
                city_code = str(getattr(partner.city_id, 'code', '') or '').strip()

        if state_department_code and state_department_code.isdigit():
            codigo_dpto = state_department_code.zfill(2)
        elif state_code and state_code.isdigit():
            codigo_dpto = state_code.zfill(2)
        else:
            codigo_dpto = ''

        if city_code and city_code.isdigit():
            codigo_mcp = city_code.zfill(5)
        else:
            codigo_mcp = ''

        country_code = partner.country_id.code or ''
        values = {
            '%sname' % prefix: partner.name or '',
            '%stipo_documento' % prefix: partner.vat_type or '',
            '%snumero_identificacion' % prefix: partner.vat or self.env.user.company_id.partner_id.vat or '',
            '%sdv' % prefix: partner.vat_vd or '',
            '%sprimer_apellido' % prefix: partner.last_name or '',
            '%ssegundo_apellido' % prefix: partner.second_last_name or '',
            '%sprimer_nombre' % prefix: partner.first_name or '',
            '%ssegundo_nombre' % prefix: partner.middle_name or '',
            '%srazon_social' % prefix: partner.name or '',
            '%sdireccion' % prefix: partner.street or '',
            '%snombre_dpto' % prefix: partner.state_id.name or '',
            '%scodigo_dpto' % prefix: codigo_dpto,
            '%snombre_mcp' % prefix: (partner.city_id.name if partner.city_id else partner.city) or '',
            '%scodigo_mcp' % prefix: codigo_mcp,
            '%spais' % prefix: partner.country_id.name or '',
            '%scodigo_pais' % prefix: self._normalize_country_code(country_code),
        }
        return values

    def _build_secondary_partner_values(self, partner):
        if not partner:
            return {
                'tipo_documento2': '',
                'numero_identificacion2': '',
                'dv2': '',
                'primer_apellido2': '',
                'segundo_apellido2': '',
                'primer_nombre2': '',
                'segundo_nombre2': '',
                'razon_social2': '',
                'direccion2': '',
                'codigo_dpto2': '',
                'nombre_dpto2': '',
                'codigo_mcp2': '',
                'nombre_mcp2': '',
                'pais2': '',
                'codigo_pais2': '',
            }

        secondary = self._build_partner_values(partner, prefix='')
        return {
            'tipo_documento2': secondary['tipo_documento'],
            'numero_identificacion2': secondary['numero_identificacion'],
            'dv2': secondary['dv'],
            'primer_apellido2': secondary['primer_apellido'],
            'segundo_apellido2': secondary['segundo_apellido'],
            'primer_nombre2': secondary['primer_nombre'],
            'segundo_nombre2': secondary['segundo_nombre'],
            'razon_social2': secondary['razon_social'],
            'direccion2': secondary['direccion'],
            'codigo_dpto2': secondary['codigo_dpto'],
            'nombre_dpto2': secondary['nombre_dpto'],
            'codigo_mcp2': secondary['codigo_mcp'],
            'nombre_mcp2': secondary['nombre_mcp'],
            'pais2': secondary['pais'],
            'codigo_pais2': secondary['codigo_pais'],
        }

    def _get_secondary_partner(self, move):
        analytic_account = move.analytic_account_id
        if analytic_account and analytic_account.partner_id:
            return analytic_account.partner_id
        return False

    def _compute_config_value(self, config, partner):
        initial_value = self._get_initial_amount(config.cuenta.id, partner.id)
        moves = self.env['account.move.line'].search(
            self.get_move_line_partial_domain2(
                self.from_date,
                self.to_date,
                self.company_id.id,
                config.cuenta.id,
                partner.id,
            )
        )
        debit_total = sum(moves.mapped('debit'))
        credit_total = sum(moves.mapped('credit'))
        return self._compute_value(config.tipo_suma, debit_total, credit_total, initial_value)

    def _get_initial_amount(self, account_id, partner_id):
        moves = self.env['account.move.line'].search(
            self.get_move_line_initial_domain(
                self.from_date,
                self.to_date,
                self.company_id.id,
                account_id,
                partner_id,
            )
        )
        return sum(moves.mapped('amount_currency'))

    def _compute_value(self, tipo_suma, debit_total, credit_total, initial_value):
        if tipo_suma == 'suma_debitos':
            return debit_total
        if tipo_suma == 'suma_creditos':
            return credit_total
        if tipo_suma == 'debitos_creditos':
            return debit_total - credit_total
        if tipo_suma == 'saldo_general':
            return initial_value + debit_total - credit_total
        if tipo_suma == 'saldo_inicial':
            return initial_value
        return 0

    def _row_has_values(self, row, field_names):
        return any(row.get(field_name) for field_name in field_names)

    def _create_output_record(self, output_model, row):
        output_model.create({
            **row,
            'year': str(self.year),
            'formato': self.formato[:4],
        })

    def _clear_output(self):
        self.env['account.medios_magneticos'].search([]).unlink()

    def _normalize_country_code(self, country_code):
        if country_code == 'CO':
            return '169'
        return country_code or ''

    def _get_company_platform_id(self):
        company = self.company_id
        if company.medios_magneticos_platform_id:
            return company.medios_magneticos_platform_id

        partner = company.partner_id
        if 'id_plataforma' in partner._fields and partner.id_plataforma:
            return partner.id_plataforma

        return False

    def _build_remote_payload(self):
        platform_id = self._get_company_platform_id()
        if not platform_id:
            raise UserError(
                "Configure el ID de plataforma en la compañía para generar medios magnéticos."
            )

        return {
            'tipo_documento': 'medios_magneticos',
            'id_plataforma': platform_id,
            'company_id': self.company_id.id,
            'formato': self.formato[:4],
            'year': self.year,
            'from_date': str(self.from_date),
            'to_date': str(self.to_date),
        }

    def _notify_remote_service(self):
        payload = self._build_remote_payload()
        try:
            response = requests.post(
                self._REMOTE_URL,
                data=json.dumps(payload),
                headers={"Content-type": "application/json"},
                verify=False,
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            _logger.warning(
                "No fue posible notificar el servicio remoto de medios magnéticos: %s",
                error,
            )

    def _get_target_move_domain(self):
        if self.target_move == 'posted':
            return [('move_id.state', '=', 'posted')]
        return []

    def get_move_line_partial_domain(self, from_date, to_date, company_id, account_ids):
        domain = [
            ('date', '<=', to_date),
            ('date', '>=', from_date),
            ('company_id', '=', company_id),
            ('account_id', 'in', account_ids),
        ]
        return domain + self._get_target_move_domain()

    def get_move_line_partial_domain2(self, from_date, to_date, company_id, account_id, partner_id):
        domain = [
            ('date', '<=', to_date),
            ('date', '>=', from_date),
            ('company_id', '=', company_id),
            ('account_id', '=', account_id),
            ('partner_id', '=', partner_id),
        ]
        return domain + self._get_target_move_domain()

    def get_move_line_initial_domain(self, from_date, to_date, company_id, account_id, partner_id):
        domain = [
            ('date', '<', from_date),
            ('company_id', '=', company_id),
            ('account_id', '=', account_id),
            ('partner_id', '=', partner_id),
        ]
        return domain + self._get_target_move_domain()
