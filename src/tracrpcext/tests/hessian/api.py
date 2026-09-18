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

import sys
import unittest

from tracrpc.tests import makeSuite, TracRpcTestCase

from pyhessian import encoder, protocol

from tracrpcext._hessian import Fault, HessianRpcEncoder, HessianProtocol
from ..util import TracRpcProtocolTestSuite
from . import PyHessianTestCase

# Module name of default Hessian client library
RPC_EXC_MODULE = 'tracrpcext.exc'

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
        self.assertEqual(r[1], b'RI\x00\x00\x00\x05')

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
                         b'FHS\x00\x04codeS\x00\x10ServiceException'
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
        self.assertEqual(name, 'Hessian')
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
    for i, r in enumerate(result[:3]):
        msg = f'Result at index {i}'
        self.assertIsInstance(r, tuple, msg)
        self.assertEqual(1, len(r), msg)
    # FIXME: Implement echo of request id
#    self.assertEqual(1, result[0]['id'])
#    self.assertEqual(2, result[1]['id'])
#    self.assertEqual(3, result[2]['id'])
    self.assertIn('WikiStart', result[0][0])
    self.assertIn('Welcome', result[1][0])
    self.assertEqual(('accepted', 'assigned', 'closed', 'new',
                      'reopened'
                     ), result[2][0])
                     
    self.assertIsInstance(result[3], protocol.Object)
    self.assertEqual(type(result[3]).__module__, RPC_EXC_MODULE)
    self.assertEqual(type(result[3]).__name__, 'NoSuchMethodException')
    self.assertRegex(result[3].message, r'''RPC method "nonexisting" not found

RPC\(Hessian\) reference : \d+:\d+''')

  def test_large_file(self):
    pagename = 'TestHessian/LargeJsonrpc'
    filename = 'large.dat'
    rv = getattr(self.admin, 'wiki.putPage')(
      pagename, 'attachment:' + filename, {}
    )
    self.assertEqual(True, rv)

    content = bytes(bytearray(range(256))) * 4 * 1024 * 4  # 4 MB
    rv = getattr(self.admin, 'wiki.putAttachmentEx')(
      pagename, filename, 'Large file', protocol.Binary(content)
    )
    self.assertEqual(filename, rv)

    rv = getattr(self.admin, 'wiki.getAttachment')(
      '%s/%s' % (pagename, filename)
    )
    self.assertIsInstance(rv, protocol.Binary)
    self.assertEqual(content, rv.value)

  def test_fragment(self):
    tktid = getattr(self.admin, 'ticket.create')(
      'ticket10786', '', {'type': 'enhancement', 'owner': 'A'}
    )
    try:
      result = getattr(self.admin, 'search.performSearch')(
        'ticket10786'
      )
      self.assertEqual(
        '<span class="new">#%d</span>: enhancement: '
          'ticket10786 (new)' % tktid,
        result[0][1]
      )
      self.assertEqual(1, len(result))
    finally:
        getattr(self.admin, 'ticket.delete')(tktid)

  def test_xmlrpc_permission(self):
    # Test returned response if not XML_RPC permission
    self._revoke_perm('anonymous', 'XML_RPC')
    try:
      getattr(self.anon, 'system.listMethods')()
    except protocol.Fault as e:
      self.assertEqual('RequireHeaderException', e.code)
      self.assertIn('XML_RPC', e.message)
      self.assertRegex(e.detail, r'RPC\(Hessian\) reference : \d+:\d+')
    else:
      self.fail('Hessian fault not raised')
    finally:
      self._grant_perm('anonymous', 'XML_RPC')

  def test_method_not_found(self):
    try:
      getattr(self.admin, 'system.doesNotExist')()
    except protocol.Fault as e:
      self.assertFaultMatches(
        e, 'NoSuchMethodException',
        'RPC method "system.doesNotExist" not found',
        r'RPC\(Hessian\) reference : \d+:\d+'
      )
    else:
      self.fail('Hessian fault not raised')

  def test_wrong_argspec(self):
    try:
      getattr(self.admin, 'system.listMethods')("hello")
    except protocol.Fault as e:
      self.assertFaultMatches(
        e, 'ServiceException',
        'listMethods() takes exactly 2 arguments' 
          if sys.version_info[0] == 2 else
        'listMethods() takes 2 positional arguments but 3 were given',
        r'RPC\(Hessian\) reference : \d+:\d+',
      )
    else:
      self.fail('Hessian fault not raised')

  def test_resource_not_found(self):
    # A Ticket resource
    try:
      getattr(self.admin, 'ticket.get')(2147483647)
    except protocol.Fault as e:
      self.assertFaultMatches(
        e, 'NoSuchObjectException',
        'Ticket 2147483647 does not exist.',
        r'RPC\(Hessian\) reference : \d+:\d+',
      )
    else:
      self.fail('Hessian fault not raised')
    # A Wiki resource
    try:
      getattr(self.admin, 'wiki.getPage')(
        "Test", 10
      )
    except protocol.Fault as e:
      self.assertFaultMatches(
        e, 'NoSuchObjectException',
        'Wiki page "Test" does not exist at version 10',
        r'RPC\(Hessian\) reference : \d+:\d+',
      )
    else:
      self.fail('Hessian fault not raised')


def test_suite():
    suite = TracRpcProtocolTestSuite()
    suite.addTest(makeSuite(ProtocolProviderTestCase))
    suite.addTest(makeSuite(HessianEncoderTestCase))
    suite.addTest(makeSuite(PyHessianApiTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

