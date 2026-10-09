from odoo import exceptions, fields, models
from datetime import datetime

class LaboralCertificationBase:
    
    def get_report_values(cls, docids, data=None):
        """Sobreescritura del método para validación de contrato activo
        de los empleados a certificar con salario"""
        employees = cls.env['hr.employee'].search([('id', 'in', docids)])
        for employee in employees:
            # if not employee.current_contract:
            #     raise exceptions.ValidationError("No hay un contrato asignado.")
            employee.text_working = employee.check_current_contract()
            employee.text_working2 = employee.check_current_contract2()

        return {
            'doc_ids': docids,
            'doc_model': 'hr.employee',
            'docs': employees,
        }
    