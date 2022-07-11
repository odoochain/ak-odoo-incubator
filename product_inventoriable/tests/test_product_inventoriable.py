# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import SavepointCase


class TestProductProduct(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env.ref("product.product_product_4_product_template")
        cls.product_product_4 = cls.env.ref("product.product_product_4")

    def test_product_template_to_inventory(self):
        self.template.write({"to_inventory": True})
        self.assertTrue(self.product_product_4.to_inventory)

    def test_product_template_not_to_inventory(self):
        self.template.write({"to_inventory": False})
        self.assertFalse(self.product_product_4.to_inventory)
