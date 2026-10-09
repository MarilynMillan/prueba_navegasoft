# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PayrollRecargoRule(models.Model):
    _name        = "payroll.recargo.rule"
    _description = "Regla de Recargo"
    _order       = "sequence, id"

    name   = fields.Char(required=True)
    active = fields.Boolean(default=True)

    sequence = fields.Integer(default=10)

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    work_entry_type_id = fields.Many2one(
        "hr.work.entry.type",
        string="Tipo Work Entry",
        required=True,
    )

    hour_from = fields.Float(
        string="Hora desde",
        required=True,
        help="Formato decimal: 21.0, 6.5, etc.",
    )
    hour_to = fields.Float(
        string="Hora hasta",
        required=True,
    )

    apply_on_normal  = fields.Boolean("Aplica día normal")
    apply_on_sunday  = fields.Boolean("Aplica domingo")
    apply_on_holiday = fields.Boolean("Aplica feriado")

    carry_previous_day_df = fields.Boolean(
        string="Hereda DF del día anterior",
        help=(
            "Para rangos 00:00-06:00 cuando NO se detecta slot de tarde previo "
            "(21:00-24:00 del día anterior): aplica esta regla DF si el día "
            "anterior fue domingo o festivo. Tiene prioridad sobre la regla "
            "Normal del mismo intervalo."
        ),
    )

    apply_art_161_weekly_limit = fields.Boolean(
        string="Aplicar validacion semanal Art. 161 CST",
        help=(
            "Si esta activo, el recargo solo se genera cuando el contrato este "
            "marcado como turnos sucesivos y el acumulado semanal supere el "
            "umbral configurado en la compania."
        ),
    )

    date_from = fields.Date("Vigente desde")
    date_to   = fields.Date("Vigente hasta")

    notes = fields.Text("Notas")

    @api.constrains("hour_from", "hour_to")
    def _check_hours(self):
        for rec in self:
            if rec.hour_from < 0 or rec.hour_from > 24:
                raise ValidationError(_("Hora desde inválida (debe estar entre 0 y 24)."))
            if rec.hour_to < 0 or rec.hour_to > 24:
                raise ValidationError(_("Hora hasta inválida (debe estar entre 0 y 24)."))
            if rec.hour_from == rec.hour_to:
                raise ValidationError(_("Hora desde y hasta no pueden ser iguales."))


class HrRuleTimeWindow(models.Model):
    _name        = "hr.rule.time.window"
    _description = "Ventanas horarias para bonos y auxilios"
    _order       = "sequence, id"

    name   = fields.Char(required=True)
    active = fields.Boolean(default=True)

    sequence = fields.Integer(default=10)

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    rule_type = fields.Selection([
        ("mobility",   "Bono Movilidad"),
        ("rodamiento", "Auxilio Rodamiento"),
    ], required=True, default="mobility", index=True)

    check_in_from  = fields.Float(string="Entrada desde",  required=True)
    check_in_to    = fields.Float(string="Entrada hasta",  required=True)
    check_out_from = fields.Float(string="Salida desde",   required=True)
    check_out_to   = fields.Float(string="Salida hasta",   required=True)

    apply_on_normal  = fields.Boolean("Aplica día normal")
    apply_on_sunday  = fields.Boolean("Aplica domingo")
    apply_on_holiday = fields.Boolean("Aplica feriado")

    date_from = fields.Date("Vigente desde")
    date_to   = fields.Date("Vigente hasta")

    notes = fields.Text("Notas")

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(_("La fecha fin no puede ser menor a la fecha inicio."))

    @api.constrains("check_in_from", "check_in_to", "check_out_from", "check_out_to")
    def _check_hours(self):
        for rec in self:
            for val in [rec.check_in_from, rec.check_in_to, rec.check_out_from, rec.check_out_to]:
                if val < 0 or val > 24:
                    raise ValidationError(_("Todas las horas deben estar entre 0 y 24."))
