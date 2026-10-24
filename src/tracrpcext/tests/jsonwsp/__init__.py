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
Test suite for Trac extension implementing JSON-WSP protocol.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

__all__ = ()

import logging

from tracrpc.tests import TracRpcTestCase 

from ..util import TracRpcProtocolTestSuite

from jsonwspclient import JsonWspClient
from jsonwspclient.jsonwspservice import JsonWspService


# Patches for JSON-WSP client

class TestJsonWspService(JsonWspService):
    def _load_description(self):
        """Loads description for this service."""
        # NOTE: Relative path
        response = self._post(
            '{}/jsonwsp/description'.format(self.name), method='GET')
        response.raise_for_status()
        self._description = response.response_dict
        self._method_names = list(self._description['methods'])
        self._types = list(self._description['types'])
        # NOTE: Service description contains URL. Generate default otherwise.
        self.url = self._description.get('url') or '%s/jsonwsp' % self.name
        for method_name, method in self._description['methods'].items():
            params = list(method['params'])
            self._set_new_method(method_name, params)
        self._description_loaded = True
        self._trigger('service.description_loaded', service=self)


class TestJsonWspClient(JsonWspClient):
    def _load_service(self, service):
        """Load service."""
        srv = TestJsonWspService(self, service)
        self._services[service.lower()] = srv
        for method_name, method in list(srv.list_methods().items()):
            if not method_name in self._methods:
                self._methods[method_name] = method

# Test scenarios

class JsonWspTestCase(TracRpcTestCase):
  '''Base class for test cases powered by jsonwspclient library.
  '''
  jsonwsp_services = ()

  def setUp(self):
    TracRpcTestCase.setUp(self)

    # Silence jsonwspclient logging
    log = logging.getLogger('jsonwspclient')
    log.setLevel(logging.FATAL)

    kwargs = {'services': self.jsonwsp_services,
              'raise_for_fault': True,}
    self.anon = TestJsonWspClient(
        self._testenv.url_anon.rsplit('/', 1)[0] + '/ws/',
        **kwargs
    )
    self.user = TestJsonWspClient(
        self._testenv.url_user.rsplit('/', 1)[0] + '/ws/',
        **kwargs
    )
    self.admin = TestJsonWspClient(
        self._testenv.url_admin.rsplit('/', 1)[0] + '/ws/',
        **kwargs
    )

  def assertFaultMatches(self, e, expected_code, expected_msg,
                         expected_detail, msg=None):
    self.assertEqual(expected_code, e.code, msg=msg)
    self.assertIn(expected_msg, e.string, msg=msg)
    self.assertRegex(expected_detail, e.detail, msg=msg)

  def tearDown(self):
    self.anon.close()
    self.user.close()
    self.admin.close()
    self.anon = self.user = self.admin = None
    TracRpcTestCase.tearDown(self)


def test_suite():
    suite = TracRpcProtocolTestSuite()
    # JSON-WSP test suite
    from . import api #, ticket, search, wiki
    for mod in (api, #ticket, search, wiki
                ):
      suite.addTest(mod.test_suite())
    return suite

