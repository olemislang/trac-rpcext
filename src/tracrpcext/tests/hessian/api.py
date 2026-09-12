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

from tracrpcext._hessian import Fault, HessianRpcEncoder, HessianProtocol
from ..util import TracRpcProtocolTestSuite
from . import PyHessianTestCase

class HessianEncoderTestCase(unittest.TestCase):
    def setUp(self):
        self.encoder = HessianRpcEncoder()

    def tearDown(self):
        del self.encoder

    def test_encoder_setup(self):
        self.assertIn(Fault, encoder.RETURN_TYPES)
        self.assertIn(protocol.Fault, encoder.RETURN_TYPES)
        self.assertIn(protocol.Reply, encoder.RETURN_TYPES)

    def test_encode_reply_v1(self):
        # Ref : http://hessian.caucho.com/doc/hessian-1.0-spec.xtp#Value
        r = self.encoder._encode(protocol.Reply(5, version=1))
        self.assertIsInstance(r, tuple)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0], 'reply')
        self.assertEqual(r[1], b'r\x01\x00I\x00\x00\x00\x05z')

    def test_encode_reply_v2(self):
        # Ref : http://hessian.caucho.com/doc/hessian-ws.html#anchor15
        r = self.encoder._encode(protocol.Reply(5, version=2))
        self.assertIsInstance(r, tuple)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0], 'reply')
        self.assertEqual(r[1], b'H\x02\x00RI\x00\x00\x00\x05')

    def test_encode_fault_v1(self):
        # Ref : http://hessian.caucho.com/doc/hessian-1.0-spec.xtp#Faults
        for f, msg in (
          (Fault(
            code='ServiceException',
            message='File Not Found',
            detail='java.io.FileNotFoundException',
            version=1,
          ), 'tracrpcext.hessian.Fault version=1'),
          (protocol.Fault(
            code='ServiceException',
            message='File Not Found',
            detail='java.io.FileNotFoundException',
          ), 'python-hessian.Falut'),
        ):
          r = self.encoder._encode(f)
          self.assertIsInstance(r, tuple, msg=msg)
          self.assertEqual(len(r), 2, msg=msg)
          self.assertEqual(r[0], 'fault', msg=msg)
          self.assertEqual(r[1],
                           b'fS\x00\x04codeS\x00\x10ServiceException'
                           b'S\x00\x07messageS\x00\x0eFile Not Found'
                           b'S\x00\x06detailS\x00\x1djava.io.FileNotFoundException'
                           b'z', msg=msg)

    def test_encode_fault_v2(self):
        # Ref : http://hessian.caucho.com/doc/hessian-ws.html#anchor16
        r = self.encoder._encode(Fault(
            code='ServiceException',
            message='File Not Found',
            detail='java.io.FileNotFoundException',
            version=2,
        ))
        self.assertIsInstance(r, tuple)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0], 'fault')
        self.assertEqual(r[1],
                         b'H\x02\x00FHS\x00\x04codeS\x00\x10ServiceException'
                         b'S\x00\x07messageS\x00\x0eFile Not Found'
                         b'S\x00\x06detailS\x00\x1djava.io.FileNotFoundException'
                         b'Z')

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


class PyHessianApiTestCase(PyHessianTestCase):

  def test_multicall(self):
    params = [
      {'methodName': 'wiki.getAllPages', 'params': [], 'id': 1},
      {'methodName': 'wiki.getPage', 'params': ['WikiStart', 1], 'id': 2},
      {'methodName': 'ticket.status.getAll', 'params': [], 'id': 3},
      {'methodName': 'nonexisting', 'params': []}
    ]
    result = getattr(self.user, 'system.multicall')(params)
    self.assertEqual(4, len(result))
    self.assertEqual(1, result[0]['id'])
    self.assertEqual(2, result[1]['id'])
    self.assertEqual(3, result[2]['id'])
    self.assertEqual(None, result[0]['error'])
    self.assertIn('WikiStart', result[0]['result'])
    self.assertIn('Welcome', result[1]['result'])
    self.assertEqual(['accepted', 'assigned', 'closed', 'new',
                                'reopened'], result[2]['result'])
    self.assertEqual(None, result[3]['result'])
    self.assertEqual('JSONRPCError', result[3]['error']['name'])


def test_suite():
    suite = TracRpcProtocolTestSuite()
    suite.addTest(makeSuite(ProtocolProviderTestCase))
    suite.addTest(makeSuite(HessianEncoderTestCase))
    suite.addTest(makeSuite(PyHessianApiTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

