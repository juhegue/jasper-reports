# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (C) 2013 Tadeus Prastowo <tadeus.prastowo@infi-nity.com>
#                         Vikasa Infinity Anugrah <http://www.infi-nity.com>
# Copyright (C) 2011-Today Serpent Consulting Services Pvt. Ltd.
#                         (<http://www.serpentcs.com>)
# Copyright (C) 2015-Today Diagram Software, S.L.
#                         (<http://www.diagram.es>)
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
import time
import socket
import subprocess
import xmlrpclib
import logging

from openerp import modules, tools
from openerp.exceptions import except_orm
from openerp.tools.translate import _

JASPER_CWD = modules.get_module_resource('jasper_reports', 'java')
JASPER_LIB = os.path.join(JASPER_CWD, 'lib', '*')
CUSTOM_REPORTS = modules.get_module_resource(
    'jasper_reports', 'custom_reports')
CLASSPATH_SEPARATOR = ';' if os.name == 'nt' else ':'


class JasperServer(object):
    def __init__(self, port=8090, dbname=None):
        self.port = port
        self.pidfile = None
        url = 'http://localhost:%d' % port
        self.proxy = xmlrpclib.ServerProxy(url, allow_none=True)
        self.logger = logging.getLogger(__name__)
        self._classpath = self.build_classpath(dbname)
        self.logger.debug('CLASSPATH=%s', self._classpath)

    def error(self, message):
        if self.logger:
            self.logger.error("%s" % message)

    def path(self):
        return os.path.abspath(os.path.dirname(__file__))

    def setPidFile(self, pidfile):  # [DEPRECATED]
        self.pidfile = pidfile

    def build_classpath(self, dbname):
        """
        Return CLASSPATH. It is composed of:
            * jasper_reports/java: JasperReport's main folder
            * jasper_reports/java/lib/*: Java libraries
            * jasper_reports/custom_reports: Common report files
            * <data_dir>/jasper_reports/<release>/<dbname>: DB report files
        """
        return CLASSPATH_SEPARATOR.join([
            JASPER_CWD,
            JASPER_LIB,
            CUSTOM_REPORTS,
            os.path.join(tools.config.jasper_data_dir, dbname)
        ])

    def start(self):
        env = os.environ.copy()
        env['CLASSPATH'] = self._classpath

        # Set headless = True because otherwise, java may use
        # existing X session and if session is closed JasperServer
        # would start throwing exceptions. So we better avoid
        # using the session at all.
        command = ['java', '-Djava.awt.headless=true', '-Xmx1024M',
                   'com.nantic.jasperreports.JasperServer',
                   unicode(self.port)]
        process = subprocess.Popen(command, env=env, cwd=JASPER_CWD)

        if tools.config['jasperpid']:
            with open(tools.config['jasperpid'], 'w') as f:
                f.write(str(process.pid))

    def execute(self, *args):
        """
        Render report and return the number of pages generated.
        """
        try:
            return self.proxy.Report.execute(*args)
        except (xmlrpclib.ProtocolError, socket.error) as e:
            self.start()
            for x in xrange(40):
                time.sleep(1)
                try:
                    return self.proxy.Report.execute(*args)
                except (xmlrpclib.ProtocolError, socket.error) as e:
                    self.error("EXCEPTION: %s %s" % (str(e), str(e.args)))
                    pass
                except xmlrpclib.Fault as e:
                    raise except_orm(_('Report Error'), e.faultString)
        except xmlrpclib.Fault as e:
            raise except_orm(_('Report Error'), e.faultString)

# vim:noexpandtab:smartindent:tabstop=8:softtabstop=8:shiftwidth=8:
