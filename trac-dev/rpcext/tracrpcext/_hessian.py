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


r"""Hessian RPC support for Trac.

[http://hessian.caucho.com/doc/hessian-overview.xtp Hessian] is a 
dinamically-typed binary RPC protocol. This module adds support for 
[http://hessian.caucho.com/doc/hessian-1.0-spec.xtp version 1.0].

Copyright 2010 Olemis Lang <olemis at gmail.com>
Licensed under the Apache version 2 License
"""
__author__ = 'Olemis Lang'

from trac.core import Component, implements, TracError
from trac.perm import PermissionError
from trac.resource import ResourceNotFound

from tracrpc.api import IRPCProtocol, XMLRPCSystem
from tracrpc.util import StringIO, prepare_docs

from tracrpcext.exc import *

from hessian.hessian import ParseContext, Call, HessianError, Reply, \
                            WriteContext
import sys
from traceback import format_exc
from types import GeneratorType

__all__ = 'HessianProtocol',

__metaclass__ = type

class HessianProtocol(Component):
  r"""
  [http://hessian.caucho.com/doc/hessian-overview.xtp Hessian] is a 
  dynamically-typed binary RPC protocol. This component adds support for 
  [http://hessian.caucho.com/doc/hessian-1.0-spec.xtp version 1.0].
  
  The following snippet illustrates how to perform authenticated calls 
  using `HessianPy`  library.
  
  {{{
  >>> from hessian.client import HessianProxy as HSP
  >>> hsp = HSP('${req.abs_href.login('hessian')}', {'username' : '$authname', \
                                                'password' : 'your_password'})
  >>> getattr(hsp, 'system.getAPIVersion')()
  [${', '.join(rpc.version.split('.'))}]
  }}}
  """
  implements(IRPCProtocol)
  
  # IRPCProtocol methods
  def rpc_info(self):
    r"""Protocol description.
    """
    return 'Hessian', prepare_docs(self.__doc__, indent=2)
  
  def rpc_match(self):
    r"""URL mapping for this protocol.
    """
    # yield 'rpc', 'application/octet-stream'
    yield 'hessian', 'application/octet-stream'
  
  def parse_rpc_request(self, req, content_type):
    """ Parse Hessian RPC requests"""
    try :
      hctx = ParseContext(req)
      return dict(zip(['method', 'headers', 'params'], \
                        Call().read(hctx, hctx.read(1))))
    except HessianError, e :
      raise ProtocolException(e)
      
  def send_rpc_result(self, req, result):
    self._send_hessian_resp(req, result, True)
  
  ERROR_CODES = dict([c, c.__name__] for c in [ProtocolException,
                                                NoSuchObjectException,
                                                RequireHeaderException,
                                                ServiceException])
  ERROR_CODES.update({
                      NoSuchMethodException: 'NoSuchMethodException', 
                      RPCError: 'ProtocolException',
                      PermissionError: 'RequireHeaderException',
                      ResourceNotFound: 'NoSuchObjectException'
                      })
  
  def send_rpc_error(self, req, e):
    r"""Send an Hessian fault message back to the caller. Exception type 
    and message are used for this purpose.
    """
    # TODO: Review HessianPy failure reply
    stackTrace = format_exc()
    result = {'details' : stackTrace, 
              'code': self.ERROR_CODES.get(e.__class__, 'ProtocolError'), 
              'message' : str(e)}
    # FIXME: Should all fields be sent back to the caller?
    # result.update(e.__dict__)             
    self._send_hessian_resp(req, result, False)
  
  # Internal methods
  def _send_hessian_resp(self, req, result, succeeded):
    rpcreq = req.rpc
    sio = StringIO()
    Reply().write(WriteContext(sio), (rpcreq['headers'], succeeded, result))
    reply = sio.getvalue()
#    self.log.debug("RPC(hessian) Return value : %s", reply)
    req.send(reply, content_type='application/octet-stream')

