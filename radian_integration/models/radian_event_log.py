from odoo import models, fields

class RadianEventLog(models.Model):
    _name = 'radian.event.log'
    _description = 'Log de eventos RADIAN'

    invoice_id = fields.Many2one('account.move', required=True, ondelete='cascade')
    event_type = fields.Selection([
        ('registro', 'Registro'),
        ('aceptacion_expresa', 'Aceptación expresa'),
        ('rechazo', 'Rechazo'),
        ('cesion', 'Cesión'),
    ], string="Tipo de Evento", required=True)
    status = fields.Char("Estado")
    response = fields.Text("Respuesta API")
    date = fields.Datetime("Fecha", default=fields.Datetime.now)