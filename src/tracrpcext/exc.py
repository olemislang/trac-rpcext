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

from datetime import datetime

from trac.core import TracError
from trac.perm import PermissionError
from trac.resource import ResourceNotFound

from tracrpc import api

from . import util

__metaclass__ = type


#------------------------------
# Exception class hierarchy
#------------------------------

class RpcBaseException(api._CompositeRpcError):
  """Base exception type for RPC protocol errors"""

  def __init__(self, message, title=None, proto_id=None):
    super(RPCBaseException, super).__init__(
      message, title or '', show_traceback=False
    )
    self.ts = util.timestamp_label()
    self.proto_id = proto_id

  @property
  def details(self):
    return f"RPC({self.proto_id} reference {self.ts}"


class RpcClientError(RpcBaseException):
  """The clients request could not be consumed by the server
  due to incorrect format or missing required arguments etc.
  """


class NoSuchObjectException(RpcClientError):
  r"""The requested object (namespace) does not exist. """


class NoSuchMethodException(RpcClientError):
  r"""The requested method does not exist."""


class RequireHeaderException(RpcClientError):
  r"""A required header was not understood by the server"""


class RPCVersionException(RpcClientError):
  r"""Client protocol version is incompatible with server protocol version.

  Typically one will encounter this type of fault if there is a version
  major in difference between the client and the server.
  """


class ContractViolation(RpcClientError):
  r"""Client request does not match service interface contract.
  """


class InvalidArgument(ContractViolation):
  r"""RPC includes invalid argument.
  """
  def __init__(self, method, argname, title=None, proto_id=None):
    super(InvalidArgument, self).__init__(
      f"{method}() got an unexpected argument '{argname}'",
      title, proto_id
    )
    self._method = method
    self._argname = argname 


class ProtocolException(RpcClientError):
    r"""The RPC request has some sort of syntactic error."""


class RpcServerError(RpcBaseException):
  r"""An error occurred on the server side after the client
  request has been successfully consumed."""


class ServiceException(RpcServerError):
  r"""The called method threw an exception."""


class RpcRuntimeError(RpcServerError):
  r"""The RPC infrastructure failed in handling the request."""


class RpcEncodingException(RpcRuntimeError):
  r"""Server was unable to encode RPC result""" 


#------------------------------
# Tools and helpers
#------------------------------

def to_rpc_error(e):
  """Return an instance of RpcBaserException based on exception object."""
  if isinstance(e, RpcBaseException):
    return e
  if isinstance(e, api.MethodNotFound):
    # FIXME : Choose title from type => str mapping
    return NoSuchMethodException(
      e, title='client', show_traceback=False
    )
  if isinstance(e, api.ResourceNotFound):
    return NoSuchObjectException(
      e, title='client', show_traceback=False
    )
  if isinstance(e, api.ProtocolException):
    # Replace
    return ProtocolException(
      e._exc if e._exc is not None else e.message,
      title=e.title,
      show_traceback=e.show_traceback
    )
  if isinstance(e, api.ServiceException):
    # Replace
    return ServiceException(
      e._exc if e._exc is not None else e.message,
      title=e.title,
      show_traceback=e.show_traceback
    )
  if isinstance(e, PermissionError):
    # Wrap and keep inner exception fields
    return RequireHeaderException(
      e, title=e.title, show_traceback=e.show_traceback
    )
  if isinstance(e, TracError):
    # Wrap and keep inner exception fields
    return RpcServerError(
      e, title=e.title, show_traceback=e.show_traceback
    )
  return RpcServerError(e, title='server',
                        show_traceback=False)
                       

