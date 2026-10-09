# -*- coding: utf-8 -*-
# Copyright 2019 NMKSoftware
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _

class ResCountry(models.Model):
    _inherit = 'res.country'

    code_dian = fields.Char(
        string='DIAN Code',
        required=False,
        readonly=False
    )

    def name_get(self):
        rec = []
        for recs in self:
            name = '%s [%s]' % (recs.name or '', recs.code or '')
            rec += [ (recs.id, name) ]
        return rec

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Se hereda metodo name search y se sobreescribe para hacer la busqueda 
        por el codigo del pais
        """
        if not args:
            args = []
        args = args[:]
        ids = []
        if name:
            ids = self.search([('code_dian', '=like', name + "%")] + args, limit=limit)
            if not ids:
                ids = self.search([('code', operator, name)] + args,limit=limit)
                if not ids:
                    ids = self.search([('name', operator, name)] + args,limit=limit)
        else:
            ids = self.search(args, limit=100)

        if ids:
            return ids.name_get()
        return self.name_get()

class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    code_department = fields.Char(string="Code department")

    def name_get(self):
        rec = []
        for recs in self:
            name = '%s [%s]' % (recs.name or '', recs.code or '')
            rec += [ (recs.id, name) ]
        return rec

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Se hereda metodo name search y se sobreescribe para hacer la busqueda 
        por el codigo del estado/departamento
        """
        if not args:
            args = []
        args = args[:]
        ids = []
        if name:
            ids = self.search([('code', '=like', name + "%")] + args, limit=limit)
            if not ids:
                ids = self.search([('name', operator, name)] + args,limit=limit)
        else:
            ids = self.search(args, limit=100)

        if ids:
            return ids.name_get()
        return self.name_get()
