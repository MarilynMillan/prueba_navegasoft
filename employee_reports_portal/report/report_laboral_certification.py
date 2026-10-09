from odoo import api, models
from .report_laboral_certification_base import LaboralCertificationBase

class LaboralCertificationSalary(models.AbstractModel):
    _name = 'report.employee_reports_portal.laboral_c'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        return LaboralCertificationBase.get_report_values(self, docids, data)
