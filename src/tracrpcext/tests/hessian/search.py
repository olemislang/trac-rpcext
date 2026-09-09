# -*- coding: utf-8 -*-

# Copyright 2026 Olemis Lang <olemis at gmail.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


"""
Test suite for Trac Hessian compliance with search API.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

import datetime
import time
import unittest

from trac.util.datefmt import to_datetime, to_utimestamp, utc

from tracrpc.util import unicode, xmlrpclib
from tracrpc.tests import Request, b64encode, urlopen, makeSuite
from tracrpc.tests.ticket import RpcTicketTestCase

from tracrpcext._hessian import HessianProtocol

from ..util import TracRpcProtocolTestSuite
from . import PyHessianTestCase

from pyhessian.protocol import Fault

class PyHessianSearchTestCase(PyHessianTestCase):

  def test_fragment_in_search(self):
    t1 = getattr(self.admin, 'ticket.create')(
      "ticket10786", "", {'type': 'enhancement', 'owner': 'A'}
    )

    try:
      results = getattr(self.user, 'search.performSearch')("ticket10786")
      self.assertEqual(1, len(results))
      self.assertEqual('<span class="new">#%d</span>: enhancement: '
                        'ticket10786 (new)' % t1, results[0][1])
    finally:
      self.assertEqual(0, getattr(self.admin, 'ticket.delete')(t1))

  def test_search_none_result(self):
    # Some plugins may return None instead of empty iterator
    # https://trac-hacks.org/ticket/12950

    # Add custom plugin to provoke error
    source = r"""# -*- coding: utf-8 -*-
from trac.core import *
from trac.search.api import ISearchSource
class NoneSearch(Component):
    implements(ISearchSource)
    def get_search_filters(self, req):
        yield ('test', 'Test')
    def get_search_results(self, req, terms, filters):
        self.log.debug('Search plugin returning None')
        return None
"""
    with self._plugin(source, 'NoneSearchPlugin.py'):
      results = getattr(self.user, 'search.performSearch')(
        "nothing_should_be_found"
      )
      self.assertEqual((), results)


def test_suite():
  suite = TracRpcProtocolTestSuite()
  suite.addTest(makeSuite(PyHessianSearchTestCase))
  return suite


if __name__ == '__main__':
  unittest.main(defaultTest='test_suite')

