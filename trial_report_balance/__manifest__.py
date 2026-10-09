{
    'name': 'Trial Report Balance',
    'version': "18.0.1.0.0",
    'description': 'Trial Report Balance',
    'summary': 'Trial Report Balance',
    'author': 'Navegasoft',
    'license': 'OPL-1',
    'category': 'account',
    'depends': [
        'account_reports'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security_group.xml',
        'wizard/balance_test_account.xml',
    ],
}
