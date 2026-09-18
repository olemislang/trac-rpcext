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

from tracrpcext._hessian import HessianProtocol

from ..util import TracRpcProtocolTestSuite
from . import Py3AMFTestCase

from pyamf.remoting import RemotingError

class Py3AMFSearchTestCase(Py3AMFTestCase):

  def test_fragment_in_search(self):
    rpc_tckt = self.admin.getService('ticket')
    t1 = rpc_tckt.create(
      "ticket10786", "", {'type': 'enhancement', 'owner': 'A'}
    )

    try:
      rpc_srch = self.user.getService('search')
      results = rpc_srch.performSearch("ticket10786")
      self.assertEqual(1, len(results))
      self.assertEqual('<span class="new">#%d</span>: enhancement: '
                        'ticket10786 (new)' % t1, results[0][1])
    finally:
      self.assertEqual(0, rpc_tckt.delete(t1))


def test_suite():
  suite = TracRpcProtocolTestSuite()
  suite.addTest(makeSuite(Py3AMFSearchTestCase))
  return suite


if __name__ == '__main__':
  unittest.main(defaultTest='test_suite')

