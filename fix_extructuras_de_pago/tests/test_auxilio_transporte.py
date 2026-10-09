from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase


class TestAuxilioTransporte(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.structure_type = cls.env['hr.payroll.structure.type'].create({
            'name': 'Estructura prueba auxilio Odoo 18',
        })
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Nomina prueba auxilio Odoo 18',
            'type_id': cls.structure_type.id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Empleado prueba auxilio Odoo 18',
            'company_id': cls.env.company.id,
        })
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Contrato prueba auxilio Odoo 18',
            'employee_id': cls.employee.id,
            'date_start': date(2025, 1, 1),
            'wage': 2_000_000.0,
            'structure_type_id': cls.structure_type.id,
            'state': 'open',
            'salario_minimo': 1_300_000.0,
            'auxilio_de_transporte': 200_000.0,
            'tipo_auxilio': 'transporte',
        })
        cls.devengado_category = cls.env['hr.salary.rule.category'].create({
            'name': 'Devengados prueba auxilio Odoo 18',
            'code': 'DEVEN',
        })
        cls.rules = {}
        for sequence, code in enumerate(
            ('Basico', 'Comision', 'AuxilioTransporte'), start=1
        ):
            cls.rules[code] = cls.env['hr.salary.rule'].create({
                'name': code,
                'code': code,
                'sequence': sequence,
                'amount_select': 'fix',
                'amount_fix': 0.0,
                'category_id': cls.devengado_category.id,
                'struct_id': cls.structure.id,
            })
        cls.work_type = cls.env['hr.work.entry.type'].search([
            ('code', '=', 'WORK100'),
        ], limit=1)
        if not cls.work_type:
            cls.work_type = cls.env['hr.work.entry.type'].create({
                'name': 'Trabajo prueba auxilio',
                'code': 'WORK100',
            })
        cls.paid_leave_type = cls.env['hr.work.entry.type'].search([
            ('code', '=', 'LicenciaR'),
        ], limit=1)
        if not cls.paid_leave_type:
            cls.paid_leave_type = cls.env['hr.work.entry.type'].create({
                'name': 'Licencia remunerada prueba auxilio',
                'code': 'LicenciaR',
                'is_leave': True,
            })

    def _create_payslip(
        self, date_from, date_to, worked_days=15.0, paid_leave_days=0.0
    ):
        worked_days_lines = [Command.create({
            'work_entry_type_id': self.work_type.id,
            'contract_id': self.contract.id,
            'number_of_days': worked_days,
            'number_of_hours': worked_days * 8,
        })]
        if paid_leave_days:
            worked_days_lines.append(Command.create({
                'work_entry_type_id': self.paid_leave_type.id,
                'contract_id': self.contract.id,
                'number_of_days': paid_leave_days,
                'number_of_hours': paid_leave_days * 8,
            }))
        return self.env['hr.payslip'].create({
            'name': 'Nomina prueba auxilio Odoo 18',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'struct_id': self.structure.id,
            'date_from': date_from,
            'date_to': date_to,
            'worked_days_line_ids': worked_days_lines,
        })

    def _create_salary_line(self, payslip, code, total):
        return self.env['hr.payslip.line'].create({
            'name': code,
            'code': code,
            'salary_rule_id': self.rules[code].id,
            'contract_id': self.contract.id,
            'employee_id': self.employee.id,
            'amount': total,
            'quantity': 1.0,
            'rate': 100.0,
            'total': total,
            'slip_id': payslip.id,
        })

    def test_campos_auxilio_en_contrato(self):
        self.assertEqual(self.contract.salario_minimo, 1_300_000.0)
        self.assertEqual(self.contract.auxilio_de_transporte, 200_000.0)
        self.assertEqual(self.contract.tipo_auxilio, 'transporte')

    def test_primera_quincena_prorratea_auxilio(self):
        payslip = self._create_payslip(
            date(2026, 1, 1), date(2026, 1, 15)
        )

        amount, quantity, rate = payslip.calcular_auxilio_transporte(
            payslip, total_devengado=100_000.0, total_basico=1_000_000.0
        )

        self.assertAlmostEqual(amount, 100_000.0)
        self.assertEqual((quantity, rate), (1.0, 100.0))

    def test_no_paga_auxilio_si_supera_dos_salarios_minimos(self):
        payslip = self._create_payslip(
            date(2026, 1, 1), date(2026, 1, 15)
        )

        amount, quantity, rate = payslip.calcular_auxilio_transporte(
            payslip, total_devengado=100_000.0, total_basico=2_600_000.0
        )

        self.assertEqual((amount, quantity, rate), (0.0, 0.0, 100.0))

    def test_segunda_quincena_revierte_auxilio_anterior(self):
        first_payslip = self._create_payslip(
            date(2026, 1, 1), date(2026, 1, 15)
        )
        self._create_salary_line(first_payslip, 'Basico', 1_300_000.0)
        self._create_salary_line(first_payslip, 'AuxilioTransporte', 100_000.0)
        first_payslip.write({'state': 'done'})
        second_payslip = self._create_payslip(
            date(2026, 1, 16), date(2026, 1, 31)
        )

        amount, quantity, rate = second_payslip.calcular_auxilio_transporte(
            second_payslip,
            total_devengado=100_000.0,
            total_basico=1_300_000.0,
        )

        self.assertAlmostEqual(amount, -100_000.0)
        self.assertEqual((quantity, rate), (1.0, 100.0))

    def test_conectividad_incluye_licencia_remunerada(self):
        self.contract.tipo_auxilio = 'conectividad'
        payslip = self._create_payslip(
            date(2026, 2, 1),
            date(2026, 2, 15),
            worked_days=10.0,
            paid_leave_days=2.0,
        )

        amount, quantity, rate = payslip.calcular_auxilio_transporte(
            payslip, total_devengado=3_000_000.0, total_basico=3_000_000.0
        )

        self.assertAlmostEqual(amount, 80_000.0)
        self.assertEqual((quantity, rate), (1.0, 100.0))
