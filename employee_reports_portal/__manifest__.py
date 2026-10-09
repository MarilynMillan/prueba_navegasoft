# -*- coding: utf-8 -*-
{
    'name': "Reportes y portal empleados",
    'description': 'Reportes de empleados y su respectivo portal para obtenerlos.',
    'summary': 'Módulo reporte y portal de empleado1s',
    'author': "Intello Idea1",
    'license': 'LGPL-3',
    'website': "http://www.intelloidea.com",
    'category': 'Human Resources/Employees',
    'version': '0.1',
    'depends': [
        'hr', 'hr_contract','hr_holidays','hr_payroll','web','website', 
        'base'
    ],
    'application': False,
    'data': [
        'security/ir.model.access.csv',
        'data/hr.certified.concept.csv',
        'views/hr_contract_view.xml',
        'views/hr_employee_view.xml',
        'views/res_company_view.xml',
        'views/employee_page/portal.xml',
        'views/employee_page/hr_leave.xml',
        'views/employee_page/hr_payroll.xml',
        'views/hr_certified_concept_view.xml',
        'views/hr_salary_view.xml',
        'views/hr_salary_rule.xml',
        'views/hr_leave_type.xml',
        'views/res_config_settings_view.xml',
        'report/hr_contract_report.xml',
        'report/report_certificate_footer.xml',
        'report/report_certificate_head.xml',
        'report/report_laboral_certification.xml',
        'report/report_laboral_certification_salary.xml',
        'report/report_laboral_certification_fn.xml',
        'report/report_laboral_certification_fn_salary.xml',
        'wizard/income_witholding_report.xml',
        'report/report_income_withholding_certification.xml',

    ],
    'assets': {
        'web.assets_frontend': [
        #'employee_reports_portal/static/src/js/**/*',
    ],
    },
}
