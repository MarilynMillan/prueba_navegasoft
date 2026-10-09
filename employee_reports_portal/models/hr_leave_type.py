from odoo import models, fields, exceptions, api
from odoo import _
import locale, datetime

class Employee(models.Model):
    _inherit = "hr.leave.type"

    obligar_adjunto = fields.Boolean(string="Obligar adjunto")
    condicion = fields.Text(string="Condición")
    tratamiento_datos = fields.Boolean(string="Mostrar tratamiento de datos")
    

class Employee(models.Model):
    _inherit = "hr.leave"

    tratamiento_datos = fields.Boolean(string="Tratamiento de datos")
    condicion = fields.Text(string="Condición",related='holiday_status_id.condicion',store=True)
    number_of_days_display = fields.Float(string='Días', readonly=True, store=True)

    #@api.onchange('holiday_status_id')
    #def _onchange_holiday_status_id(self):
    #    for rec in self:
    #        rec.condicion = False
            # No hagas nada si aún no hay tipo seleccionado
            #if not rec.holiday_status_id:
            #    rec.condicion = False
            #    continue
#
           #
            #txt = rec.holiday_status_id.condicion or False
            #rec.condicion ='111' txt
    

    @api.depends('employee_id', 'holiday_status_id', 'request_date_from')
    def _compute_display_name(self):
        for leave in self:
            leave.display_name = _("%(employee)s en %(type)s: %(days)s días (%(date)s)") % {
                'employee': leave.employee_id.name or '',
                'type': leave.holiday_status_id.name or '',
                'days': leave.number_of_days_display or 0.0,
                'date': self._format_request_date(leave.request_date_from),
            }

    def _format_request_date(self, date):
        if not date:
            return ''
        return date.strftime('%d-%m-%Y')
    
    # @api.constrains('date_from', 'date_to', 'employee_id')
    # def _check_date(self):
    #     ##le quito este constrain porque no se como crear mas de un permiso
    #     print("QUITE EL CONSTRAIN")