# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class administradoras(models.Model):
    _name = 'hr.administradoras'
    _description = 'Administradoras'

    name = fields.Char(string="Nombre Comercial")
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company)
    ccostos = fields.Many2one("hr.centrocostos", string="Centro de costos")
    administradora = fields.Many2one("hr.tipo", string="Tipo")
    tercero = fields.Many2one("res.partner", string="Tercero")
    porcentaje = fields.Float(string="Porcentaje")
    compania = fields.Boolean(string="Compañia")
    colaborador = fields.Boolean(string="Colaborador")
    centro_costos = fields.Boolean(string="Centro de costos")
    cuenta_debito = fields.Many2one("account.account", string="Cuenta debito")
    cuenta_credito = fields.Many2one("account.account", string="Cuenta crédito")



    @api.onchange('centro_costos')
    def _onchange_centro_costos(self):
        pass 
        # today_date = datetime.date.today()
        # for partner in self:
        #     if partner.date_of_birth:
        #         date_of_birth = fields.Datetime.to_datetime(
        #             partner.date_of_birth).date()
        #         total_age = ((today_date - date_of_birth).days / 365)
        #         partner.age = total_age
