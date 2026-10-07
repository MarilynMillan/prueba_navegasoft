from odoo import api, fields, models

class PilaTipoTrabajador(models.Model):
    _name = 'pila.tipo.trabajador'
    _description = 'Tipo Trabajador'

    code = fields.Char(string='Código', required=True)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}"


class PilaSubtipoTrabajador(models.Model):
    _name = 'pila.subtipo.trabajador'
    _description = 'Subtipo Trabajador'

    code = fields.Char(string='Código', required=True)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}"
