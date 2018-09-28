# -*- coding: utf-8 -*-
# © 2016 Akretion (http://www.akretion.com)
# Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


{'name': 'Multi Company Holding Invoicing',
 'version': '10.0.0.0.1',
 'category': 'Accounting & Finance',
 'author': 'Akretion, Odoo Community Association (OCA)',
 'website': 'http://www.akretion.com/',
 'license': 'AGPL-3',
 'depends': [
     'account_invoice_inter_company',
     'agreement_sale',
     'base_suspend_security',
     'sale',
     'queue_job',
     'base_onchange_rule',
 ],
 'data': [
     # 'demo/config.xml',
     'views/agreement_view.xml',
     'views/sale_view.xml',
     'views/account_invoice_view.xml',
     'views/queue_view.xml',
     'wizards/wizard_holding_view.xml',
     # 'wizards/sale_make_invoice_view.xml',
 ],
 'demo': [
     'demo/res_company_demo.xml',
     'demo/res_users_demo.xml',
     'demo/agreement_demo.xml',
     'demo/sale_order_demo.xml',
     # 'demo/account_config.yml',
 ],
 'installable': True,
 }