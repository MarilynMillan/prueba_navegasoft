

from odoo import api, fields, models

from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _
from odoo.tools import float_is_zero, float_compare
from datetime import datetime, timedelta, date
from odoo.exceptions import ValidationError

import pprint
import logging
_logger = logging.getLogger(__name__)

def _update_nogap(self, number_increment):
    number_next = self.number_next
    self._cr.execute("SELECT number_next FROM %s WHERE id=%s FOR UPDATE NOWAIT" % (self._table, self.id))
    self._cr.execute("UPDATE %s SET number_next=number_next+%s WHERE id=%s " % (self._table, number_increment, self.id))
    self.invalidate_cache(['number_next'], [self.id])
    return number_next

class IrSequence(models.Model):
    _name = 'ir.sequence'
    _inherit = 'ir.sequence'

    use_dian_control = fields.Boolean('Use DIAN control resolutions')
    remaining_numbers = fields.Integer(default=1, help='Remaining numbers')
    remaining_days = fields.Integer(default=1, help='Remaining days')
    sequence_dian_type = fields.Selection([
        ('invoice_computer_generated', 'Invoice generated from computer'),
        ('pos_invoice', 'POS Invoice')],
        'Type', required=True, default='invoice_computer_generated')
    dian_resolution_ids = fields.One2many('ir.sequence.dian_resolution', 'sequence_id', 'DIAN Resolutions')

    _defaults = {
        'remaining_numbers': 400,
        'remaining_days': 30,
    }

    @api.model
    def check_active_resolution(self, sequence_id):

        dian_resolutions_sequences_ids = self.search([('use_dian_control', '=', True),('id', '=', sequence_id)])

        for record in dian_resolutions_sequences_ids:
            if record:

                if len( record.dian_resolution_ids ) > 1:
                    actual_date = datetime.now().strftime('%Y-%m-%d')

                    for resolution in record.dian_resolution_ids:

                        if resolution.number_next_actual >= resolution.number_from and resolution.number_next_actual <= resolution.number_to and  actual_date >= resolution.date_to:
                            self.check_active_resolution_cron()
                            return True

        return False

    @api.model
    def check_active_resolution_cron(self):

        dian_resolutions_sequences_ids = self.search([('use_dian_control', '=', True)])
        for record in dian_resolutions_sequences_ids:
            if record:

                if len( record.dian_resolution_ids ) > 1:
                    actual_date = datetime.now().strftime('%Y-%m-%d')
                    _active_resolution = False


                    for resolution in record.dian_resolution_ids:

                        if resolution.number_next_actual >= resolution.number_from and resolution.number_next_actual <= resolution.number_to and  actual_date >= resolution.date_to and resolution.active_resolution:
                            continue
                            continue

                    _active_resolution = False

                    for resolution in record.dian_resolution_ids:
                        if _active_resolution:
                            continue
                            continue

                        if resolution.number_next_actual >= resolution.number_from and resolution.number_next_actual <= resolution.number_to and  actual_date <= resolution.date_to:
                            record.dian_resolution_ids.write({
                                'active_resolution' : False
                            })

                            resolution.write({
                                'active_resolution' : True
                            })

                            _active_resolution = True

    def _next(self, sequence_date=None):
        if not self.use_dian_control:
            return super(IrSequence, self)._next()

        seq_dian_actual = self.env['ir.sequence.dian_resolution'].search([('sequence_id','=',self.id),('active_resolution','=',True)], limit=1)
        if seq_dian_actual.exists():
            number_actual = seq_dian_actual._next()
            import re
            long_total = len(number_actual)
            lista = re.findall(r"\d+", number_actual)
            number = lista[0]
            prefi =  number_actual[0:long_total-len(number)]
            if int(number) > seq_dian_actual['number_to']:
                seq_dian_next = self.env['ir.sequence.dian_resolution'].search([('sequence_id','=',self.id),('active_resolution','=',True)], limit=1, offset=1)
                if seq_dian_next.exists():
                    seq_dian_actual.active_resolution = False
                    return seq_dian_next._next()
            return number_actual
        return super(IrSequence, self)._next()

    @api.constrains('dian_resolution_ids')
    def val_active_resolution(self):

        _active_resolution = 0

        if self.use_dian_control:

            for record in self.dian_resolution_ids:
                if record.active_resolution:
                    _active_resolution += 1

            if _active_resolution > 1:
                raise ValidationError( _('The system needs only one active DIAN resolution') )

            if _active_resolution == 0:
                raise ValidationError( _('The system needs at least one active DIAN resolution') )


class IrSequenceDianResolution(models.Model):
    _name = 'ir.sequence.dian_resolution'
    _description = 'DIAN Resolution Sequence'
    _rec_name = "sequence_id"

    def _get_number_next_actual(self):
        for element in self:
            element.number_next_actual = element.number_next

    def _set_number_next_actual(self):
        for record in self:
            record.write({'number_next': record.number_next_actual or 0})

    @api.depends('number_from')
    def _get_initial_number(self):
        for record in self:
            if not record.number_next:
                record.number_next = record.number_from

    resolution_number = fields.Char('Resolution number', required=True)
    date_from = fields.Date('From', required=True)
    date_to = fields.Date('To', required=True)
    number_from = fields.Integer('Initial number', required=True)
    number_to = fields.Integer('Final number', required=True)
    number_next = fields.Integer('Next Number', compute='_get_initial_number', store=True)
    number_next_actual = fields.Integer(compute='_get_number_next_actual', inverse='_set_number_next_actual',
                                 string='Next Number', required=True, default=1, help="Next number of this sequence")
    active_resolution = fields.Boolean('Active resolution', required=False)
    sequence_id = fields.Many2one("ir.sequence", 'Main Sequence', required=True, ondelete='cascade')

    def _next(self):
        #number_next = self.env['ir.sequence']._update_nogap(self, 1)
        number_next = _update_nogap(self, self.sequence_id.number_increment)
        return self.sequence_id.get_next_char(number_next)

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info(vals_list)
        return super(IrSequenceDianResolution, self).create(vals_list)
