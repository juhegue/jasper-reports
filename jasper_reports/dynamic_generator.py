# -*- encoding: utf-8 -*-

import os
import tempfile
import base64
import logging
import csv, codecs, cStringIO

logger = logging.getLogger(__name__)


class UnicodeWriter:
    def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow(row)
        data = self.queue.getvalue()
        data = data.decode('utf-8')
        data = self.encoder.encode(data)
        self.stream.write(data)
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def dynamic_generator(self, dataFile, subreportDataFiles):
    base = self.report._module.__dict__["DataGenerator"]

    class CsvDataGenerator(base):
        def __init__(self, parent, dataFile, subreportDataFiles):
            super(CsvDataGenerator, self).__init__(parent.model, parent.pool, parent.cr, parent.uid, parent.ids, parent.context)
            self.parent = parent
            self.imageFiles = dict()

            if parent.report.language() == 'xpath':
                with open(dataFile, 'wb') as f:
                    w = UnicodeWriter(f, encoding='utf-8', delimiter=',')
                    for row in self.generate():
                        data = list()
                        for r in row:
                            data.append(self.field_value(*r)) if isinstance(r, tuple) or isinstance(r, list) else data.append(r)
                        w.writerow(data)

            for subreportInfo in parent.report.subreports():
                subreport = subreportInfo['report']
                if subreport.language() == 'xpath':
                    message = 'Creating CSV '
                    if subreportInfo['pathPrefix']:
                        message += 'with prefix %s ' % subreportInfo['pathPrefix']
                    else:
                        message += 'without prefix '
                    message += 'for file %s' % subreportInfo['filename']
                    logger.info("%s" % message)

                    fd, subreportDataFile = tempfile.mkstemp()
                    os.close(fd)
                    subreportDataFiles.append({
                        'parameter': subreportInfo['parameter'],
                        'dataFile': subreportDataFile,
                        'jrxmlFile': subreportInfo['filename'],
                    })
                    parent.temporaryFiles.append(subreportDataFile)
                    # function with 20 characters max.
                    func_name = 'generate_%s' % subreportInfo['parameter'][0:20].lower()
                    with open(subreportDataFile, 'wb') as f:
                        w = UnicodeWriter(f, encoding='utf-8', delimiter=',')
                        for row in getattr(self, func_name, None)():
                            data = list()
                            for r in row:
                                data.append(self.field_value(*r)) if isinstance(r, tuple) or isinstance(r, list) else data.append(r)
                            w.writerow(data)

        def field_value(self, record, field):
            fields = field.split('.')
            field = fields[0]

            field_type = None
            if field in record._columns:
                field_type = record._columns[field]._type
            elif field in record._inherit_fields:
                field_type = record._inherit_fields[field][2]._type

            if field_type in ('many2one', 'one2many', 'many2many'):
                if len(fields[1:]):
                    record = getattr(record, field)
                    return self.field_value(record, '.'.join(fields[1:]))
                return getattr(record, 'id')

            value = getattr(record, field)

            if field == 'id':
                # Check for field 'id' because we can't find it's type in _columns
                value = str(value)
            elif value in (False,None):
                value = ''
            elif field_type == 'date':
                value = '%s 00:00:00' % str(value)
            elif field_type == 'binary':
                imageId = (record.id, field)
                if imageId in self.imageFiles:
                    fileName = self.imageFiles[ imageId ]
                else:
                    fd, fileName = tempfile.mkstemp()
                    try:
                        os.write( fd, base64.decodestring( value ) )
                    finally:
                        os.close( fd )
                    self.parent.temporaryFiles.append( fileName )
                    self.imageFiles[ imageId ] = fileName
                value = fileName
            elif isinstance(value, unicode):
                value = value.encode('utf-8')
            elif isinstance(value, float):
                value = '%.10f' % value
            elif not isinstance(value, str):
                value = str(value)

            return value

    return CsvDataGenerator(self, dataFile, subreportDataFiles)
