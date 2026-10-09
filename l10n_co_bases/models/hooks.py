from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _unify_l10n_co_bases_cities(env)


def _unify_l10n_co_bases_cities(env):
    MODULE_NAME = 'l10n_co_bases'
    COUNTRY_CODE = 'CO'

    IrModelData = env['ir.model.data']
    City = env['res.city']
    Partner = env['res.partner']
    Country = env['res.country'].search([('code', '=', COUNTRY_CODE)], limit=1)

    if not Country:
        return

    def field_exists(model, field):
        return field in model._fields

    partner_city_fields = [
        'city_id',
        'l10n_co_edi_city_id',
        'l10n_co_edi_municipality_id',
    ]

    imds = IrModelData.search([
        ('module', '=', MODULE_NAME),
        ('model', '=', 'res.city'),
    ])
    cities = City.browse(imds.mapped('res_id')).filtered(
        lambda c: c.country_id.id == Country.id
    )

    if not cities:
        return  # idempotente: si ya se borraron, no hace nada

    for city in cities:
        # buscar ciudad canónica con mismo code+state
        canonical = City.search([
            ('id', '!=', city.id),
            ('code', '=', city.code),
            ('state_id', '=', city.state_id.id),
            ('country_id', '=', city.country_id.id),
        ], limit=1)

        if not canonical:
            # si no hay canónica, lo dejamos (por seguridad)
            continue

        # reasignar partners
        for fname in partner_city_fields:
            if not field_exists(Partner, fname):
                continue
            partners = Partner.search([(fname, '=', city.id)])
            if partners:
                partners.write({fname: canonical.id})

        # borrar ciudad y su xml_id
        city_imds = imds.filtered(lambda r: r.res_id == city.id)
        try:
            city.unlink()
            city_imds.unlink()
        except Exception:
            # si falla por alguna razón, no rompas la instalación
            continue
