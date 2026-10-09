# -*- coding: utf-8 -*-
from odoo import fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    mobility_bonus = fields.Float(
        string="Bono Movilidad (monto por dia aplicable)",
        help="Monto unitario por dia que cumpla las condiciones de Bono Movilidad.",
    )
    aux_rodamiento = fields.Float(
        string="Auxilio Rodamiento (monto por dia aplicable)",
        help="Monto unitario por dia que cumpla las condiciones de Auxilio de Rodamiento.",
    )
    auxilio_de_transporte = fields.Float(
        string="Auxilio de Transporte (monto por dia aplicable)",
    )

    hr_night_shift_successive = fields.Boolean(
        string="Turnos sucesivos Art. 161 CST",
        help=(
            "Marque este contrato cuando aplique la excepcion de turnos "
            "sucesivos para recargos nocturnos segun el acumulado semanal."
        ),
    )
