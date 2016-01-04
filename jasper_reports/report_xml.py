# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (C) 2013 Tadeus Prastowo <tadeus.prastowo@infi-nity.com>
#                         Vikasa Infinity Anugrah <http://www.infi-nity.com>
# Copyright (C) 2011-Today Serpent Consulting Services Pvt. Ltd.
#                         (<http://www.serpentcs.com>)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os
import base64
import unicodedata
from xml.dom.minidom import getDOMImplementation
import logging

from . import jasper_report
from jasper_report import get_file_path

from openerp import api, exceptions, fields, models, _

src_chars = """ '"()/*-+?¿!&$[]{}@#`'^:;<>=~%,\\"""
src_chars = unicode(src_chars, 'iso-8859-1')
dst_chars = """________________________________"""
dst_chars = unicode(dst_chars, 'iso-8859-1')

_logger = logging.getLogger(__name__)


class report_xml_file(models.Model):
    _name = 'ir.actions.report.xml.file'

    file = fields.Binary('File', compute='_compute_file', inverse='_inverse_file')
    filename = fields.Char('File Name', size=256, required=True)
    filepath = fields.Char('File Path', size=256, readonly=True)
    report_id = fields.Many2one(
        'ir.actions.report.xml', 'Report', ondelete='cascade')
    default = fields.Boolean('Default')

    @api.multi
    def _compute_file(self):
        for rec in self:
            rec.file = ''

            if rec.filepath and os.path.isfile(rec.filepath):
                try:
                    with open(rec.filepath, 'rb') as f:
                        rec.file = f.read().encode('base64')
                except Exception as e:
                    _logger.exception('report_xml_file: unable to read %s: %s', rec.filepath, e)

    @api.multi
    def _inverse_file(self):
        dbname = self.env.cr.dbname
        is_tmpl = lambda r: (r.filename or '').lower().endswith('.jrxml')

        for rec in self:
            old_filepath = rec.filepath
            rec.filepath = ''

            if rec.file and rec.filename:
                rec.filepath = get_file_path(dbname if is_tmpl(rec) else '.files', rec.filename)
                with open(rec.filepath, 'wb+') as f:
                    f.write(base64.decodestring(rec.file))
                state = 'created' if rec.filepath != old_filepath else 'updated'
                _logger.info('report_xml_file: %s file %s', state, rec.filepath)

            if old_filepath and rec.filepath != old_filepath and os.path.isfile(old_filepath):
                try:
                    os.unlink(old_filepath)
                    _logger.info('report_xml_file: unlinked obsolete file %s', old_filepath)
                except OSError:
                    _logger.exception('report_xml_file: unable to unlink %s', old_filepath)

    @api.model
    def create(self, vals):
        res = super(report_xml_file, self).create(vals)

        # Update parent report, its default file has changed
        if res.default:
            res.report_id.update()

        return res

    @api.multi
    def write(self, vals):
        res = super(report_xml_file, self).write(vals)

        # Update parent reports, their default file might have changed
        for rec in self:
            rec.report_id.update()

        return res

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.filepath and os.path.exists(rec.filepath):
                os.unlink(rec.filepath)
                _logger.info('report_xml_file: unlinked file %s', rec.filepath)
        return super(report_xml_file, self).unlink()


# Inherit ir.actions.report.xml and add an action to be able to store
# .jrxml and .properties files attached to the report so they can be
# used as reports in the application.
class report_xml(models.Model):
    _inherit = 'ir.actions.report.xml'

    jasper_output = fields.Selection([
        ('html', 'HTML'), ('csv', 'CSV'), ('xls', 'XLS'), ('rtf', 'RTF'),
        ('odt', 'ODT'), ('ods', 'ODS'), ('txt', 'Text'), ('pdf', 'PDF')
    ], 'Jasper Output', default='pdf')
    jasper_file_ids = fields.One2many(
        'ir.actions.report.xml.file', 'report_id', 'Files', help='')
    jasper_model_id = fields.Many2one('ir.model', 'Model', help='')
    jasper_report = fields.Boolean('Is Jasper Report?')
    jasper_main_file_id = fields.Many2one(
        'ir.actions.report.xml.file', 'Main File', compute='_compute_jasper_main_file_id')

    @api.multi
    @api.depends('jasper_file_ids', 'jasper_file_ids.default')
    def _compute_jasper_main_file_id(self):
        for rec in self:
            rec.jasper_main_file_id = rec.jasper_file_ids.filtered(
                lambda r: r.default and r.filename.endswith('.jrxml'))[:1]

    def _get_default_vals(self, jasper_model_id=False):
        res = {}
        if jasper_model_id:
            res['model'] = self.env['ir.model'].browse(jasper_model_id).model
        res['type'] = 'ir.actions.report.xml'
        res['report_type'] = 'pdf'
        res['jasper_report'] = True
        return res

    @api.model
    def create(self, vals):
        if self.env.context.get('jasper_report'):
            vals.update(self._get_default_vals(vals.get('jasper_model_id')))
        return super(report_xml, self).create(vals)

    @api.multi
    def write(self, vals):
        if self.env.context.get('jasper_report'):
            vals.update(self._get_default_vals(vals.get('jasper_model_id')))
        # Avoid infinite loop when updating 'report_rml' value in `update()`.
        res = super(report_xml, self).write(vals)
        if res and not self.env.context.get('jasper_update'):
            self.with_context(jasper_update_silent=True).update()
        return res

    @api.multi
    def update(self):
        IrValues = self.env['ir.values']
        for report in self:
            report = report.with_context(jasper_update=True)
            # Browse attachments and store .jrxml and .properties
            # into jasper_reports/custom_reports directory. Also add
            # or update ir.values data so they're shown on model views.for
            # attachment in self.env['ir.attachment'].browse(attachmentIds)
            if not report.jasper_main_file_id:
                if self.env.context.get('jasper_update_silent'):
                    continue
                raise exceptions.Warning(
                    _('No report has been marked as default! You need '
                      'atleast one jrxml report!'))
            elif len(report.jasper_main_file_id) > 1:
                raise exceptions.Warning(
                    _('There is more than one report marked as default'))

            # Update path into report_rml field.
            report.report_rml = report.jasper_main_file_id.filepath
            report_ref = 'ir.actions.report.xml,%s' % (report.id,)

            values = IrValues.search([('value', '=', report_ref)])
            data = {
                'name': report.name,
                'model': report.model,
                'key': 'action',
                'key2': 'client_print_multi',
                'value': report_ref
            }

            if not values:
                values = IrValues.create(data)
            else:
                for value in values:
                    value.write(data)

            # Ensure the report is registered so it can be used immediately
            jasper_report.register_jasper_report(
                report.report_name, report.model)
        return True

    def normalize(self, text):
        if isinstance(text, unicode):
            text = text.encode('utf-8')
        return text

    def unaccent(self, text):
        if isinstance(text, str):
            text = unicode(text, 'utf-8')
        output = text
        for c in xrange(len(src_chars)):
            if c >= len(dst_chars):
                break
            output = output.replace(src_chars[c], dst_chars[c])
        output = unicodedata.normalize('NFKD', output).encode('ASCII',
                                                              'ignore')
        output = output.strip('_').encode('utf-8')
        return output

    @api.model
    def generate_xml(self, pool, modelName, parentNode, document, depth,
                     first_call):
        if self._context is None:
            self._context = {}
        # First of all add "id" field
        fieldNode = document.createElement('id')
        parentNode.appendChild(fieldNode)
        valueNode = document.createTextNode('1')
        fieldNode.appendChild(valueNode)
        language = self._context.get('lang')
        if language == 'en_US':
            language = False

        # Then add all fields in alphabetical order
        model = pool.get(modelName)
        fields = model._columns.keys()
        fields += model._inherit_fields.keys()
        # Remove duplicates because model may have fields with the
        # same name as it's parent
        fields = sorted(list(set(fields)))
        for field in fields:
            name = False
            if language:
                # Obtain field string for user's language.
                name = pool.get('ir.translation')._get_source(
                    self.env.cr, self.env.uid, '%s,%s' % (modelName, field), 'field', language)
            if not name:
                # If there's not description in user's language,
                # use default (english) one.
                if field in model._columns.keys():
                    name = model._columns[field].string
                else:
                    name = model._inherit_fields[field][2].string

            if name:
                name = self.unaccent(name)
            # After unaccent the name might result in an empty string
            if name:
                name = '%s-%s' % (self.unaccent(name), field)
            else:
                name = field
            # If the first char is not alpha, prepend "_"
            if not name[:1].isalpha():
                name = '_' + name

            fieldNode = document.createElement(name)

            parentNode.appendChild(fieldNode)
            if field in pool.get(modelName)._columns:
                fieldType = model._columns[field]._type
            else:
                fieldType = model._inherit_fields[field][2]._type
            if fieldType in ('many2one', 'one2many', 'many2many'):
                if depth <= 1:
                    continue
                if field in model._columns:
                    newName = model._columns[field]._obj
                else:
                    newName = model._inherit_fields[field][2]._obj
                self.generate_xml(pool, newName, fieldNode, document,
                                  depth - 1, False)
                continue

            value = field
            if fieldType == 'float':
                value = '12345.67'
            elif fieldType == 'integer':
                value = '12345'
            elif fieldType == 'date':
                value = '2009-12-31 00:00:00'
            elif fieldType == 'time':
                value = '12:34:56'
            elif fieldType == 'datetime':
                value = '2009-12-31 12:34:56'

            valueNode = document.createTextNode(value)
            fieldNode.appendChild(valueNode)

        if depth > 1 and modelName != 'Attachments':
            # Create relation with attachments
            fieldNode = document.createElement('%s-Attachments' % self.
                                               unaccent(_('Attachments')))
            parentNode.appendChild(fieldNode)
            self.generate_xml(pool, 'ir.attachment', fieldNode, document,
                              depth - 1, False)

        if first_call:
            # Create relation with user
            fieldNode = document.createElement('%s-User' % self.unaccent
                                               (_('User')))
            parentNode.appendChild(fieldNode)
            self.generate_xml(pool, 'res.users', fieldNode, document,
                              depth - 1, False)

            # Create special entries
            fieldNode = document.createElement('%s-Special' % self.unaccent
                                               (_('Special')))
            parentNode.appendChild(fieldNode)

            newNode = document.createElement('copy')
            fieldNode.appendChild(newNode)
            valueNode = document.createTextNode('1')
            newNode.appendChild(valueNode)

            newNode = document.createElement('sequence')
            fieldNode.appendChild(newNode)
            valueNode = document.createTextNode('1')
            newNode.appendChild(valueNode)

            newNode = document.createElement('subsequence')
            fieldNode.appendChild(newNode)
            valueNode = document.createTextNode('1')
            newNode.appendChild(valueNode)

    @api.model
    def create_xml(self, model, depth):
        if self._context is None:
            self._context = {}
        document = getDOMImplementation().createDocument(None, 'data', None)
        topNode = document.documentElement
        recordNode = document.createElement('record')
        topNode.appendChild(recordNode)
        self.generate_xml(self.pool, model, recordNode, document, depth, True)
        topNode.toxml()
        return topNode.toxml()
