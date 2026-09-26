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
Test suite for Trac JSON-WSP compliance with protocol API.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

import sys
import unittest

from tracrpc import api
from tracrpc.tests import makeSuite, TracRpcTestCase

from tracrpcext._json_wsp import JsonWspProtocol
from ..util import TracRpcProtocolTestSuite
from . import JsonWspTestCase


class ProtocolProviderTestCase(TracRpcTestCase):
    def setUp(self):
        TracRpcTestCase.setUp(self)

    def tearDown(self):
        TracRpcTestCase.tearDown(self)

    def test_rpc_info(self):
        # Just try getting the docs for Hessian to test, it should always exist
        json_wsp = JsonWspProtocol(self._testenv.get_trac_environment())
        name, docs = json_wsp.rpc_info()
        self.assertEqual(name, 'JSON-WSP')
        self.assertIn('Content-Type: application/x-jsonwsp', docs)
        self.assertIn('Content-Type: application/json', docs)


class JsonWspApiTestCase(JsonWspTestCase):

  def test_api_version(self):
    resp = getattr(self.anon, 'system.getAPIVersion')()
    self.assertEqual(api.api_version, resp.result)


def test_suite():
    suite = TracRpcProtocolTestSuite()
    suite.addTest(makeSuite(ProtocolProviderTestCase))
    suite.addTest(makeSuite(JsonWspApiTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

