#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright 2010 Olemis Lang <olemis at gmail.com>
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


r"""RPC protocols for Trac.

This project implements RPC protocols not provided by
TracXMLRPC plugin. This could be due to conflicting
dependencies, policies, or maybe other reasons. In the former
case this plugin MIGHT NOT install by default all the
dependencies needed by every protocol implementation. In that
case it will check whether dependencies are available or not
and will display informative messages if it is not possible
to process client requests.

Copyright 2010 Olemis Lang <olemis at gmail.com>
Licensed under the Apache version 2 License
"""
__author__ = 'Olemis Lang'

import sys

try:
    # Ignore errors to avoid Internal Server Errors
    from trac.core import TracError
    if sys.version[0] > 2:
        unicode = str
    TracError.__str__ = lambda self: unicode(self).encode('ascii', 'ignore')

    from _amf import *
    from _hessian import *
    msg = 'Ok'
except Exception as exc:
#    raise
    msg = "Exception %s raised: '%s'" % (exc.__class__.__name__, str(exc))

