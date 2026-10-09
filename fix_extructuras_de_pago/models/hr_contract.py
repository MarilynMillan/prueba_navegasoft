# -*- coding: utf-8 -*-

from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # name = fields.Char(string="Centro de costos")
    # company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company)
    administradoras_ids = fields.Many2many(
        'hr.administradoras',
        domain="[('colaborador', '=', True)]",
    )
    auxilio_de_transporte = fields.Float(string="Auxilio de transporte")
    salario_minimo = fields.Float(string="Salario minimo")
    tipo_auxilio = fields.Selection(
        selection=[
            ('transporte', 'Auxilio de transporte'),
            ('conectividad', 'Auxilio de conectividad'),
        ],
        string="Tipo de auxilio",
        default='transporte',
        required=True,
    )

