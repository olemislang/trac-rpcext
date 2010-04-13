#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright 2009-2011 Olemis Lang <olemis at gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


r"""Hessian RPC support for Trac.

[http://hessian.caucho.com/doc/hessian-overview.xtp Hessian] is a 
dinamically-typed binary RPC protocol. This module adds support for 
[http://hessian.caucho.com/doc/hessian-1.0-spec.xtp version 1.0].

Copyright 2009-2011 Olemis Lang <olemis at gmail.com>
Licensed under the GPL License
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

__metaclass__ = type

class TracHessian(Component):
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
  [1, 1, 0]
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

