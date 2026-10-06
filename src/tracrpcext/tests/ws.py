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
Test suite for Trac web services core.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

from itertools import zip_longest
import unittest

from tracrpc.api import XMLRPCSystem
from tracrpc.tests import makeSuite, TracRpcTestCase

from .util import EnvTestCase, TracRpcProtocolTestSuite
from .. import ws

class WebServiceSystemTestCase(EnvTestCase):

    def setUp(self):
        super(WebServiceSystemTestCase, self).setUp()
        self.ws = ws.WebServiceSystem(self.env)

    def tearDown(self):
        self.env = None
        super(WebServiceSystemTestCase, self).tearDown()

    # Custom assertions

    def assertMethodDescMatch(self, expected, method_desc, msg=None):
        msg = msg or ''
        self.assertIn('params', method_desc, msg)
        self.assertIn('return', method_desc, msg)
        self.assertIn('doc', method_desc, msg)
        # Documentation
        self.assertIsInstance(method_desc['doc'], str,
                              'Docs. ' + msg)
        self.assertNotEqual('', method_desc['doc'])
        # Return type
        self.assertIn('return', method_desc, msg)
        self.assertEqual(expected['return']['type'],
                         method_desc['return']['type'],
                         'Result type. ' + msg)
        # Parameters
        try:
            param_names = ', '.join(
                p['name'] for p in method_desc['params']
            )
        except:
            param_names = ''
        self.assertEqual(
            len(expected['params']),
            len(method_desc['params']),
            f'Number of params ({param_names}).' + msg,
        )
        for expect_pd, pd in zip_longest(expected['params'],
                                         method_desc['params']):
            msg_param = f"Param {expect_pd['name']}.. {msg}"
            self.assertIn('type', pd, msg_param)
            self.assertIn('name', pd, msg_param)
            self.assertIn('def_order', pd, msg_param)
            self.assertIn('optional', pd, msg_param)
            # TODO: Assertions for param docs
            self.assertEqual(expect_pd['name'],
                             pd['name'],
                             'Param name. ' + msg_param)
            self.assertEqual(expect_pd['type'],
                             pd['type'],
                             'Type definition. ' + msg_param)
            self.assertEqual(expect_pd['def_order'],
                             pd['def_order'],
                             'Param order. ' + msg_param)
            self.assertEqual(expect_pd['optional'],
                             pd['optional'],
                             'Optional. ' + msg_param)

    # Test scenarios

    def test_desc_system(self):
        desc = self.ws.generate_service_desc('system')
        self.assertIn('name', desc)
        self.assertIn('methods', desc)
        self.assertIn('types', desc)

        self.assertEqual('system', desc['name'])
        self.assertEqual({'multicall',
                          'listMethods',
                          'methodHelp',
                          'methodSignature',
                          'getAPIVersion',
                         }, set(desc['methods'].keys()))
        # system.multicall
        method_desc = desc['methods']['multicall']
        self.assertMethodDescMatch({
            'params': [{
                'name': 'signatures',
                'def_order': 1,
                'type': (list, 'RpcCall'),
                'optional': False,
            }],
            'return': {
                'type': (list, 'MulticallResult'),
            }
        }, method_desc)
        self.assertIn('MulticallResult', desc['types'],)
        self.assertIn('RpcCall', desc['types'],)

        # system.listMethods
        method_desc = desc['methods']['listMethods']
        self.assertMethodDescMatch({
            'params': [],
            'return': {
                'type': (list, str),
            }
        }, method_desc)


def test_suite():
    suite = TracRpcProtocolTestSuite()
    suite.addTest(makeSuite(WebServiceSystemTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

