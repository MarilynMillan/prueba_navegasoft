from odoo import models, fields, api
import datetime

class IncomeWithholdingReport(models.TransientModel):
    _name = "income.withholding.report"
    
    def _get_company(self):    
        """Metodo para obtener la compañia del empleado seleccionado"""
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        return docs.company_id.id

    def _get_employee(self):
        """Metodo para obtener el empleado"""
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        return docs.id
    
    company_id = fields.Many2one('res.company', default=_get_company)
    employee_id = fields.Many2one('hr.employee', default=_get_employee)
    certificate_year = fields.Selection(selection='_get_years', string='Taxable year')
    
    @api.onchange('building')
    def _get_years(self):    
        """Metodo que genera una lista de años hasta el año actual desde el año 2000"""
        year_list = []
        for i in range(2000, datetime.datetime.now().year):
            year_list.append((i, str(i)))
        year_list.sort(reverse=True)
        return year_list
    
    def print_report(self):
        """Metodo llamado desde Wizard para generar el reporte, envia los datos a mostrar y los datos del reporte"""
        data = {
            'ids': self.ids,
            'model': self._name,
            'form':{
                'company_id': self.company_id.id,
                'employee_id': self.employee_id.id,
                'certificate_year': self.certificate_year
            }
        }
        return self.env.ref('employee_reports_portal.action_report_income_withholding_certification').report_action(self, data=data)
