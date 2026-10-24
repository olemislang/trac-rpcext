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

from jsonwspclient.jsonwspexceptions import JsonWspFault

class JsonWspProviderTestCase(TracRpcTestCase):
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
  jsonwsp_services = ('system', 'ticket', 'wiki',)

  def test_api_version(self):
    ws_sys = self.anon.service('system')
    resp = ws_sys.getAPIVersion()
    self.assertEqual(list(api.api_version), resp.result)

  def test_multicall(self):
    params = [
      {'methodName': 'wiki.getAllPages', 'params': [], 'id': 1},
      {'methodName': 'wiki.getPage', 'params': ['WikiStart', 1], 'id': 2},
      {'methodName': 'ticket.status.getAll', 'params': [], 'id': 3},
      {'methodName': 'nonexisting', 'params': []}
    ]
    ws_sys = self.user.service('system')
    result = ws_sys.multicall(signatures=params)
    self.assertFalse(result.has_fault)
    result = result.result
    self.assertEqual(4, len(result))
    for i, r in enumerate(result[:3]):
        msg = f'Result at index {i}'
        self.assertIn('error', r, msg)
        self.assertIsNone(r['error'], msg)
        self.assertIn('result', r, msg)
        self.assertIn('id', r, msg)
    self.assertEqual(1, result[0]['id'])
    self.assertEqual(2, result[1]['id'])
    self.assertEqual(3, result[2]['id'])
    self.assertIn('WikiStart', result[0]['result'])
    self.assertIn('Welcome', result[1]['result'])
    self.assertEqual(['accepted', 'assigned', 'closed', 'new',
                      'reopened'
                    ], result[2]['result'])
    self.assertIsInstance(result[3], dict)
    self.assertIn('error', result[3])
    error = result[3]['error']
    self.assertIsInstance(error, dict)
    self.assertEqual('NoSuchMethodException', error['name'])
    self.assertIn('RPC method "nonexisting" not found',
                  error['message'])
    self.assertRegex(error['detail'], r'RPC\(jsonwsp\) reference : \d+:\d+')

  def test_large_file(self):
    pagename = 'TestAmf/LargeJsonrpc'
    filename = 'large.dat'
    ws_wiki = self.admin.service('wiki')
    rv = ws_wiki.putPage(
      pagename, 'attachment:' + filename, {}
    )
    self.assertEqual(True, rv)

    content = bytes(bytearray(range(256))) * 4 * 1024 * 4  # 4 MB
    rv = ws_wiki.putAttachmentEx(
      pagename, filename, 'Large file', content
    )
    self.assertEqual(filename, rv)

    rv = ws_wiki.getAttachment(
      '%s/%s' % (pagename, filename)
    )
    self.assertIsInstance(rv, bytes)
    self.assertEqual(content, rv)

  def test_xmlrpc_permission(self):
    # Test returned response if not XML_RPC permission
    self._revoke_perm('anonymous', 'XML_RPC')
    try:
      ws_sys = self.anon.service('system')
      methods = ws_sys.listMethods()
    except JsonWspFault as e:
      self.assertIn('XML_RPC', str(e))
    else:
      self.fail(f'Exception not raised. Returned {methods}')
    finally:
      self._grant_perm('anonymous', 'XML_RPC')

  def test_method_not_found(self):
    try:
      ws_sys = self.admin.service('system')
      ws_sys.doesNotExist()
    except KeyError as e:
      self.assertEqual(
        'doesNotExist',
        e.args[0]
      )
    else:
      self.fail('JSON-WSP fault not raised')

  def test_wrong_argspec(self):
    try:
      ws_sys = self.admin.service('system').listMethods(wrong_arg="hello")
    except JsonWspFault as e:
      self.assertEqual('client', e.args[0])
      self.assertIn(
        "ystem.listMethods() got an unexpected argument 'wrong_arg'",
        e.args[1]
      )
    else:
      self.fail('JSON-WSP fault not raised')

  def test_resource_not_found(self):
    # A Ticket resource
    try:
      ws_tckt = self.admin.service('ticket')
      ws_tckt.get(id=2147483647)
    except JsonWspFault as e:
      self.assertEqual('client', e.args[0])
      self.assertIn(
        'Ticket 2147483647 does not exist.',
        e.args[1]
      )
    else:
      self.fail('JSON-WSP fault not raised')

    # A Wiki resource
    try:
      ws_wiki = self.admin.service('wiki')
      ws_wiki.getPage(pagename="Test", version=10)
    except JsonWspFault as e:
      self.assertEqual('client', e.args[0])
      self.assertIn(
        'Wiki page "Test" does not exist at version 10',
        e.args[1]
      )
    else:
      self.fail('JSON-WSP fault not raised')


def test_suite():
    suite = TracRpcProtocolTestSuite()
    suite.addTest(makeSuite(JsonWspProviderTestCase))
    suite.addTest(makeSuite(JsonWspApiTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

