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

import copy
import sys
import unittest

from tracrpc.tests import makeSuite, TracRpcTestCase, TracRpcTestSuite

from tracrpcext._amf import AMFProtocol
from ..util import TracRpcProtocolTestSuite
from . import Py3AMFTestCase

from pyamf import amf3
from pyamf.remoting import ErrorFault, RemotingError, \
                           STATUS_OK, STATUS_ERROR

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

  def test_multireq(self):
    # Multiple AMF RPC messages in single HTTP request
    rpc_wiki = self.user.getService('wiki',
                                 auto_execute=False)
    amf_req1 = rpc_wiki.getAllPages()
    amf_req2 = rpc_wiki.getPage('WikiStart', 1)

    rpc_status = self.user.getService('ticket.status',
                                   auto_execute=False)
    amf_req3 = rpc_status.getAll()

    rpc_unk = self.user.getService('nonexisting',
                                auto_execute=False)
    amf_req4 = rpc_unk.method()

    result = self.user.execute()

    self.assertEqual(4, len(result))

    # Assertions for previous call to wiki.getAllPages()
    amf_rsp1 = result[amf_req1.id]
    self.assertEqual(STATUS_OK, amf_rsp1.status)
    self.assertIsInstance(amf_rsp1.body, list)
    self.assertIn('WikiStart', amf_rsp1.body)
    self.assertIn('TitleIndex', amf_rsp1.body)

    # Assertions for previous call to wiki.getPage('WikiStart', 1)
    amf_rsp2 = result[amf_req2.id]
    self.assertEqual(STATUS_OK, amf_rsp2.status)
    self.assertIsInstance(amf_rsp2.body, str)
    self.assertIn('Welcome', amf_rsp2.body)

    # Assertions for previous call to ticket.status.getAll()
    amf_rsp3 = result[amf_req3.id]
    self.assertEqual(STATUS_OK, amf_rsp3.status)
    self.assertEqual(
      ['accepted', 'assigned', 'closed', 'new', 'reopened'],
      amf_rsp3.body
    )

    # Assertions for previous call to nonexisting.method()
    amf_rsp4 = result[amf_req4.id]
    self.assertEqual(STATUS_ERROR, amf_rsp4.status)
    self.assertIsInstance(amf_rsp4.body, ErrorFault)
    self.assertEqual('error', amf_rsp4.body.level)
    self.assertEqual('MethodNotFound', amf_rsp4.body.code)
    self.assertEqual('RPC method "nonexisting.method" not found', amf_rsp4.body.description)
    # TODO: Add server log reference in details
    self.assertIs(None, amf_rsp4.body.details)
    self.assertEqual('', amf_rsp4.body.type)

  def test_large_file(self):
    pagename = 'TestAmf/LargeJsonrpc'
    filename = 'large.dat'
    rpc_wiki = self.admin.getService('wiki')
    rv = rpc_wiki.putPage(
      pagename, 'attachment:' + filename, {}
    )
    self.assertEqual(True, rv)

    content = bytes(bytearray(range(256))) * 4 * 1024 * 4  # 4 MB
    rv = rpc_wiki.putAttachmentEx(
      pagename, filename, 'Large file', amf3.ByteArray(content)
    )
    self.assertEqual(filename, rv)

    rv = rpc_wiki.getAttachment(
      '%s/%s' % (pagename, filename)
    )
    self.assertIsInstance(rv, amf3.ByteArray)
    self.assertEqual(content, rv.getvalue())

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

  def test_resource_not_found(self):
    # A Ticket resource
    try:
      rpc_tckt = self.admin.getService('ticket')
      rpc_tckt.get(2147483647)
    except RemotingError as e:
      self.assertEqual(
        'Ticket 2147483647 does not exist.',
        e.args[0]
      )
    else:
      self.fail('AMF remoting fault not raised')

    # A Wiki resource
    try:
      rpc_wiki = self.admin.getService('wiki')
      rpc_wiki.getPage("Test", 10)
    except RemotingError as e:
      self.assertEqual(
        'Wiki page "Test" does not exist at version 10',
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

