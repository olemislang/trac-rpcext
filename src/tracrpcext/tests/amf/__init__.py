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
Test suite for Trac extension implementing Action Message Format protocol.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

__all__ = ()

from pyamf.remoting import client

from tracrpc.tests import TracRpcTestCase

from ..util import TracRpcProtocolTestSuite

class Py3AMFTestCase(TracRpcTestCase):
  '''Base class for test cases powered by python-hessian client.
  '''
  def _for_user(self, client, username, secret):
    client.opener = self._opener_auth(client._root_url,
                                 username, secret).open

  def setUp(self):
    TracRpcTestCase.setUp(self)
    # Authenticate through HTTP headers
    self.anon = client.RemotingService(self._testenv.url_anon)
    self.user = client.RemotingService(self._testenv.url_auth)
    self._for_user(self.user, 'user', 'user')
    self.admin = client.RemotingService(self._testenv.url_auth)
    self._for_user(self.admin, 'admin', 'admin')

  def assertFaultMatches(self, e, expected_code, expected_msg,
                         expected_detail, msg=None):
    self.assertEqual(expected_code, e.code, msg=msg)
    self.assertIn(expected_msg, e.message, msg=msg)
    self.assertRegex(e.detail, expected_detail, msg=msg)

  def tearDown(self):
    self.anon = self.user = self.admin = None
    TracRpcTestCase.tearDown(self)


def test_suite():
    suite = TracRpcProtocolTestSuite()
    # AMF test suite
    from . import api, search, ticket, wiki
    for mod in (api, search, ticket, wiki):
      suite.addTest(mod.test_suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

