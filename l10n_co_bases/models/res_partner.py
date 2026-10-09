# -*- coding: utf-8 -*-
# Copyright 2019 NMKSoftware
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.exceptions import ValidationError
import re
import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_available_regime(self):
        return [
            ('48', '48 - Responsable del impuesto sobre las ventas - IVA'),
            ('49', '49 - No responsable del IVA'),
        ]

    first_name = fields.Char(
        string="First Name",
    )
    dv_vat = fields.Char('DV', default=0)
    dv_vat = fields.Char('DV', default=0)
    vat_vd = fields.Char(
        string="Dígito Verificacion",
    )
    vat_dv = fields.Char(
        string="Digito Verificación",
    )
    middle_name = fields.Char(
        string="Middle Name",
    )
    last_name = fields.Char(
        string="Last Name",
    )
    second_last_name = fields.Char(
        string="Second Last Name",
    )
    vat_ref = fields.Char(
        string="NIT Formateado",
        compute="_compute_vat_ref",
        readonly=True,
    )
    vat_type = fields.Selection(
        string=u'Tipo de Documento',
        selection=[
            ('11', u'11 - Registro civil de nacimiento'),
            ('12', u'12 - Tarjeta de identidad'),
            ('13', u'13 - Cédula de ciudadanía'),
            ('21', u'21 - Tarjeta de extranjería'),
            ('22', u'22 - Cédula de extranjería'),
            ('31', u'31 - NIT/RUT'),
            ('41', u'41 - Pasaporte'),
            ('42', u'42 - Documento de identificación extranjero'),
            ('47', u'47 - Permiso especial de permanencia'),
            ('50', u'50 - NIT de otro pais'),
            ('91', u'91 - NUIP'),
        ],
        help = u'Identificacion del Cliente, segun los tipos definidos por la DIAN.',
    )
    ciiu_id = fields.Many2one(
        string='Actividad CIIU',
        comodel_name='res.ciiu',
        domain=[('type', '!=', 'view')],
        help=u'Código industrial internacional uniforme (CIIU)'
    )

    taxes_ids = fields.Many2many(
        string="Customer taxes",
        comodel_name="account.tax",
        relation="partner_tax_sale_rel",
        column1="partner_id",
        column2="tax_id",
        domain="[('type_tax_use','=','sale')]",
        help="Taxes applied for sale.",
    )
    supplier_taxes_ids =  fields.Many2many(
        string="Supplier taxes",
        comodel_name="account.tax",
        relation="partner_tax_purchase_rel",
        column1="partner_id",
        column2="tax_id",
        domain="[('type_tax_use','=','purchase')]",
        help="Taxes applied for purchase.",
    )

    regime_type = fields.Selection(_get_available_regime, string="Regimen", default="48")
    anonymous_customer = fields.Boolean(string="Anonymous customer")
    x_tope = fields.Integer(
        string=u"Tope",
    )

    # @api.model
    # def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
    #     args = args or []
    #     if name:
    #         args = ['|','|',('vat', 'ilike', name + '%'),('name', 'ilike', name),('display_name', 'ilike', name)] + args

    #     return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    def _display_address(self, without_company=False):

        address_format = self.country_id.address_format or \
            self._get_default_address_format()
        args = {
            'street': self.street or '',
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self.country_id.name or '',
            'company_name': self.commercial_company_name or '',
            'city_name': self.city_id and self.city_id.display_name or '',
        }
        for field in self._address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format

        if self.vat_type in ['31','13','22']:
            id_type = {}
            id_type['31'] = 'NIT'
            id_type['13'] = 'CC'
            id_type['22'] = 'CE'
            id_id = id_type[self.vat_type]
        else:
            id_id = 'ID'

        res = address_format % args
        
        if self.vat_ref:
            res = "%s:%s\n%s" % (id_id, self.vat_ref, res)
        else:
            res = "%s:%s\n%s" % (id_id, self.vat, res)

        return res

        
    def _address_fields(self):
        result = super(ResPartner, self)._address_fields()
        result = result + ['city_id']
        return result


    def _compute_vat_ref(self):
        """
        Compute vat_ref field
        """
        for partner in self:
            result_vat = None
            # if partner.vat_type == '31' and partner.vat and partner.vat.isdigit() and len(partner.vat.strip()) > 0:
            #     result_vat = '{:,}'.format(int(partner.vat.strip())).replace(",", ".")
            #     #partner.vat_ref = "%s-%i" % (result_vat,partner.vat_vd)
            #     partner.vat_ref = partner.vat
            # else:
            partner.vat_ref = partner.vat

    @api.constrains("vat_vd")
    def check_vat_dv(self):
        """
        Check vat_vd field
        """
        self.ensure_one()
        # if self.vat_type == '31' and self.vat and self.vat_vd and \
        #    not self.check_vat_co():
        #     _logger.info(u'Importing VAT Number [%s - %i] for "%s" is not valid !' %
        #                 (self.vat, self.vat_vd, self.name))
        #     raise ValidationError(u'NIT/RUT [%s - %i] suministrado para "%s" no supera la prueba del dígito de verificacion, el valor calculado es %s!' %
        #                           (self.vat, self.vat_vd, self.name, self.compute_vat_vd(self.vat)))
        return True

    @api.constrains("vat", "vat_type")
    def check_vat(self):
        """
        Check vat field
        """
        for partner in self:
            if partner.vat:
                if not re.match(r'^\d+$', partner.vat) and partner.vat_type in ['31', '13']:
                    raise ValidationError(_('The vat number must be only numbers, there are characters invalid like letters or empty space'))

                partner.vat.strip()
                partner.check_unique_constraint()

    @api.onchange("vat_type", "vat", "vat_vd", )
    def _onchange_vat_vd(self):
        self.ensure_one()
        self.check_vat_dv()

    def check_vat_co(self):
        """
        Check vat_co field
        """
        self.ensure_one()
        vat_vd = self.vat_vd
        computed_vat_vd = self.compute_vat_vd(self.vat)
        if vat_vd != computed_vat_vd:
            return False
        return True

    def compute_vat_vd(self, rut):
        """
        :param rut(str): rut to check
        
        Obtiene el digito de verificacion de un rut

        :return result(str): vat vd
        """
        result = None
        factores = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
        rut_ajustado=str(rut).rjust( 15, '0')
        s = sum(int(rut_ajustado[14-i]) * factores[i] for i in range(14)) % 11
        if s > 1:
            result =  11 - s
        else:
            result = s

        return str(result)

    @api.onchange('first_name', 'middle_name', 'last_name', 'second_last_name')
    def _onchange_person_names(self):
        if self.company_type == 'person':
            names = [name for name in [self.first_name, self.middle_name, self.last_name, self.second_last_name] if name]
            self.name = u' '.join(names)

    @api.depends('company_type', 'name', 'first_name', 'middle_name', 'last_name', 'second_last_name')
    def copy(self, default=None):
        default = default or {}
        if self.company_type == 'person':
            default.update({
                'first_name': self.first_name and self.first_name + _('(copy)') or '',
                'middle_name': self.middle_name and self.middle_name + _('(copy)') or '',
                'last_name': self.last_name and self.last_name + _('(copy)') or '',
                'second_last_name': self.second_last_name and self.second_last_name + _('(copy)') or '',
            })
        return super(ResPartner, self).copy(default=default)

    def check_unique_constraint(self):
        partner_ids = self.search([
            ('vat','=', self.vat),
            ('vat_type','=', self.vat_type),
            ('parent_id','=',False),
        ])
        partner_ids = partner_ids - self
        
        if len(partner_ids) > 0 and not self.parent_id:
            raise ValidationError(_("VAT %s is already registered for the contact %s") % (self.vat, ';'.join([partner_id.display_name for partner_id in partner_ids])))

    def person_name(self, vals):
        values = vals or {}
        person_field = ['first_name', 'middle_name', 'last_name', 'second_last_name']
        person_names = set(person_field)
        values_keys = set(values.keys())

        if person_names.intersection(values_keys):
            names = []
            for x in person_field:
                if x in values.keys():
                    names += [values.get(x, False) and values.get(x).strip() or '']
                else:
                    names += [self[x] or '']
            name = ' '.join(names)
            if name.strip():
                values.update({
                    'name': name,
                })

        if values.get('name', False):
            values.update({
                'name': values.get('name').strip(),
            })

        return values

    def write(self, values):
        values = self.person_name(values)
        return super(ResPartner, self).write(values)

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self.person_name(values) for values in vals_list]
        return super(ResPartner, self).create(vals_list)
