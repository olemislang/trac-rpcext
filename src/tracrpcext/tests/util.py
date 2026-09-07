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
Reusable code for testing purposes.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

import os
import unittest

from tracrpc import tests


class TracRpcProtocolTestSuite(unittest.TestSuite):

    ENABLED_PLUGINS = ('tracrpc.*', 'tracrpcext.*')

    def run(self, result):
        if tests._rpc_testenv:
            created = False
        else:
            tests._new_testenv()
            # Enable plugins
            self._enable_plugins(self.ENABLED_PLUGINS)

            # Overwrite URL since protocols are available at /rpc
            # This change is backwards compatible since XML-RPC is still
            # selected for content type application/xml
            tests._rpc_testenv.url_user = '%s/login/rpc' % \
                                          tests._rpc_testenv.url.replace(
                                              '://',
                                              '://user:user@')
            tests._rpc_testenv.url_admin = '%s/login/rpc' % \
                                           tests._rpc_testenv.url.replace(
                                               '://',
                                               '://admin:admin@')
            created = True
        try:
            return super(TracRpcProtocolTestSuite, self).run(result)
        finally:
            if created:
                tests._del_testenv()

    # Internal methods
    def _enable_plugins(self, module_names):
        '''Modify inherit.ini to enable plaugins in test environment.
        '''
        inherit = os.path.join(tests._rpc_testenv._testdir, 'inherit.ini')

        def new_ini_lines(f):
            for l in f:
                if l.strip() != '[components]':
                    # Echo all lines before [components]
                    yield l
                else:
                    yield l
                    for modnm in module_names:
                        yield f'{modnm} = enabled\n'
                    break
            # Ignore all lines in [components] section
            for l in f:
                if l.strip().startswith('['):
                    yield l
                    break
            # Keep everythin after [components]
            for l in f:
                yield l


        with open(inherit, 'r') as f:
            new_config = list(new_ini_lines(f))
        with open(inherit, 'w') as f:
            for l in new_config:
                f.write(l)

