from odoo import api, models
from .report_laboral_certification_base import LaboralCertificationBase

class LaboralCertificationSalary(models.AbstractModel):
    _name = 'report.employee_reports_portal.laboral_c_salary'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        return LaboralCertificationBase.get_report_values(self, docids, data)


class LaboralCertificationSalarymas(models.AbstractModel):
    _name = 'report.employee_reports_portal.laboral_c_salary_variable'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        return LaboralCertificationBase.get_report_values(self, docids, data)
    

class LaboralCertificationfn(models.AbstractModel):
    _name = 'report.employee_reports_portal.laboral_c_fn'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        return LaboralCertificationBase.get_report_values(self, docids, data)