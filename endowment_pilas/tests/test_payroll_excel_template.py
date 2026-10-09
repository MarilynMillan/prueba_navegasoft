import base64

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.endowment_pilas.wizard.payroll_excel_wizard import (
    PILA_TEMPLATE_ATTACHMENT_PARAM,
)


@tagged('post_install', '-at_install')
class TestPayrollExcelTemplate(TransactionCase):

    def setUp(self):
        super().setUp()
        self.config = self.env['ir.config_parameter'].sudo()
        self.config.search([
            ('key', '=like', '%s.%%' % PILA_TEMPLATE_ATTACHMENT_PARAM),
        ]).unlink()
        self.other_company = self.env['res.company'].create({
            'name': 'Other company',
        })

    def _get_company_template_param(self, company):
        return '%s.%s' % (
            PILA_TEMPLATE_ATTACHMENT_PARAM,
            company.id,
        )

    def _create_wizard(self, values=None):
        wizard_values = {'sucursal_codigo': '001'}
        if values:
            wizard_values.update(values)
        return self.env['hr.payroll.excel.wizard'].create(wizard_values)

    def test_uploaded_template_is_saved_as_company_template(self):
        template_content = b'template content'
        wizard = self._create_wizard({
            'plantilla_excel': base64.b64encode(template_content),
            'plantilla_excel_name': 'custom_template.xlsx',
        })

        self.assertEqual(wizard._get_template_content(), template_content)

        attachment_id = int(
            self.config.get_param(
                self._get_company_template_param(self.env.company)
            )
        )
        attachment = self.env['ir.attachment'].browse(attachment_id)
        self.assertEqual(attachment.name, 'custom_template.xlsx')
        self.assertEqual(attachment.company_id, self.env.company)
        self.assertEqual(
            base64.b64decode(attachment.datas),
            template_content
        )

        next_wizard = self._create_wizard()
        self.assertEqual(
            next_wizard.plantilla_guardada_nombre,
            'custom_template.xlsx'
        )
        self.assertEqual(next_wizard._get_template_content(), template_content)
        self.assertEqual(
            base64.b64decode(next_wizard.plantilla_excel),
            template_content
        )
        self.assertEqual(
            next_wizard.plantilla_excel_name,
            'custom_template.xlsx'
        )

    def test_onchange_uploaded_template_is_saved_as_company_template(self):
        template_content = b'onchange template content'
        wizard = self._create_wizard()
        wizard.plantilla_excel = base64.b64encode(template_content)
        wizard.plantilla_excel_name = 'onchange_template.xlsx'

        wizard._onchange_plantilla_excel()

        attachment_id = int(
            self.config.get_param(
                self._get_company_template_param(self.env.company)
            )
        )
        attachment = self.env['ir.attachment'].browse(attachment_id)
        self.assertEqual(attachment.name, 'onchange_template.xlsx')
        self.assertEqual(attachment.company_id, self.env.company)
        self.assertEqual(
            base64.b64decode(attachment.datas),
            template_content
        )
        self.assertEqual(
            wizard.plantilla_guardada_nombre,
            'onchange_template.xlsx'
        )

    def test_generate_requires_branch_code(self):
        wizard = self.env['hr.payroll.excel.wizard'].new({})

        with self.assertRaises(UserError):
            wizard._validate_generate_excel_fields()

    def test_company_template_is_not_shared_between_companies(self):
        template_content = b'company template content'
        self._create_wizard({
            'plantilla_excel': base64.b64encode(template_content),
            'plantilla_excel_name': 'company_template.xlsx',
        })._get_template_content()

        other_wizard = self.env['hr.payroll.excel.wizard'].with_company(
            self.other_company
        ).create({'sucursal_codigo': '001'})

        self.assertFalse(other_wizard.plantilla_guardada_nombre)
        with self.assertRaises(UserError):
            other_wizard._get_template_content()

    def test_missing_company_template_raises_user_error(self):
        wizard = self._create_wizard()

        self.assertFalse(wizard.plantilla_guardada_nombre)
        with self.assertRaises(UserError):
            wizard._get_template_content()
