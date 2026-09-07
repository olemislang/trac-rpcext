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
Test suite for Trac Hessian compliance with protocol API.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

import unittest

from tracrpc.tests import makeSuite, TracRpcTestCase

from pyhessian import encoder, protocol

from tracrpcext._hessian import HessianRpcEncoder, HessianProtocol
from tracrpcext.tests.util import TracRpcProtocolTestSuite

class HessianEncoderTestCase(unittest.TestCase):
    def setUp(self):
        self.encoder = HessianRpcEncoder()

    def tearDown(self):
        del self.encoder

    def test_encoder_setup(self):
        self.assertIn(protocol.Fault, encoder.RETURN_TYPES)
        self.assertIn(protocol.Reply, encoder.RETURN_TYPES)

    def test_encode_fault(self):
        # Ref : http://hessian.caucho.com/doc/hessian-ws.html#anchor16
        r = self.encoder.encode(protocol.Fault(
            code='ServiceException',
            message='File Not Found',
            detail='java.io.FileNotFoundException',
        ))
        self.assertIsInstance(r, tuple)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0], 'fault')
        self.assertEqual(r[1],
                         b'fhS\x00\x04codeS\x00\x10ServiceException'
                         b'S\x00\x07messageS\x00\x0eFile Not Found'
                         b'S\x00\x06detailS\x00\x1djava.io.FileNotFoundException'
                         b'z')

class ProtocolProviderTestCase(TracRpcTestCase):
    def setUp(self):
        TracRpcTestCase.setUp(self)

    def tearDown(self):
        TracRpcTestCase.tearDown(self)

    def test_rpc_info(self):
        # Just try getting the docs for Hessian to test, it should always exist
        hessian = HessianProtocol(self._testenv.get_trac_environment())
        name, docs = hessian.rpc_info()
        self.assertEqual(name, 'hessian')
        self.assertIn('Content-Type: application/x-hessian', docs)


def test_suite():
    suite = TracRpcProtocolTestSuite()
    suite.addTest(makeSuite(ProtocolProviderTestCase))
    suite.addTest(makeSuite(HessianEncoderTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

