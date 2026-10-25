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
Test suite for Trac AMF compliance with search API.

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

from ..util import TracRpcProtocolTestSuite
from . import JsonWspTestCase

from pyamf.remoting import RemotingError

class JsonWspSearchTestCase(JsonWspTestCase):
  jsonwsp_services = ('search', 'ticket',)

  def test_fragment_in_search(self):
    ws_tckt = self.admin.service('ticket')
    resp = ws_tckt.create(summary="ticket10786",
                          description="",
                          attributes={'type': 'enhancement', 'owner': 'A'})
    t1 = resp.result

    try:
      ws_srch = self.user.service('search')
      resp = ws_srch.performSearch(query="ticket10786")
      results = resp.result
      self.assertEqual(1, len(results))
      self.assertEqual('<span class="new">#%d</span>: enhancement: '
                        'ticket10786 (new)' % t1, results[0][1])
    finally:
      resp = ws_tckt.delete(id=t1)
      self.assertEqual(0, resp.result)

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
      ws_srch = self.user.service('search')
      resp = ws_srch.performSearch(
        query="nothing_should_be_found"
      )
      results = resp.result
      self.assertEqual([], results)


def test_suite():
  suite = TracRpcProtocolTestSuite()
  suite.addTest(makeSuite(JsonWspSearchTestCase))
  return suite


if __name__ == '__main__':
  unittest.main(defaultTest='test_suite')

