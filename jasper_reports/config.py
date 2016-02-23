# -*- coding: utf-8 -*-

import logging
import os

from openerp import release
from openerp.tools.config import config, configmanager

_logger = logging.getLogger(__name__)


def jasper_data_dir(self):
    """ Get -and create if necessary- the JasperReports' data dir. """
    d = os.path.join(self['data_dir'], 'jasper_reports', release.series)
    if not os.path.exists(d):
        os.makedirs(d, 0o700)
    else:
        assert os.access(d, os.W_OK), \
            "%s: directory is not writable" % d
    return d

configmanager.jasper_data_dir = property(jasper_data_dir)

_logger.info('jasper data path: %s', config.jasper_data_dir)
