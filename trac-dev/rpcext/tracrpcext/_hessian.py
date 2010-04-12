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
from tracrpcext.util import RPCRequest

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
  """
  implements(IRPCProtocol)
  
  def rpc_info(self):
    r"""Protocol description.
    """
    return 'Hessian', prepare_docs(self.__doc__, indent=2)
  
  def rpc_match(self):
    r"""URL mapping for this protocol.
    """
    # yield 'rpc', 'application/octet-stream'
    yield 'hessian', 'application/octet-stream'
  
  def rpc_process(self, req, content_type):
    r"""Process incoming Hessian RPC request and finalize response.
    """
    try :
      self.log.debug("RPC(hessian) call by '%s'", req.authname)
      rpcreq = self.parse_rpc_request(req)
      method_name, args = rpcreq.method, rpcreq.args
      self.log.debug("RPC(hessian) call by '%s' %s", req.authname, method_name)
      try :
        result = (XMLRPCSystem(self.env).get_method(method_name)(req, args))[0]
        if isinstance(result, GeneratorType):
            result = list(result)
      except (RPCError, PermissionError, ResourceNotFound), e:
        raise
      except Exception:
        e, tb = sys.exc_info()[-2:]
        raise ServiceException(e), None, tb
      else :
        self.send_rpc_result(req, rpcreq, result)
    except (RPCError, PermissionError, ResourceNotFound), e:
      self.send_rpc_error(req, rpcreq, e)
    except Exception, e :
      self.log.exception("RPC(hessian) Error parsing request")
      self.send_unknown_error(req, rpcreq, e)
        
  def parse_rpc_request(self, req):
    try :
      hctx = ParseContext(req)
      method, headers, params = Call().read(hctx, hctx.read(1))
    except HessianError, e :
      raise ProtocolException(str(e))
    else :
      rpcreq = RPCRequest(method, params)
      rpcreq.headers = headers
      return rpcreq
      
  def _send_hessian_resp(self, req, rpcreq, result, succeeded):
    try:
      sio = StringIO()
      Reply().write(WriteContext(sio), (rpcreq.headers, succeeded, result))
      reply = sio.getvalue()
    except Exception, e:
      self.log.exception("RPC(hessian) Error sending response")
      self.send_unknown_error(req, rpcreq, e)
    else :
      self.log.debug("RPC(hessian) Return value : %s", reply)
      req.send(reply, content_type='application/octet-stream')
      
  def send_rpc_result(self, req, rpcreq, result):
    self._send_hessian_resp(req, rpcreq, result, True)
  
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
  
  def send_rpc_error(self, req, rpcreq, e):
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
    self._send_hessian_resp(req, rpcreq, result, False)
  
  def send_unknown_error(self, req, rpcreq, e):
    stackTrace = format_exc()
    body = "Can not send response for '%s'\n\n%s" % (rpcreq.method, stackTrace)
    req.send_error(None, template='', content_type='text/plain',
                        env=None, data=body)
