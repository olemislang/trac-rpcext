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
Test suite for Trac extension implementing Hessian protocol.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

__all__ = ()

from tracrpc.tests import TracRpcTestCase 

from pyhessian.client import HessianProxy

from ..util import TracRpcProtocolTestSuite

class PyHessianTestCase(TracRpcTestCase):
  '''Base class for test cases powered by python-hessian client.
  '''
  def setUp(self):
    TracRpcTestCase.setUp(self)
    self.anon = HessianProxy(self._testenv.url_anon)
    self.user = HessianProxy(self._testenv.url_user)
    self.admin = HessianProxy(self._testenv.url_admin)

  def assertFaultMatches(self, e, expected_code, expected_msg,
                         expected_detail, msg=None):
    self.assertEqual(expected_code, e.code, msg=msg)
    self.assertEqual(expected_msg, e.message, msg=msg)
    self.assertRegex(e.detail, expected_detail, msg=msg)

  def tearDown(self):
    self.anon = self.user = self.admin = None
    TracRpcTestCase.tearDown(self)


def test_suite():
    suite = TracRpcProtocolTestSuite()
    # Hessian test suite
    from . import api, ticket, search, wiki
    for mod in (api, ticket, search, wiki):
      suite.addTest(mod.test_suite())
    return suite

