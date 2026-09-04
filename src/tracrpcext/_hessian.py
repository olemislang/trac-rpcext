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

from struct import pack
import sys
from types import GeneratorType

from trac.core import Component, implements, TracError
from trac.perm import PermissionError
from trac.resource import ResourceNotFound

from tracrpc.api import IRPCProtocol, XMLRPCSystem
from tracrpc.util import cleandoc_, gettext

#from hessian.hessian import ParseContext, Call, HessianError, Reply, \
#                            WriteContext

from pyhessian import encoder, parser, protocol

from tracrpcext.exc import *
from tracrpcext import util

__all__ = 'HessianProtocol',

__metaclass__ = type

# Register Hessian types for serialization
# FIXME : Remove once https://github.com/olemislang/python-hessian PR is merged in

for t, lbl in ((protocol.Reply, 'reply'),
               (protocol.Fault, 'fault')):
  encoder.RETURN_TYPES[t] = lbl

class HessianRpcEncoder(encoder.Encoder):
    @encoder.encoder_for(protocol.Reply)
    def encode_reply(self, reply):
       headers = b''
       args = b''

       for header, value in reply.headers.items():
         if not isinstance(header, str):
           raise TypeError("Reply header keys must be strings")

         headers += pack('>cH', b'H', len(header)) + header
         headers += self.encode(value)

       data_type, encoded_reply_value = self.encode(reply.value)

       encoded = pack('>cBB', 'r', reply.version, 0)
       encoded += headers
       encoded += encoded_reply_value 
       encoded += b'z'

       return encoded

    @encoder.encoder_for(protocol.Fault)
    def encode_fault(self, fault):
       encoded = b''.join(self.encode_keyval(key, getattr(fault, key))
                          for key in ('code', 'message', 'detail')) 
       return pack('>c', b'f') + encoded + b'z'

  # Trac components

class HessianProtocol(Component):
  _description = cleandoc_(r"""
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

  Implementation details:

    * `"id"` is optional, and any marker value received with a
      request is returned with the response.
    * Fields overload and version of Hessian calls are ignored.
  """)
  implements(IRPCProtocol)

  RPC_PROTO = 'hessian'

  # IRPCProtocol methods
  def rpc_info(self):
    r"""Protocol description.
    """
    return self.RPC_PROTO, gettext(self._description)

  def rpc_match(self):
    r"""URL mapping for this protocol.
    """
    yield 'rpc', 'application/x-hessian'

  def parse_rpc_request(self, req, content_type):
    """ Parse Hessian RPC requests"""
    try :
      call = parser.Parser().parse_string(
        req.read(req.get_header('Content-Length'))
      )
      return {
        field : getattr(call, field, None)
        for field in ('method', 'headers', 'params', 'version')
      }
    except HessianError as e :
      raise ProtocolException(e)

  def send_rpc_result(self, req, result):
    self._send_hessian_resp(req, result, True)

  # FIXME: Match these to Hessian specification
  ERROR_CODES = dict([c, c.__name__] for c in [ProtocolException,
                                                NoSuchObjectException,
                                                NoSuchMethodException,
                                                RequireHeaderException,
                                                ServiceException])
  ERROR_CODES.update({
                      RPCError: 'ProtocolException',
                      PermissionError: 'RequireHeaderException',
                      ResourceNotFound: 'NoSuchObjectException'
                      })

  def send_rpc_error(self, req, e):
    r"""Send an Hessian fault message back to the caller. Exception type 
    and message are used for this purpose.
    """
    # TODO: Review HessianPy failure reply
    ts = util.timestamp_label()
    stack_trace = sys.exc_info()
    msg = f'RPC({self.RPC_PROTO}) reference : {ts}'
    util.logging.rpcerror(self.log, msg, exc_info=stack_trace)
    result = {'details' : msg, 
              'code': self.ERROR_CODES.get(e.__class__, 'ServiceException'), 
              'message' : str(e)}
    # FIXME: Should all fields be sent back to the caller?
    # result.update(e.__dict__)             
    self._send_hessian_resp(req, result, False)

  # Internal methods

  def _encode_reply(self, value):
    return HessianRpcEncoder().encode_reply(
      protocol.Reply(value)
    )[1]

  def _send_hessian_resp(self, req, result, succeeded):
    rpcreq = req.rpc
    # FIXME : Should all headers be echoed back to the caller?
    if not succeeded:
       result = Fault(result['code'],
                      result['message'],
                      result['detail'])
    reply = self._encode_reply(
      Reply(result,
            headers=rpcreq.get('headers'),
            version=rpcreq.get('version'))
    )
#    self.log.debug("RPC(hessian) Return value : %s", reply)
    req.send(reply, content_type='application/x-hessian')

