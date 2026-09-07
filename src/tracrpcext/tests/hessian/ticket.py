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
from tracrpc.tests import (Request, b64encode, urlopen, makeSuite,
                           TracRpcTestCase)

from tracrpcext._hessian import HessianProtocol

from ..util import TracRpcProtocolTestSuite

from pyhessian.client import HessianProxy

class HessianTicketTestCase(TracRpcTestCase):
  def setUp(self):
    TracRpcTestCase.setUp(self)
    self.anon = HessianProxy(self._testenv.url_anon)
    self.user = HessianProxy(self._testenv.url_user)
    self.admin = HessianProxy(self._testenv.url_admin)

  def tearDown(self):
    self.anon = self.user = self.admin = None
    TracRpcTestCase.tearDown(self)

  def test_create_get_delete(self):
    tid = getattr(
      self.admin, 'ticket.create'
    )("create_get_delete", "fooy", {})
    tid, time_created, time_changed, attributes = getattr(
      self.admin, 'ticket.get'
    )(tid)
    self.assertEqual('fooy', attributes['description'])
    self.assertEqual('create_get_delete', attributes['summary'])
    self.assertEqual('new', attributes['status'])
    self.assertEqual('admin', attributes['reporter'])
    getattr(
      self.admin, 'ticket.delete'
    )(tid)
    # Check that ticket no longer exists
    reply = getattr(
      self.admin, 'ticket.get'
    )(tid)


def test_suite():
  suite = TracRpcProtocolTestSuite()
  suite.addTest(makeSuite(HessianTicketTestCase))
  return suite


if __name__ == '__main__':
  unittest.main(defaultTest='test_suite')

