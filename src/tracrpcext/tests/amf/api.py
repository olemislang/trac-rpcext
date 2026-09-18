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

import sys
import unittest

from tracrpc.tests import makeSuite, TracRpcTestCase, TracRpcTestSuite

from tracrpcext._amf import AMFProtocol
from ..util import TracRpcProtocolTestSuite
from . import Py3AMFTestCase

from pyamf.remoting import RemotingError

class ProtocolProviderTestCase(TracRpcTestCase):
    def setUp(self):
        TracRpcTestCase.setUp(self)

    def tearDown(self):
        TracRpcTestCase.tearDown(self)

    def test_rpc_info(self):
        # Just try getting the docs for AMF to test, it should always exist
        amf = AMFProtocol(self._testenv.get_trac_environment())
        name, docs = amf.rpc_info()
        self.assertEqual(name, 'Action Message Format')
        self.assertIn('Content-Type: application/x-amf', docs)


class Py3AMFApiTestCase(Py3AMFTestCase):

  def test_multicall(self):
    params = [
      {'methodName': 'wiki.getAllPages', 'params': [], 'id': 1},
      {'methodName': 'wiki.getPage', 'params': ['WikiStart', 1], 'id': 2},
      {'methodName': 'ticket.status.getAll', 'params': [], 'id': 3},
      {'methodName': 'nonexisting', 'params': []}
    ]
    rpc_sys = self.user.getService('system')
    result = rpc_sys.multicall(params)
    self.assertEqual(4, len(result))
    for i, r in enumerate(result[:3]):
        msg = f'Result at index {i}'
        self.assertIsInstance(r, list, msg)
        self.assertEqual(1, len(r), msg)
    # FIXME: Implement echo of request id
#    self.assertEqual(1, result[0]['id'])
#    self.assertEqual(2, result[1]['id'])
#    self.assertEqual(3, result[2]['id'])
    self.assertIn('WikiStart', result[0][0])
    self.assertIn('Welcome', result[1][0])
    self.assertEqual(['accepted', 'assigned', 'closed', 'new',
                      'reopened'
                    ], result[2][0])
    self.assertIsInstance(result[3], dict)
    self.assertEqual('Trac Error', result[3]['title'])
    self.assertEqual('MethodNotFound', result[3]['name'])
    self.assertRegex('RPC method "nonexisting" not found',
                     result[3].message)

  def test_large_file(self):
    pagename = 'SandBox/LargeJsonrpc'
    filename = 'large.dat'
    rpc_wiki = self.admin.getService('wiki')
    rv = rpc_wiki.putPage(
      pagename, 'attachment:' + filename, {}
    )
    self.assertEqual(True, rv)

    content = bytes(bytearray(range(256))) * 4 * 1024 * 4  # 4 MB
    rv = rpc_wiki.putAttachmentEx(
      pagename, filename, 'Large file', content
    )
    self.assertEqual(filename, rv)

    rv = rpc_wiki.getAttachment(
      '%s/%s' % (pagename, filename)
    )
    self.assertIsInstance(rv, type(None))
    self.assertEqual(content, rv.value)

  def test_xmlrpc_permission(self):
    # Test returned response if not XML_RPC permission
    self._revoke_perm('anonymous', 'XML_RPC')
    try:
      rpc_sys = self.anon.getService('system')
      rpc_sys.listMethods()
    except RemotingError as e:
      self.assertIn('XML_RPC', str(e))
    else:
      self.fail('AMF fault not raised')
    finally:
      self._grant_perm('anonymous', 'XML_RPC')

  def test_method_not_found(self):
    try:
      rpc_sys = self.admin.getService('system')
      rpc_sys.doesNotExist()
    except RemotingError as e:
      self.assertEqual(
        'RPC method "system.doesNotExist" not found',
        e.args[0]
      )
    else:
      self.fail('AMF remoting fault not raised')

  def test_wrong_argspec(self):
    try:
      rpc_sys = self.admin.getService('system').listMethods("hello")
    except TypeError as e:
      self.assertIn(
        'listMethods() takes exactly 2 arguments' 
          if sys.version_info[0] == 2 else
        'listMethods() takes 2 positional arguments but 3 were given',
        e.args[0]
      )
    else:
      self.fail('AMF remoting fault not raised')


def test_suite():
    suite = TracRpcProtocolTestSuite()
    suite.addTest(makeSuite(ProtocolProviderTestCase))
    suite.addTest(makeSuite(Py3AMFApiTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

