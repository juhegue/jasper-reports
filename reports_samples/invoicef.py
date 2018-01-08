# -*- encoding: utf-8 -*-

""" Hay que definir:
    <property name='OPENERP_MODULE'/>

    Los campos con el prefijo '__' llaman a este módulo
    <fieldDescription><![CDATA[/data/record/__logo]]></fieldDescription>

"""

import logging

logger = logging.getLogger(__name__)


class DataFunction(object):
    def __init__(self, model, pool, cr, uid, ids, context, record):
        self.model = model
        self.pool = pool
        self.cr = cr
        self.uid = uid
        self.ids = ids
        self.context = context

        logger.info('DataFunction')

    def logo(self, record):
        value = getattr(record, 'logo')

        field_type = 'binary'     # char, date , binary
        return field_type, value

    def date_invoice(self, record):
        value = getattr(record, 'date_invoice')

        field_type = 'date'     # char, date , binary
        return field_type, value

    def price_unit(self, record):
        value = getattr(record, 'price_unit')

        field_type = 'char'     # char, date , binary
        return field_type, value

