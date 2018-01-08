# -*- encoding: utf-8 -*-

""" Hay que definir:
    <property name='OPENERP_MODULE'/>
    <property name='OPENERP_DYNAMIC'/>
"""

import logging

logger = logging.getLogger(__name__)


class DataGenerator(object):
    def __init__(self, model, pool, cr, uid, ids, context):
        self.model = model
        self.pool = pool
        self.cr = cr
        self.uid = uid
        self.ids = ids
        self.context = context

        logger.info('DataGenerator')

        # ids = pool.get('res.company').search(cr, uid, [('id', '>=', 1)])
        # for record in self.pool.get('res.company').browse(self.cr, self.uid, ids, self.context):
        #     print record.name
        
    def generate(self):
        data = list()
        data.append(['Logo', 'Company', 'Partner', 'Number', 'Date', 'Product', 'Quantity', 'Price'])
        for record in self.pool.get(self.model).browse(self.cr, self.uid, self.ids, self.context):
            row = list()
            for record_line in record.invoice_line:
                row.append([record, 'company_id.logo'])
                row.append([record, 'company_id.name'])
                row.append([record, 'partner_id.name'])
                row.append([record, 'number'])
                row.append([record, 'date_invoice'])
                row.append([record_line, 'name'])
                row.append([record_line, 'quantity'])
                row.append([record_line, 'price_unit'])
                data.append(row)
        return data

    def generate_subreport_lin(self):
        data = list()
        data.append(['Product', 'Quantity', 'Price'])
        for record in self.pool.get(self.model).browse(self.cr, self.uid, self.ids, self.context):
            row = list()
            for record_line in record.invoice_line:
                row.append([record_line, 'name'])
                row.append([record_line, 'quantity'])
                row.append([record_line, 'price_unit'])
                data.append(row)
        return data


