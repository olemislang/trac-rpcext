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
Test suite for helper functions.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

import unittest

from tracrpc.api import XMLRPCSystem
from tracrpc.tests import makeSuite, TracRpcTestCase

from .util import TracRpcProtocolTestSuite
from .. import util

# Module name of default Hessian client library
RPC_EXC_MODULE = 'tracrpcext.exc'

class EnvTestCase(TracRpcTestCase):

    def setUp(self):
        self.env = self._testenv.get_trac_environment()

    def tearDown(self):
        self.env = None

    def test_parse_kwargs_noargs(self):
        self.assertEqual([],
                         util.parse_rpc_kwargs(
                             self.env,
                             'system.getAPIVersion',
                             {}
                         ))

    def test_parse_kwargs_exact(self):
        self.assertEqual(['wiki.getPage'],
                         util.parse_rpc_kwargs(
                             self.env,
                             'system.methodHelp',
                             {'method' : 'wiki.getPage'}
                         ))
        self.assertEqual([1034, 'file.txt'],
                         util.parse_rpc_kwargs(
                             self.env,
                             'ticket.getAttachment',
                             {'ticket' : 1034,
                              'filename': 'file.txt'}
                         ))

    def test_parse_kwargs_default(self):
        self.assertEqual([512, 'My comment'],
                         util.parse_rpc_kwargs(
                             self.env,
                             'ticket.update',
                             {'id' : 512,
                              'comment': 'My comment'}
                         ))
        self.assertEqual([512, 'My comment', {'type': 'task'}],
                         util.parse_rpc_kwargs(
                             self.env,
                             'ticket.update',
                             {'id' : 512,
                              'attributes': {'type': 'task'},
                              'comment': 'My comment'}
                         ))
        self.assertEqual([512, 'My comment', {}, False, 'user'],
                         util.parse_rpc_kwargs(
                             self.env,
                             'ticket.update',
                             {'id' : 512,
                              'author': 'user',
                              'comment': 'My comment'}
                         ))

    def test_parse_kwargs_missing(self):
        # Partial match, call missing the last args
        with self.assertRaises(KeyError) as ctx_exc:
            util.parse_rpc_kwargs(self.env,
                                  'ticket.getAttachment',
                                  {'ticket': 1})
        self.assertEqual('filename',
                         ctx_exc.exception.args[0])

        # Partial match, call missing the first args
        with self.assertRaises(KeyError) as ctx_exc:
            util.parse_rpc_kwargs(self.env,
                                  'ticket.getAttachment',
                                  {'filename': 'file.txt'})
        self.assertEqual('ticket',
                         ctx_exc.exception.args[0])

        # Partial match, call missing args at the middle
        with self.assertRaises(KeyError) as ctx_exc:
            util.parse_rpc_kwargs(self.env,
                                  'ticket.putAttachment',
                                  {'ticket': 1,
                                   'filename': 'file.txt',
                                   'data': b''})
        self.assertEqual('description',
                         ctx_exc.exception.args[0])

        # Partial match, call missing args at the middle
        # just before args with default value, actually set
        with self.assertRaises(KeyError) as ctx_exc:
            util.parse_rpc_kwargs(self.env,
                                  'ticket.putAttachment',
                                  {'ticket': 1,
                                   'filename': 'file.txt',
                                   'description': 'Some ticket',
                                   'replace': False,})
        self.assertEqual('data',
                         ctx_exc.exception.args[0])

    def test_parse_kwargs_wrong(self):
        with self.assertRaises(NameError) as ctx_exc:
            util.parse_rpc_kwargs(self.env,
                                  'system.getAPIVersion',
                                  {'some_arg': 'some_value'})
        self.assertEqual('some_arg',
                         ctx_exc.exception.args[0])


def test_suite():
    suite = TracRpcProtocolTestSuite()
    suite.addTest(makeSuite(EnvTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

