#!/usr/bin/env python3
"""Captura screenshots del modulo l10n_co_dian_extended."""
import time, os, xmlrpc.client

ODOO_URL = "http://localhost:8068"
DB = "dian_demo"
USER = "admin"
PASS = "admin"
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(DIR, exist_ok=True)

# ── RPC helpers ──
common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PASS, {})
api = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

def x(model, method, *a):
    return api.execute_kw(DB, uid, PASS, model, method, list(a))
def s(model, dom, lim=0):
    return api.execute_kw(DB, uid, PASS, model, 'search', [dom], {'limit': lim})
def c(model, v):
    return api.execute_kw(DB, uid, PASS, model, 'create', [v])
def w(model, ids, v):
    return api.execute_kw(DB, uid, PASS, model, 'write', [ids, v])


def seed():
    """Create demo invoices."""
    co = s('res.country', [('code', '=', 'CO')], 1)[0]
    company = s('res.company', [], 1)[0]
    w('res.company', [company], {'name': 'DEMO COLOMBIA SAS', 'country_id': co})

    # Partners (sin VAT para evitar validacion)
    pids = {}
    for name in ['PROVEEDOR NACIONAL SAS', 'DISTRIBUIDORA BOGOTA LTDA',
                 'SERVICIOS MEDELLIN SA', 'CLIENTE CALI SAS']:
        found = s('res.partner', [('name', '=', name)], 1)
        pids[name] = found[0] if found else c('res.partner', {'name': name, 'country_id': co})

    pj = s('account.journal', [('type', '=', 'purchase')], 1)
    sj = s('account.journal', [('type', '=', 'sale')], 1)
    if not pj:
        print("ERROR: No purchase journal - chart of accounts not installed")
        return {}

    inv = {}
    # Vendor bills
    for key, partner, prod, qty, price in [
        ('pending', 'PROVEEDOR NACIONAL SAS', 'Materia Prima Nacional', 100, 50000),
        ('received', 'DISTRIBUIDORA BOGOTA LTDA', 'Servicios de Consultoria', 1, 15000000),
        ('goods_received', 'SERVICIOS MEDELLIN SA', 'Equipos de Computo', 5, 3500000),
    ]:
        inv[key] = c('account.move', {
            'move_type': 'in_invoice', 'partner_id': pids[partner],
            'journal_id': pj[0], 'invoice_date': '2026-03-15',
            'invoice_line_ids': [(0, 0, {'name': prod, 'quantity': qty, 'price_unit': price})],
        })

    # Sale invoice
    if sj:
        inv['sale'] = c('account.move', {
            'move_type': 'out_invoice', 'partner_id': pids['CLIENTE CALI SAS'],
            'journal_id': sj[0], 'invoice_date': '2026-03-01',
            'invoice_line_ids': [(0, 0, {'name': 'Productos Terminados', 'quantity': 200, 'price_unit': 85000})],
        })

    # Post
    for k, v in inv.items():
        try: x('account.move', 'action_post', [v])
        except Exception as e: print(f"  Post {k}: {e}")

    # Set RADIAN states
    try:
        w('account.move', [inv['received']], {'l10n_co_dian_commercial_state': 'received'})
        w('account.move', [inv['goods_received']], {'l10n_co_dian_commercial_state': 'goods_received'})
    except Exception as e:
        print(f"  States: {e}")

    print(f"Invoices: {inv}")
    return inv


def screenshots(inv):
    from playwright.sync_api import sync_playwright

    def shot(pg, name, **kw):
        pg.screenshot(path=f"{DIR}/{name}", **kw)
        print(f"  {name}")

    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        pg = br.new_context(viewport={'width': 1440, 'height': 900}, locale='es-CO').new_page()

        # Login
        pg.goto(f"{ODOO_URL}/web/login?db={DB}")
        pg.wait_for_load_state('load')
        pg.fill('input[name="login"]', USER)
        pg.fill('input[name="password"]', PASS)
        pg.click('button[type="submit"]')
        pg.wait_for_load_state('load')
        time.sleep(2)
        shot(pg, "01_home.png")

        # Accounting
        pg.goto(f"{ODOO_URL}/odoo/accounting")
        pg.wait_for_load_state('load')
        time.sleep(2)
        shot(pg, "02_contabilidad.png")

        # Vendor bills list
        pg.goto(f"{ODOO_URL}/odoo/accounting/vendor-bills")
        pg.wait_for_load_state('load')
        time.sleep(2)
        shot(pg, "03_facturas_compra_lista.png")

        # Pending bill (030 button visible)
        if inv.get('pending'):
            pg.goto(f"{ODOO_URL}/odoo/accounting/vendor-bills/{inv['pending']}")
            pg.wait_for_load_state('load')
            time.sleep(2)
            shot(pg, "04_factura_pendiente.png")
            shot(pg, "05_botones_radian_header.png", clip={'x': 0, 'y': 0, 'width': 1440, 'height': 480})

        # Received (032 button)
        if inv.get('received'):
            pg.goto(f"{ODOO_URL}/odoo/accounting/vendor-bills/{inv['received']}")
            pg.wait_for_load_state('load')
            time.sleep(2)
            shot(pg, "06_estado_recibido_030.png")

        # Goods received (033/031 buttons)
        if inv.get('goods_received'):
            pg.goto(f"{ODOO_URL}/odoo/accounting/vendor-bills/{inv['goods_received']}")
            pg.wait_for_load_state('load')
            time.sleep(2)
            shot(pg, "07_bienes_recibidos_032.png")

            # Claim wizard
            try:
                btn = pg.locator('button:has-text("Reclamar")')
                if btn.count() > 0:
                    btn.first.click()
                    time.sleep(2)
                    shot(pg, "08_wizard_reclamar_031.png")
                    pg.locator('.modal .btn-close, .modal button:has-text("Cerrar")').first.click()
                    time.sleep(1)
            except: pass

        # Sale invoice
        if inv.get('sale'):
            pg.goto(f"{ODOO_URL}/odoo/accounting/customer-invoices/{inv['sale']}")
            pg.wait_for_load_state('load')
            time.sleep(2)
            shot(pg, "09_factura_venta.png")

        # Sales list
        pg.goto(f"{ODOO_URL}/odoo/accounting/customer-invoices")
        pg.wait_for_load_state('load')
        time.sleep(2)
        shot(pg, "10_facturas_venta_lista.png")

        # Settings
        pg.goto(f"{ODOO_URL}/odoo/settings")
        pg.wait_for_load_state('load')
        time.sleep(3)
        shot(pg, "11_configuracion.png")

        # EDI tab
        if inv.get('pending'):
            pg.goto(f"{ODOO_URL}/odoo/accounting/vendor-bills/{inv['pending']}")
            pg.wait_for_load_state('load')
            time.sleep(2)
            tabs = pg.locator('.o_notebook .nav-link, a.nav-link')
            for i in range(tabs.count()):
                t = tabs.nth(i).inner_text()
                if any(k in t.upper() for k in ['EDI', 'DIAN', 'ELECTR']):
                    tabs.nth(i).click()
                    time.sleep(1)
                    shot(pg, "12_tab_edi_dian.png")
                    break

        br.close()
        print(f"\nScreenshots: {DIR}")


if __name__ == '__main__':
    print("=== Seed ===")
    inv = seed()
    print("\n=== Screenshots ===")
    screenshots(inv)
    print("\n=== Done ===")
