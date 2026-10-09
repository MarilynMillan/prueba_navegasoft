# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    home_office_codes = fields.Char(
        string="Codigos Home Office",
        default="HOME,REMOTE",
        config_parameter="hr_bonus.home_office_codes",
    )
    holiday_we_type_codes = fields.Char(
        string="Codigos WE festivo",
        default="PUBLIC,PH,FEST",
        config_parameter="hr_bonus.holiday_we_type_codes",
    )
    hr_night_shift_weekly_limit = fields.Float(
        string="Umbral semanal turnos sucesivos",
        related="company_id.hr_night_shift_weekly_limit",
        readonly=False,
    )


class ResCompany(models.Model):
    _inherit = "res.company"

    hr_bonus_home_office_codes = fields.Char(
        string="Codigos Home Office (WE)",
        default="HOME,REMOTE",
        help="Codigos de tipos de Work Entry que se consideran Home Office. Ej: HOME,REMOTE",
    )
    hr_bonus_holiday_we_type_codes = fields.Char(
        string="Codigos Festivo (WE)",
        default="PUBLIC,PH,FEST",
        help="Codigos de tipos de Work Entry que se consideran festivo. Ej: PUBLIC,PH,FEST",
    )
    hr_bonus_defer_to_next_quincena = fields.Boolean(
        string="Pagar en la siguiente quincena",
        default=True,
        help="Si esta activo, los bonos, auxilios y recargos se liquidan en la nomina siguiente.",
    )
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
    perc_rec_noct = fields.Float(string="Recargo Nocturno (%)", default=35.0)
    perc_rec_noct_fest = fields.Float(string="Recargo Noct. Festivo (%)", default=75.0)
    perc_rec_diur_dom = fields.Float(string="Recargo Diurno Dominical (%)", default=75.0)
    hr_night_shift_weekly_limit = fields.Float(
        string="Umbral semanal turnos sucesivos",
        default=36.0,
        help=(
            "Horas semanales maximas para contratos en turnos sucesivos sin "
            "generar recargo nocturno segun Art. 161 CST."
        ),
    )
