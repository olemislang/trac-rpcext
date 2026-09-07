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
from trac.web.api import HTTPBadRequest 

from tracrpc.api import IRPCProtocol, XMLRPCSystem
from tracrpc.util import cleandoc_, gettext

from pyhessian import encoder, parser, protocol
import six

from tracrpcext.exc import *
from tracrpcext import util

__all__ = 'HessianProtocol',

# Register Hessian types for serialization
# FIXME : Remove once https://github.com/olemislang/python-hessian PR is merged in

class Fault(protocol.Fault):
    '''Hessian Fault aware of protocol version.

    Needed for serialization.
    '''
    def __init__(self, code, message, detail, version=None):
        super(Fault, self).__init__(code, message, detail)
        self.version = version

for t, lbl in (
    (protocol.Reply, 'reply'),
    (protocol.Fault, 'fault'),
    (Fault,          'fault'),
):
    encoder.RETURN_TYPES[t] = lbl


@six.add_metaclass(encoder.EncoderBase)
class HessianRpcEncoder(object):
    @encoder.encoder_for(protocol.Reply)
    def encode_reply(self, reply):
        if reply.version > 1 and isinstance(reply.value, (protocol.Fault, Fault)):
            raise TypeError(f'Reply value may not be Fault in version {reply.version}')

        headers = b''

        for header, value in reply.headers.items():
            if not isinstance(header, str):
                raise TypeError("Reply header keys must be strings")

            headers += pack('>cH', b'H', len(header)) + header
            headers += self.encode(value)

        data_type, encoded_reply_value = self.encode(reply.value)

        if reply.version == 1:
            encoded = pack('>cBB', b'r', reply.version, 0)
            encoded += headers
            encoded += encoded_reply_value 
            encoded += b'z'
        else:
            encoded = pack('>cBBc', b'H', reply.version, 0, b'R')
            encoded += headers
            encoded += encoded_reply_value 
            encoded += b'Z'

        return 'reply', encoded

    def _encode_fault_v1(self, fault):
        encoded = b''.join(self.encode_keyval((key, getattr(fault, key)))
                           for key in ('code', 'message', 'detail')) 
        return pack('>c', b'f') + encoded + b'z'

    @encoder.encoder_for(protocol.Fault)
    def encode_pyhessian_fault(self, fault):
        # No version context. Default to version=1
        return ('fault', self._encode_fault_v1(fault))

    @encoder.encoder_for(Fault)
    def encode_fault(self, fault):
        if fault.version == 1:
            return ('fault', self._encode_fault_v1(fault))
        # Protocol version >= 2
        encoded = b''.join(self.encode_keyval((key, getattr(fault, key)))
                           for key in ('code', 'message', 'detail')) 
        return ('fault',
            pack('>cBBcc', b'H', fault.version, 0, b'F', b'H') + encoded + b'Z'
        )

    # Copy all methods in encoder.Encoder
    _encode = encoder.Encoder.__dict__['_encode']
    add_ref = encoder.Encoder.__dict__['add_ref']
    encode = encoder.Encoder.__dict__['encode']
    encode_arg = encoder.Encoder.__dict__['encode_arg']
    encode_null = encoder.Encoder.__dict__['encode_null']
    encode_boolean = encoder.Encoder.__dict__['encode_boolean']
    encode_int = encoder.Encoder.__dict__['encode_int']
    encode_long = encoder.Encoder.__dict__['encode_long']
    encode_double = encoder.Encoder.__dict__['encode_double']
    encode_date = encoder.Encoder.__dict__['encode_date']
    high_codepoints_re = encoder.Encoder.__dict__['high_codepoints_re']
    _unicode_encode = encoder.Encoder.__dict__['_unicode_encode']
    _encode_to_surrogate_pair = encoder.Encoder.__dict__['_encode_to_surrogate_pair']
    encode_unicode = encoder.Encoder.__dict__['encode_unicode']
    if 'encode_string' in encoder.Encoder.__dict__:
        encode_string = encoder.Encoder.__dict__['encode_string']
    encode_list = encoder.Encoder.__dict__['encode_list']
    encode_tuple = encoder.Encoder.__dict__['encode_tuple']
    encode_keyval = encoder.Encoder.__dict__['encode_keyval']
    encode_map = encoder.Encoder.__dict__['encode_map']
    encode_mobject = encoder.Encoder.__dict__['encode_mobject']
    encode_remote = encoder.Encoder.__dict__['encode_remote']
    encode_binary = encoder.Encoder.__dict__['encode_binary']
    encode_call = encoder.Encoder.__dict__['encode_call']


# Trac components

__metaclass__ = type

class HessianProtocol(Component):
  _description = cleandoc_(r"""
  [http://hessian.caucho.com/doc/hessian-overview.xtp Hessian] is a 
  dynamically-typed binary RPC protocol. This component adds support for 
  [http://hessian.caucho.com/doc/hessian-1.0-spec.xtp version 1.0] and
  [http://hessian.caucho.com/doc/hessian-ws.html version 2.0]. There are
  [client implementations](http://hessian.caucho.com/#HessianImplementationsDownload)
  available for some popular programming languages.

  The following snippet illustrates how to perform authenticated calls 
  using `python-hessian`  library.

  {{{
  >>> from pyhessian.client import HessianProxy
  >>> hsp = HessianProxy('${req.abs_href.login('hessian')}', {'username' : '$authname', \
                                                'password' : 'your_password'})
  >>> getattr(hsp, "system.getAPIVersion")()
  [${', '.join(rpc.version.split('.'))}]
  }}}

  Implementation details:

    * Hessian calls must include Content-Type: application/x-hessian
      header and shall sent to /rpc path relative to the Trac instance base URL.
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
      clen = int(req.get_header('Content-Length'))
    except:
      raise HTTPBadRequest('Invalid value ' + 
                           repr(req.get_header('Content-Length')) +
                           ' for Content-Length header') 
    else:
      try:
        call = parser.Parser().parse_string(req.read(clen))
        return {
          field : getattr(call, field, None)
          for field in ('method', 'headers', 'params', 'version')
        }
      # FIXME: Function _decode_surrogate_pair in python-hessian
      # raises instances of built-in Exception class.
      except parser.ParseError as e :
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
    result = {'detail' : msg, 
              'code': self.ERROR_CODES.get(e.__class__, 'ServiceException'), 
              'message' : str(e)}
    # FIXME: Should all fields be sent back to the caller?
    # result.update(e.__dict__)             
    self._send_hessian_resp(req, result, False)

  # Internal methods

  def _encode_reply(self, value):
    return HessianRpcEncoder().encode(value)[1]

  def _send_hessian_resp(self, req, result, succeeded):
    rpcreq = req.rpc
    # FIXME : Should all headers be echoed back to the caller?
    if succeeded:
      result = protocol.Reply(result,
                              headers=rpcreq.get('headers'),
                              version=rpcreq.get('version'))
    else:
      version = rpcreq.get('version')
      result = Fault(result['code'],
                     result['message'],
                     result['detail'],
                     version=version)
      if version == 1:
        # Wrap into Reply for Hessian v1
        result = protocol.Reply(result,
                                headers=rpcreq.get('headers'),
                                version=version)

    reply = self._encode_reply(result)
#    self.log.debug("RPC(hessian) Return value : %s", reply)
    req.send(reply, content_type='application/x-hessian')

