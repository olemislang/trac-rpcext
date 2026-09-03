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


r"""Exception classes used to describe generic RPC protocol errors.

Copyright 2010 Olemis Lang <olemis at gmail.com>
Licensed under the Apache version 2 License
"""
__author__ = 'Olemis Lang'

from tracrpc.api import RPCError, MethodNotFound as NoSuchMethodException, \
                        ProtocolException, ServiceException

__metaclass__ = type

class NoSuchObjectException(RPCError):
  r"""The requested object (namespace) does not exist. """

class RequireHeaderException(RPCError):
  r"""A required header was not understood by the server"""

