# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    to_inventory = fields.Boolean("To inventory", default=True)
    
    def write(self, vals):
        if "to_inventory" in vals:
            self.product_variant_ids.to_inventory = vals.get("to_inventory")
        return super().write(vals)
