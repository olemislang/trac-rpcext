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

from functools import reduce
import operator
from struct import pack
import sys
from types import GeneratorType

from trac.core import Component, implements, TracError
from trac.perm import PermissionError
from trac.resource import ResourceNotFound
from trac.util.datefmt import to_datetime, utc
from trac.util.html import Fragment
from trac.util.text import to_unicode
from trac.web.api import HTTPBadRequest 

from tracrpc.api import Binary, IRPCProtocol, RPCError, XMLRPCSystem
from tracrpc.util import cleandoc_, gettext, to_b

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

class HessianStream(object):
    def __init__(self, obj, version_major, version_minor=0):
        if version_major < 2:
            raise ValueError('Required protocol version >= 2.0')
        self.value = obj
        self.version = (version_major, version_minor)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                self.version == other.version and \
                self.value == other.value

    def __ne__(self, other):
        return not self.__eq__(other)


class HessianRpcBinary(protocol.Binary):
    def __init__(self, value):
        self.value = value.value \
                         if isinstance(value, protocol.Binary) else \
                     value

    @property
    def data(self):
        return self.value

for t, lbl in (
    (protocol.Reply,   'reply'),
    (protocol.Fault,   'fault'),
    (HessianStream,    'version'),
    (Fault,            'fault'),
    (Fragment,         'string'),
    (Binary,           'binary'),
    (HessianRpcBinary, 'binary'),
    (RPCError,         'fault'),
    (PermissionError,  'fault'),
    (ResourceNotFound, 'fault'),
):
    encoder.RETURN_TYPES[t] = lbl

# FIXME: Match these to Hessian specification
ERROR_CODES = dict([c, c.__name__] for c in [ProtocolException,
                                             NoSuchObjectException,
                                             RequireHeaderException,
                                             ServiceException])
ERROR_CODES.update({
  RPCError: 'ServiceException',
  NoSuchMethodException: 'NoSuchMethodException',
  PermissionError: 'RequireHeaderException',
  ResourceNotFound: 'NoSuchObjectException'
})


@six.add_metaclass(encoder.EncoderBase)
class HessianRpcEncoder(object):

    ERROR_CODES = ERROR_CODES

    def __init__(self, version=None, log=None):
        self._refs = []
        self.version = version
        self.log = log

    @encoder.encoder_for(HessianStream)
    def encode_stream(self, hs):
        # Protocol version >= 2 required by HessianStream.__init__
        encoded = self.encode(hs.value)
        return pack('>cBB', b'H', *stream.version[:2]) + encoded

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

        data_type, encoded_reply_value = self._encode(reply.value)

        if reply.version == 1:
            # FIXME : Any Hessian protocol version wirh minor != 0 ?
            encoded = pack('>cBB', b'r', reply.version, 0)
            encoded += headers
            encoded += encoded_reply_value 
            encoded += b'z'
        else:
            encoded = pack('>c', b'R')
            encoded += headers
            encoded += encoded_reply_value 

        return encoded

    def _encode_fault_v1(self, fault):
        encoded = b''.join(self.encode_keyval((key, getattr(fault, key)))
                           for key in ('code', 'message', 'detail')) 
        return pack('>c', b'f') + encoded + pack('>c', b'z')

    @encoder.encoder_for(protocol.Fault)
    def encode_pyhessian_fault(self, fault):
        # No version context. Default to version=1
        return self._encode_fault_v1(fault)

    @encoder.encoder_for(Fault)
    def encode_fault(self, fault):
        version = fault.version
        if not isinstance(version, int):
            version = version[0]
        if version == 1:
            return self._encode_fault_v1(fault)
        # Protocol version >= 2
        encoded = b''.join(self.encode_keyval((key, getattr(fault, key)))
                           for key in ('code', 'message', 'detail')) 
        return pack('>cc', b'F', b'H') + encoded + b'Z'

    def _encode_mobject(self, objtype, members):
        '''Encode object as a map as described in:

        - v1 : http://hessian.caucho.com/doc/hessian-1.0-spec.xtp#map
        - v2 : http://hessian.caucho.com/doc/hessian-serialization.html##map
        '''
        encoded = b'' if objtype is None else \
                  pack('>cH', b't', len(objtype)) + to_b(objtype) \
                      if self.version == 1 else \
                  self.encode(len(objtype)) + to_b(objtype)
        keyvals = map(self.encode_keyval, members.items())
        encoded += reduce(operator.add, keyvals, b'')
        return pack('>c', b'H' if objtype is None and version > 1 else b'M') + \
               encoded + b'z'

    def _encode_trac_error(self, e):
        # Encode as M object
        ts = util.timestamp_label()
        msg = f'RPC(Hessian) reference : {ts}'
        stack_trace = (e.__class__, e, e.__traceback__)
        if self.log is not None:
            util.logging.rpcerror(self.log, msg, exc_info=stack_trace)
        objtype = 'tracrpcext.exc.' + self.ERROR_CODES.get(e.__class__, 'ServiceException') 
        members = {'message' : f'{e}\n\n{msg}'}
        return self._encode_mobject(objtype, members)

    @encoder.encoder_for(RPCError)
    def encode_rpc_error(self, e):
        return self._encode_trac_error(e)

    @encoder.encoder_for(PermissionError)
    def encode_perm_error(self, e):
        return self._encode_trac_error(e)

    @encoder.encoder_for(ResourceNotFound)
    def encode_noobj_error(self, e):
        return self._encode_trac_error(e)

    @encoder.encoder_for(Fragment)
    def encode_fragment(self, frag):
        return self.encode(str(frag))

    @encoder.encoder_for(Binary)
    def encode_tracrpc_binary(self, obj):
        return self.encode(protocol.Binary(obj.data))

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


class ParserV1(parser.ParserV1):
    def _read_date(self):
        t = super(ParserV1, self)._read_date()
        return to_datetime(t, utc)

    def _read_binary(self, len=None):
        return HessianRpcBinary(
            super(ParserV1, self)._read_binary(len)
        )


class ParserV2(parser.ParserV2):
    def _read_date(self):
        t = super(ParserV1, self)._read_date()
        return to_datetime(t, utc)

    def _read_binary(self, code, len=None):
        return HessianRpcBinary(
            super(ParserV2, self)._read_binary(code, len)
        )


class Parser(parser.Parser):
    def __init__(self):
        self._version_adapters = {
            1: ParserV1,
            2: ParserV2,
        }

    def read_object(self, code=None):
        obj = super(Parser, self).read_object(code)
        # Wrapper for binary values
        if isinstance(obj, protocol.Binary):
            return HessianRpcBinary(obj)
        return obj


# Trac components

__metaclass__ = type

class HessianProtocol(Component):
  _description = cleandoc_(r"""
  [http://hessian.caucho.com/doc/hessian-overview.xtp Hessian] is a 
  dynamically-typed binary RPC protocol. This component adds support for 
  [http://hessian.caucho.com/doc/hessian-1.0-spec.xtp version 1.0] and
  [http://hessian.caucho.com/doc/hessian-ws.html version 2.0]. There are
  [http://hessian.caucho.com/#HessianImplementationsDownload client implementations]
  available for some popular programming languages.

  The following snippet illustrates how to perform authenticated calls 
  using `python-hessian`  library.

  {{{#!python
  >>> from pyhessian.client import HessianProxy
  >>> hsp = HessianProxy(%(url_auth)r)
  >>> getattr(hsp, "system.getAPIVersion")()
  %(version)r
  }}}

  Implementation details:

    * Hessian calls must include `Content-Type: application/x-hessian`
      header.
    * Anonymous calls shall be sent to `/rpc` path
      relative to the Trac instance base URL.
    * Authenticated calls shall be sent to `/login/rpc` path
      relative to the Trac instance base URL.
    * RPC request`"id"` marks are not supported yet.
    * Field `overload` of Hessian calls is ignored.
    * Some client libraries (e.g. `python-hessian` proxy)
      return instances of `tuple` rather than `list`.
    * Multiple RPC methods may be executed at once by
      invoking `system.multicall` endpoint, and in that case
      - outcomes are returned in the same order as requested,
      - the result of a successful method call is returned back
        wrapped in an unary `tuple`,
      - faults are sent back encoded as
        [http://hessian.caucho.com/doc/hessian-serialization.html##map object maps]
        with `type` set to one of
        [http://hessian.caucho.com/doc/hessian-ws.html#anchor16 Hessian fault codes].
        Client libraries are responsible for choosing the concrete class type for
        object instantiation.
  """)
  implements(IRPCProtocol)

  RPC_PROTO = 'Hessian'

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
        call = Parser().parse_string(req.read(clen))
        result = {
          field : getattr(call, field, None)
          for field in ('method', 'headers', 'version')
        }
        result['params'] = call.args
        result['version'] = int(result['version'])
        # Copy before TracRPC since version is needed to send Fault back
        req.rpc = result
        result['method'] = to_unicode(result['method'])
        return result
      except (parser.ParseError, TypeError) as e :
        raise ProtocolException(e)
      except Exception as e:
        # FIXME: Function _decode_surrogate_pair in python-hessian
        # raises instances of built-in Exception class.
        raise ServiceException(e)

  def send_rpc_result(self, req, result):
    self._send_hessian_resp(req, result, True)

  ERROR_CODES = ERROR_CODES

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

  def _encode_reply(self, value, version=1):
    return HessianRpcEncoder(version, self.log).encode(value)

  def _send_hessian_resp(self, req, result, succeeded):
    rpcreq = req.rpc
    # FIXME : Should all headers be echoed back to the caller?
    version = rpcreq.get('version', 1)
    self.log.info(f'RPC({self.RPC_PROTO}) : Version {version} detected')
    if succeeded:
      result = protocol.Reply(result,
                              headers=rpcreq.get('headers'),
                              version=rpcreq.get('version', 1))
    else:
      result = Fault(result['code'],
                     result['message'],
                     result['detail'],
                     version=version)
      if version == 1:
        # Wrap into Reply for Hessian v1
        result = protocol.Reply(result,
                                headers=rpcreq.get('headers'),
                                version=version)

    if version >= 2:
        # FIXME : Any Hessian protocol version wirh minor != 0 ?
        result = HessianStream(
          result, version_major=version, version_minor=0
        )

    reply = self._encode_reply(result, version)
#    self.log.debug("RPC(hessian) Return value : %s", reply)
    req.send(reply, content_type='application/x-hessian')

