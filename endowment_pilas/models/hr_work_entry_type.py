from odoo import fields, models

class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    WORK_ENTRY_NOVELTY_CODES = [
        ('SLN', 'SLN - Suspensión del Contrato'),
        ('IGE', 'IGE - Incapacidad por Enfermedad General'),
        ('LMA', 'LMA - Licencia de Maternidad'),
        ('VAL-LR', 'VAL-LR - Vacaciones o Licencia Remunerada'),
        ('AVP', 'AVP - Ausencia por Vacaciones Pagadas'),
        ('VCT', 'VCT - Vacaciones Colectivas'),
        ('IRL', 'IRL - Incapacidad por Accidente de Trabajo / Enfermedad Laboral'),
    ]

    pila_novelty_code = fields.Selection(
        WORK_ENTRY_NOVELTY_CODES,
        string='Código Novedad PILA',
        help="Clasifica esta entrada de trabajo como una novedad específica para el reporte PILA.",
    )