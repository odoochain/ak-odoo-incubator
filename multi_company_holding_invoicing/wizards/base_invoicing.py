# -*- coding: utf-8 -*-
# © 2015 Akretion (http://www.akretion.com)
# Sébastien BEAU <sebastien.beau@akretion.com>
# Chafique Delli <chafique.delli@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class BaseHoldingInvoicing(models.AbstractModel):
    _name = 'base.holding.invoicing'

    @api.model
    def _get_invoice_line_data(self, data):
        if self.env.context.get('agree_group_by') == 'none':
            return [data]
        else:
            read_fields, groupby = self._get_group_fields()
            read_fields += ['name', 'client_order_ref']
            groupby += ['name', 'client_order_ref']
            return self.env['sale.order'].read_group(
                data['__domain'], read_fields, groupby, lazy=False)

    @api.model
    def _get_accounting_value_from_product(self, data_line, product):
        # We do not have access to the partner here so we can not
        # play correctly the onchange
        # We need to refactor the way to generate the line
        # Refactor will be done in V10
        # for now we just read the info on the product
        # you need to set the tax by yourself
        if self.env.context.get('agree_group_by') == 'none':
            name = product.name
        else:
            name = '%s - %s' % (
                data_line['name'], data_line.get('client_order_ref', ''))
        return {
            'name': name,
            'product_id': product.id,
            'account_id': (product.property_account_income_id or
                           product.categ_id.property_account_income_categ_id
                           ).id,
        }

    @api.model
    def _prepare_invoice_line(self, data_line):
        agree = self.env['agreement'].browse(data_line['agreement_id'][0])
        vals = self._get_accounting_value_from_product(
            data_line, agree.holding_product_id)
        vals.update({
            'price_unit': data_line['amount_untaxed'],
            'quantity': data_line.get('quantity', 1),
        })
        return vals

    @api.model
    def _prepare_invoice(self, data, lines):
        # get default from native method _prepare_invoice
        # use first sale order as partner and agreement are the same
        sale = self.env['sale.order'].search(data['__domain'], limit=1)
        vals = sale._prepare_invoice()
        vals.update({
            'origin': _('Holding Invoice'),
            'company_id': self.env.context['force_company'],
            'user_id': self.env.uid,
            'invoice_line_ids': [(6, 0, lines.ids)],
        })
        # Remove fiscal position from vals
        # Because fiscal position in vals is not that of the 'force_company'
        if vals.get('fiscal_position'):
            vals['fiscal_position'] = False
        return vals

    @api.model
    def _get_group_fields(self):
        return NotImplemented

    @api.model
    def _get_invoice_data(self, domain):
        read_fields, groupby = self._get_group_fields()
        return self.env['sale.order'].read_group(
            domain, read_fields, groupby, lazy=False)

    @api.model
    def _get_company_invoice(self, data):
        return NotImplemented

    @api.model
    def _link_sale_order(self, invoice, sales):
        return NotImplemented

    @api.model
    def _link_sale_order_line(self, invoice_lines, sale_lines):
        return NotImplemented

    @api.model
    def _create_inv_lines(self, val_lines):
        inv_line_obj = self.env['account.invoice.line']
        lines = inv_line_obj.browse(False)
        for val_line in val_lines:
            lines |= inv_line_obj.create(val_line)
        return lines

    @api.model
    def _generate_invoice(self, domain, invoice_date=None):
        self = self.suspend_security()
        invoices = self.env['account.invoice'].browse(False)
        _logger.debug('Retrieve data for generating the invoice')
        for data in self._get_invoice_data(domain):
            company = self._get_company_invoice(data)
            agree = self.env['agreement'].browse(data['agreement_id'][0])
            # add company and agreement info in the context
            loc_self = self.with_context(
                force_company=company.id,
                invoice_date=invoice_date,
                agreement_id=agree.id,
                agree_group_by=agree.holding_invoice_group_by)
            _logger.debug('Prepare vals for holding invoice')
            data_lines = loc_self._get_invoice_line_data(data)
            val_lines = []
            for data_line in data_lines:
                val_lines.append(loc_self._prepare_invoice_line(data_line))
            invoice_lines = loc_self._create_inv_lines(val_lines)
            _logger.debug('Link the invoice line with the sale order line')
            sales = self.env['sale.order'].search(data['__domain'])
            sale_lines = self.env['sale.order.line'].search([
                ('order_id', 'in', sales.ids)])
            self._link_sale_order_line(invoice_lines, sale_lines)
            invoice_vals = loc_self._prepare_invoice(data, invoice_lines)
            _logger.debug('Generate the holding invoice')
            invoice = loc_self.env['account.invoice'].create(invoice_vals)
            _logger.debug('Link the invoice with the sale order')
            self._link_sale_order(invoice, sales)
            invoices |= invoice
        return invoices


class HoldingInvoicing(models.TransientModel):
    _inherit = 'base.holding.invoicing'
    _name = 'holding.invoicing'

    @api.model
    def _get_group_fields(self):
        return [
            ['partner_invoice_id', 'agreement_id', 'amount_untaxed'],
            ['partner_invoice_id', 'agreement_id'],
        ]

    @api.model
    def _get_company_invoice(self, data):
        agree = self.env['agreement'].browse(
            data['agreement_id'][0])
        return agree.holding_company_id

    @api.model
    def _link_sale_order(self, invoice, sales):
        self._cr.execute("""UPDATE sale_order
            SET holding_invoice_id=%s, invoice_state='pending'
            WHERE id in %s""", (invoice.id, tuple(sales.ids)))
        invoice.invalidate_cache()


class ChildInvoicing(models.TransientModel):
    _inherit = 'base.holding.invoicing'
    _name = 'child.invoicing'

    @api.model
    def _get_company_invoice(self, data):
        return self.env['res.company'].browse(data['company_id'][0])

    @api.model
    def _link_sale_order(self, invoice, sales):
        sales.write({'invoice_ids': [(6, 0, [invoice.id])],
                     'state': 'done'})
        for order_line in self.env['sale.order.line'].search([
                ('order_id', 'in', sales.ids)]):
            order_line.invoice_status = 'invoiced'

    @api.model
    def _link_sale_order_line(self, invoice_lines, sale_lines):
        sale_lines.write({'invoice_lines': [(6, 0, invoice_lines.ids)]})

    @api.model
    def _get_invoice_line_data(self, data):
        agree = self.env['agreement'].browse(
            data['agreement_id'][0])
        data_lines = super(ChildInvoicing, self)._get_invoice_line_data(data)
        data_lines.append({
            'name': 'royalty',
            'amount_untaxed': data['amount_untaxed'],
            'quantity': - agree.holding_discount / 100.,
            'sale_line_ids': [],
            'agreement_id': [agree.id],
        })
        return data_lines

    @api.model
    def _prepare_invoice_line(self, data_line):
        val_line = super(ChildInvoicing, self).\
            _prepare_invoice_line(data_line)
        # TODO the code is too complicated
        # we should simplify the _get_invoice_line_data
        # and _prepare_invoice_line to avoid this kind of hack
        if data_line.get('name') == 'royalty':
            agree = self.env['agreement'].browse(
                data_line['agreement_id'][0])
            val_line.update(self._get_accounting_value_from_product(
                data_line,
                agree.holding_royalty_product_id))
            val_line['name'] = agree.holding_royalty_product_id.name
        return val_line

    @api.model
    def _prepare_invoice(self, data, lines):
        vals = super(ChildInvoicing, self)._prepare_invoice(data, lines)
        sale = self.env['sale.order'].search(data['__domain'], limit=1)
        holding_invoice = sale.holding_invoice_id
        vals['origin'] = holding_invoice.name
        vals['partner_id'] = holding_invoice.company_id.partner_id.id
        agree = self.env['agreement'].browse(data['agreement_id'][0])
        if agree.journal_id:
            journal_id = agree.journal_id
        else:
            journal_id = self.env['account.invoice'].with_context(
                company_id=data['company_id'][0])._default_journal()
        if not journal_id:
            raise UserError(_(
                'Please define an accounting sale journal for the company %s.',
                data['company_id'][1]))
        vals['journal_id'] = journal_id.id
        partner_data = {
            'type': 'out_invoice',
            'partner_id': holding_invoice.company_id.partner_id.id,
            'company_id': self.env.context['force_company'],
        }
        partner_data = self.env['account.invoice'].play_onchanges(
            partner_data, ['partner_id'])
        vals['account_id'] = partner_data.get('account_id', False)
        return vals

    @api.model
    def _get_group_fields(self):
        return [
            ['partner_invoice_id', 'agreement_id',
             'company_id', 'amount_untaxed'],
            ['partner_invoice_id', 'agreement_id', 'company_id'],
        ]