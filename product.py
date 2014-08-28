# -*- coding: utf-8 -*-
"""
    product.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from nereid import url_for
from flask import json

__all__ = [
    'Template', 'Product', 'ProductVariationAttributes',
]
__metaclass__ = PoolMeta


class Template:
    "Product Template"
    __name__ = 'product.template'

    variation_attributes = fields.One2Many(
        'product.variation_attributes', 'template', 'Variation Attributes',
    )

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()
        cls._error_messages.update({
            'missing_attributes':
                "Please define following attributes for product %s: %s"
        })

    def validate_variation_attributes(self):
        for product in self.products_displayed_on_eshop:
            product.validate_attributes()

    @classmethod
    def validate(cls, templates):
        super(Template, cls).validate(templates)
        for template in templates:
            template.validate_variation_attributes()

    def get_product_variation_data(self, as_json=False):
        """Returns json data for product for variants
        """
        variants = []
        varying_attributes = []

        for product in self.products_displayed_on_eshop:
            res = product.attributes or {}
            variants.append({
                'id': product.id,
                'rec_name': product.rec_name,
                'code': product.code,
                'price': product.sale_price(1),
                'url': url_for('product.product.render', uri=product.uri),
                'attributes': res,
            })

        for varying_attrib in self.variation_attributes:
            # TODO: This assumes that the attribute is a selection
            # attribute.
            #
            # I feel that this can be improved, by just looking at every
            # attribute and looking at the attribute values and making a
            # set out of it. This will be costly, but could be easily
            # cached and invalidated on product data change.
            varying_attributes.append({
                'sequence': varying_attrib.sequence,
                'name': varying_attrib.attribute.name,
                'widget': varying_attrib.widget,

                # TODO: Add support for more attribute types
                'options': json.loads(varying_attrib.attribute.selection_json),
            })

        rv = {
            'variants': variants,
            'varying_attributes': varying_attributes,
        }
        if as_json:
            return json.dumps(rv)
        return rv


class Product:
    "Product"
    __name__ = 'product.product'

    @classmethod
    def __setup__(cls):
        super(Product, cls).__setup__()
        cls._error_messages.update({
            'missing_attributes':
                "Please define following attributes for product %s: %s"
        })

    def validate_attributes(self):
        """Check if product defines all the attributes specified in
        template variation attributes.
        """
        if not self.displayed_on_eshop:
            return
        required_attrs = set(
            [v.attribute.name for v in self.template.variation_attributes]
        )
        missing = required_attrs - \
            set(self.attributes.keys() if self.attributes else [])
        if missing:
            self.raise_user_error(
                "missing_attributes",
                (self.rec_name, ','.join(map(unicode, missing)))
            )

    @classmethod
    def validate(cls, products):
        super(Product, cls).validate(products)
        for product in products:
            product.validate_attributes()


class ProductVariationAttributes(ModelSQL, ModelView):
    "Variation attributes for product template"
    __name__ = 'product.variation_attributes'

    sequence = fields.Integer('Sequence')
    template = fields.Many2One('product.template', 'Template', required=True)
    attribute = fields.Many2One(
        'product.attribute', 'Attribute', required=True,
        domain=[('sets', '=',
                Eval('_parent_template', {}).get('attribute_set', -1))],
    )
    widget = fields.Selection([
        ('dropdown', 'Dropdown'),
        ('swatches', 'Swatches'),
    ], 'Widget', required=True)

    @staticmethod
    def default_widget():
        return 'dropdown'

    @staticmethod
    def default_sequence():
        return 10
