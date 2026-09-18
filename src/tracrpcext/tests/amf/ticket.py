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
Test suite for Trac Hessian compliance with ticket API.

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
from . import Py3AMFTestCase

from pyamf.remoting import RemotingError

class Py3AMFTicketTestCase(Py3AMFTestCase):

  def test_create_get_delete(self):
    rpc_tckt = self.admin.getService('ticket')
    tid = rpc_tckt.create("create_get_delete", "fooy", {})

    _tid, time_created, time_changed, attributes = rpc_tckt.get(tid)
    self.assertEqual(_tid, tid)
    self.assertEqual('fooy', attributes['description'])
    self.assertEqual('create_get_delete', attributes['summary'])
    self.assertEqual('new', attributes['status'])
    self.assertEqual('admin', attributes['reporter'])
    rpc_tckt.delete(tid)
    # Check that ticket no longer exists
    try:
      rpc_tckt.get(tid)
    except RemotingError as e:
      self.assertEqual(
        f'Ticket {tid} does not exist.',
        e.args[0]
      )
    else:
      self.fail('Unexpected success')


def test_suite():
  suite = TracRpcProtocolTestSuite()
  suite.addTest(makeSuite(Py3AMFTicketTestCase))
  return suite


if __name__ == '__main__':
  unittest.main(defaultTest='test_suite')

