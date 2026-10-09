from odoo import models, fields, modules,tools , api,_ 


class calidades(models.Model):
    _name = 'account.calidadess'
    
    codigo = fields.Char("Codigo")
    responsabilidad = fields.Char("Responsabilidad")
    descripcion = fields.Text("Descripcion")


class aduaneros(models.Model):
    _name = 'account.aduaneros'
    
    codigo = fields.Char("Codigo")
    responsabilidad = fields.Char("Responsabilidad")
    descripcion = fields.Char("Descripcion")

class partner_fact(models.Model):
    _inherit = 'res.partner'

    vat_vd = fields.Char("Digito de verificacion")
    id_plataforma = fields.Char("id Plataforma")
    password = fields.Char("Password")
    regimen_fiscal = fields.Selection(
        selection=[('48', 'Impuestos sobre la venta del IVA'),
				   ('49', 'No responsables del IVA'),],
        string='regimen_fiscal', 
        default='48'
    )
    ciiu_id = fields.Many2one(
        string='Actividad CIIU',
        comodel_name='res.ciiu',
        domain=[('type', '!=', 'view')],
        help=u'Código industrial internacional uniforme (CIIU)'
    )
    correo_factura = fields.Char("Correo Facturación Electrónica")
    tipo_pago = fields.Selection(    
        selection=[#('1', '1 - Instrumento no definido'),
                   #('2', '2 - Crédito ACH'),
                   #('3', '3 - Débito ACH'),
                   #('4', '4 - Reversión débito de demanda ACH'), 
                   #('5', '5 - Reversión crédito de demanda ACH'),
                   #('6', '6 - Crédito de demanda ACH'), 
                   #('7', '7 - Débito de demanda ACH'), 
                   #('8', '8 - Mantener'), 
                   #('9', '9 - Clearing Nacional o Regional'), 
                   ('10', '10 - Efectivo'), 
                   #('11', '11 - Reversión Crédito Ahorro'), 
                   #('12', '12 - Reversión Débito Ahorro'), 
                   #('13', '13 - Crédito Ahorro'), 
                   #('14', '14 - Débito Ahorro'), 
                   #('15', '15 - Bookentry Crédito'), 
                   #('16', '16 - Bookentry Débito'), 
                   #('17', '17 - Concentración de la demanda en efectivo /Desembolso Crédito (CCD)'), 
                   #('18', '18 - Concentración de la demanda en efectivo / Desembolso (CCD) débito'),
                   #('19', '19 - Crédito Pago negocio corporativo (CTP)'), 
                   ('20', '20 - Cheque'), 
                   #('21', '21 - Poyecto bancario'), 
                   #('22', '22 - Proyecto bancario certificado'), 
                   #('23', '23 - Cheque bancario'), 
                   #('24', '24 - Nota cambiaria esperando aceptación'), 
                   #('25', '25 - Cheque certificado'), 
                   #('26', '26 - Cheque Local'), 
                   #('27', '27 - Débito Pago Neogcio Corporativo (CTP)'), 
                   #('28', '28 - Crédito Negocio Intercambio Corporativo (CTX)'), 
                   #('29', '29 - Débito Negocio Intercambio Corporativo (CTX)'), 
                   #('30', '30 - Transferecia Crédito'), 
                   ('42', '42 - Consignación bancaria'), 
                   ('ZZZ', 'ZZZ - Acuerdo mutuo'),],
        string=_('Tipo de pago'), default='10'
    )
    metodo_pago = fields.Selection(
        selection=[('1', _('Contado')),
				   ('2', _('Credito')),],
        string=_('Método de pago'), 
        default='1'
    )
    tipo_factura = fields.Selection(
        selection=[('1', _('1- Combustibles')),
                   ('2', _('2- Emisor es Autorretenedor')),
                   ('3', _('3- Excluidos y Exentos')),
                   ('4', _('4- Extranjero')),
                   ('5', _('5- Generica')),
                   ('6', _('6- Generica con pago anticipado')),
                   ('7', _('7- Generica con periodo de facturacion')),
                   ('8', _('8- Consorcio')),
                   ('9', _('9- Servicios AIU')),
                   ('10', _('10- Estandar')),],
        string=_('Tipo de factura'),
        default ='10'
    )
    calidades_atributos = fields.Many2many("account.calidadess")
    usuario_aduanero = fields.Many2many("account.aduaneros")
    tipo_contribuyente = fields.Selection([('1','Persona juridica'),('2','Persona natural')],'Tipo de contribuyente')
    tipo_regimen = fields.Selection([('0','Simplificado'),('2','Comun')],'Tipo de Regimen')
    is_colombia = fields.Boolean(compute='_compute_is_colombia', default=False)

    @api.depends('country_id')
    def _compute_is_colombia(self):
        for record in self:
            record.is_colombia = record.company_id.country_id.code == 'CO'
