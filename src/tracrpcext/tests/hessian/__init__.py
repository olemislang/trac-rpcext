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
Test suite for Trac extension implementing Hessian protocol.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

__all__ = ()

from ..util import TracRpcProtocolTestSuite


def test_suite():
    suite = TracRpcProtocolTestSuite()
    # Hessian test suite
    from . import api, ticket #, wiki, web_ui, search
    for mod in (api, ticket,
#               wiki, web_ui, search
    ):
      suite.addTest(mod.test_suite())
    return suite

