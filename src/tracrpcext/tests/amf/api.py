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
Test suite for Trac AMF compliance with protocol API.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

import unittest

from tracrpcext._amf import AMFProtocol
from tracrpc.tests import makeSuite, TracRpcTestCase, TracRpcTestSuite

class ProtocolProviderTestCase(TracRpcTestCase):
    def setUp(self):
        TracRpcTestCase.setUp(self)

    def tearDown(self):
        TracRpcTestCase.tearDown(self)

    def test_rpc_info(self):
        # Just try getting the docs for AMF to test, it should always exist
        amf = AMFProtocol(self._testenv.get_trac_environment())
        name, docs = amf.rpc_info()
        self.assertEqual(name, 'AMF')
        self.assertIn('Content-Type: application/x-amf', docs)


def test_suite():
    suite = TracRpcTestSuite()
    suite.addTest(makeSuite(ProtocolProviderTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

