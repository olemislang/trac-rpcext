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


r"""Action Message Format support for Trac.

[http://en.wikipedia.org/wiki/Action_Message_Format AMF] is a binary 
protocol designed by ''Macromedia'', now [http://www.adobe.com Adobe Systems] 
to provide a lightweight, efficient means to serialize, deserialize, and transport 
data between the [http://en.wikipedia.org/wiki/Adobe_Flash_Player Flash Player] 
and the ''Flash Remoting gateway''. This module adds support for 
[http://opensource.adobe.com/wiki/download/attachments/1114283/amf0_spec_121207.pdf AMF 0] 
and [http://opensource.adobe.com/wiki/download/attachments/1114283/amf3_spec_05_05_08.pdf AMF 3].

Copyright 2010 Olemis Lang <olemis at gmail.com>
Licensed under the Apache version 2 License
"""
__author__ = 'Olemis Lang'

from datetime import datetime, timedelta
from io import StringIO
import sys
from traceback import format_exc
from types import GeneratorType

from trac.core import Component, implements, TracError
from trac.perm import PermissionError
from trac.resource import ResourceNotFound
from trac.util.datefmt import to_datetime, utc
from trac.util.html import Fragment
from trac.util.text import to_unicode
from trac.web.api import HTTPBadRequest, HTTPInternalServerError, \
                          HTTPForbidden, HTTPNotFound, HTTP_STATUS, \
                          HTTPUnprocessableContent, RequestDone

from tracrpc.api import Binary, IRPCProtocol, XMLRPCSystem, \
                        ProtocolException
from tracrpc.util import cleandoc_, gettext

import pyamf.amf3
from pyamf import remoting
from pyamf.flex import messaging
from pyamf.remoting import amf0, amf3, gateway

from .exc import *
from tracrpcext import util

__all__ = 'AMFProtocol',

__metaclass__ = type

# AMF encode / decode setup

class TracByteArrayAdapter(pyamf.amf3.ByteArray):
  # Needed so that RPC methods can read binary data
  @property
  def data(self):
    return self.getvalue()

# FIXME : This belongs in pyamf decoder instead
def _fix_param(value):
  if isinstance(value, pyamf.amf3.ByteArray):
    return TracByteArrayAdapter(value.getvalue())
  elif isinstance(value, datetime):
    return to_datetime(value, utc)
  return value

# Encode Binary objects as ByteArray
pyamf.add_type(Binary, lambda obj, encoder: pyamf.amf3.ByteArray(obj.data))

# Encode Fragment objects as string (XML?)
pyamf.add_type(Fragment, lambda obj, encoder: str(obj))

class Amf0ReqProcessor(amf0.RequestProcessor):
  def parse_rpc_ctx(self, amf_msg):
    rpcreq = {'methodName': amf_msg.target,
              'params': [_fix_param(v) for v in amf_msg.body]}
    # TODO: Process DescribeService header
    cred = amf_msg.headers.get('Credentials')
    if cred is not None:
      rpcreq['amf.userid'] = cred['userid']
      rpcreq['amf.secret'] = cred['password']
    return rpcreq

  def build_error_from_ctx(self, rpcreq, error):
    amf_msg = rpcreq['amf.msg']
    if isinstance(error, Exception):
      error = type(error), error, error.__traceback__
    return self.buildErrorResponse(amf_msg, error)

  def build_resp_from_ctx(self, ctx, value):
    return remoting.Response(value)


class Amf3ReqProcessor(amf3.RequestProcessor):
  def parse_rpc_ctx(self, amf_msg):
    ro_request = amf_msg.body[0]
    if not isinstance(ro_request, messaging.RemotingMessage):
      msg_type = type(ro_request).__name__
      raise ValueError('RPC(amf) Unexpected AMF3 request {msg_type}')
    rpcreq = {'methodName': amf3.get_service_name(ro_request),
              'params': [_fix_param(v) for v in ro_request.body]}
    # TODO: User credentials in request
    return rpcreq

  def build_error_from_ctx(self, rpcreq, error=None):
    amf_req = rpcreq['amf.req']
    amf_msg = rpcreq['amf.msg']
    amf_proc = rpcreq['amf.handler']

    if isinstance(error, Exception):
      error = type(error), error, error.__traceback__

    ro_request = amf_msg.body[0]
    fault = amf_proc.buildErrorResponse(ro_request, error)
    body = remoting.Response(fault, status=remoting.STATUS_ERROR)
    ro_response = body.body
    dsid = ro_request.headers.get('DSId', None)
    if not dsid == 'nil':
      dsid = amf3.generate_random_id()
    ro_response.headers.setdefault('DSId', dsid)
    return body

  def build_resp_from_ctx(self, rpcreq, value):
    amf_msg = rpcreq['amf.msg']
    ro_request = amf_msg.body[0]

    ro_response = amf3.generate_acknowledgement(ro_request)
    ro_response.body = value
    return remoting.Response(ro_response)


class TracRpcGateway(gateway.BaseGateway):
  """Trac AMF Remoting gateway.
  """

  def getServiceRequest(self, amf_msg, target):
    return self._request_class(
      amf_msg, None, target
    )


class AMFProtocol(Component):
  _description = cleandoc_(r"""
  [http://en.wikipedia.org/wiki/Action_Message_Format AMF] is a binary 
  protocol designed by ''Macromedia'', now [http://www.adobe.com Adobe Systems],
  to provide a lightweight, efficient means to serialize, deserialize, and transport 
  data between the [http://en.wikipedia.org/wiki/Adobe_Flash_Player Flash Player] 
  and the ''Flash Remoting gateway''. This module adds support for 
  [http://opensource.adobe.com/wiki/download/attachments/1114283/amf0_spec_121207.pdf AMF 0] 
  and [http://opensource.adobe.com/wiki/download/attachments/1114283/amf3_spec_05_05_08.pdf AMF 3].

  The following snippet illustrates how to perform authenticated calls 
  using the [http://www.pyamf.org PyAMF]  library.

  {{{
  >>> import base64
  >>> from pyamf.remoting import RemotingError
  >>> from pyamf.remoting.client import RemotingService
  >>> username, password = '$authname', 'mypassword'
  >>> url = %(url_anon)r
  >>> gw = RemotingService(url)
  >>> auth = base64.encodestring('%%s:%%s' %% (username, password))[:-1]
  >>> gw.addHTTPHeader("Authorization", "Basic %%s" %% auth)
  >>> service = gw.getService('system')
  >>> print service.getAPIVersion()
  %(version)r
  }}}

  Implementation details:

    * AMF calls must include Content-Type: application/x-amf
      header and shall sent to /rpc path relative to the Trac instance base URL.
    * Request `"id"` is required, as stated in section 4.1.3 of AMF0 specification,
      and therefore any marker value received with a request is returned with the response.
  """)
  implements(IRPCProtocol)

  RPC_PROTO = 'Action Message Format'
  RPC_ID    = 'amf'

  # IRPCProtocol methods
  def rpc_info(self):
    r"""Protocol description.
    """
    return self.RPC_PROTO, gettext(self._description)

  def rpc_match(self):
    r"""URL mapping for this protocol.
    """
    yield 'rpc', remoting.CONTENT_TYPE

  def parse_rpc_request(self, req, content_type):
    """ Parse AMF RPC requests"""
    self.log.info(f'RPC({self.RPC_ID}) Call by {req.authname}')
    self.debug = False
    body = req.read(int(req.get_header('Content-Length')))
    stream = None

    # Decode the request
    try:
      # TODO: Configurable strict decoding mode
      request = remoting.decode(
        body, strict=False, logger=self.log,
        # UTC
        timezone_offset=timedelta(hours=0)
      )
    except (pyamf.DecodeError, IOError) as e:
      raise ProtocolException(e)
    except Exception as e:
      raise
    else :
      args = []
      # Prepare for the possibility of inline multicall
      gw = TracRpcGateway()
      sigs = [self._get_call_ctx(msg_id, msg, gw) for msg_id, msg in request]
      nsigs = len(sigs)
      rpcreq = {}
      if nsigs == 0:
        raise ProtocolException('RPC(amf) : Empty request')
      elif nsigs == 1 and sigs[0]['methodName'] == 'system.multicall':
        # Avoid unnecessary nested multicall
        # Override for Trac RPC protocol API
        rpcreq, = sigs
        rpcreq['method'] = rpcreq.pop('methodName', '')
      else:
        # FIXME : Global req ID ?
        rpcreq = {'method': 'system.multicall',
                  'params': [sigs],
                  # Flag to send response messages back wrapped in AMF envelope
                  'multicall.style': 'amf_packet'}
      rpcreq['amf.req'] = request
      return rpcreq

  def send_rpc_result(self, req, result):
    rpcreq = req.rpc
    request = rpcreq['amf.req']
    # Sequences for them pairs of RPC call ID + result
    if rpcreq.get('multicall.style') == 'amf_packet':
      # Envelope wrapping multiple messages
      sigs, = rpcreq['params']
      retvals = ((True, r[0]) # Successful RPC call
                    if isinstance(r, tuple) else
                 (False, r)   # RPC failure exception
                 for r in result)
      amf_msgs = (
        (s['id'],
         self._build_result_msg(s, r)
            if is_ok else
         self._build_error_msg(s, r)
        ) for s, (is_ok, r) in zip(sigs, retvals)
      )
    else:
      # Real multicall
      amf_msgs = [(rpcreq['id'],
                   self._build_result_msg(rpcreq, result)
                   )]

    response = remoting.Envelope(request.amfVersion)
    for req_id, amf_msg in amf_msgs:
      response[req_id] = amf_msg

    self._send_amf_response(req, rpcreq, response)

  def send_rpc_error(self, req, e):
    # All requests are routed as system.multicall
    # hence errors raised from within RPC methods do not get in here.
    rpcreq = req.rpc
    ts = util.timestamp_label()
    stack_trace = sys.exc_info()
    reason = f'Could not parse request from {req.authname}' \
               if isinstance(e, ProtocolException) else \
             f"Call by '{req.authname}' failed: {e}"
    msg = f'RPC({self.RPC_ID}) reference : {ts}'
    util.logging.rpcerror(self.log, f'{msg}\n\n{reason}', exc_info=stack_trace)

    errmsg = f'{reason}\n\n{msg}'
    ncalls = len(rpcreq['params'])
    is_real_multicall = rpcreq.get('multicall.style') != 'amf_packet'
    if not is_real_multicall and ncalls > 1:
      # Exception raised beyond the scope of system.multicall
      # HTTP error must be sent back to cancel the potentially
      # multiple unread AMF RPC messages bundled in request.
      if isinstance(e, ProtocolException):
        # TODO: Confirm whether HTTPBadRequest should be used or not
        errcode = HTTPBadRequest.code
      elif isinstance(e, (ServiceException, RPCError)):
        # TODO: Confirm whether HTTPInternalError should be used or not
        errcode = HTTPInternalServerError.code
      elif isinstance(e, PermissionError):
        errcode = HTTPForbidden.code
      elif isinstance(e, ResourceNotFound):
        errcode = HTTPUnprocessableContent.code
      else :
        errcode = HTTPInternalServerError.code
      # Send HTTP error back to the client
      self._send_response(
        req, errmsg, content_type='text/plain', status=errcode
      )
    else:
      # Single RPC method call
      # Reply back with AMF response
      amf_req = rpcreq['amf.req']
      if is_real_multicall:
        call_ctx = rpcreq
      else:
          (call_ctx,), = rpcreq['params']
      amf_proc = call_ctx['amf.handler']
      msg_id = call_ctx['id']

      response = remoting.Envelope(amf_req.amfVersion)
      msg_resp = amf_proc.build_error_from_ctx(call_ctx, e)
      response[msg_id] = msg_resp

      self._send_amf_response(req, rpcreq, response)

  # Internal methods
  def _get_processor(self, amf_msg, gw):
    '''Choose either AMF0 or AMF3 processor for AMF messaage.
    '''
    if amf_msg.target == 'null' or not amf_msg.target:
      return Amf3ReqProcessor(gw)
    else:
      return Amf0ReqProcessor(gw)

  def _get_call_ctx(self, msg_id, amf_msg, gw):
    amf_proc = self._get_processor(amf_msg, gw)
    rpcreq = amf_proc.parse_rpc_ctx(amf_msg)
    rpcreq.update({
      'id': msg_id,
      'amf.msg': amf_msg,
      'amf.req': amf_msg.envelope,
      'amf.handler': amf_proc,
    })
    return rpcreq

  def _build_result_msg(self, rpcreq, result):
    amf_proc = rpcreq['amf.handler']
    return amf_proc.build_resp_from_ctx(rpcreq, result)

  def _build_error_msg(self, rpcreq, e):
    amf_proc = rpcreq['amf.handler']

    ts = util.timestamp_label()
    stack_trace = type(e), e, e.__traceback__
    reason = f'Call to {rpcreq['methodName']} failed'
    msg = f'RPC({self.RPC_ID}) reference : {ts}'
    util.logging.rpcerror(self.log,
                          f'{msg}\n\n{reason}',
                          exc_info=stack_trace)

    return amf_proc.build_error_from_ctx(rpcreq, e)

  def _send_amf_response(self, req, rpcreq, amf_resp):
    try:
      stream = remoting.encode(
        amf_resp,
        # FIXME: Determine strict value from config option
        strict=False,
        # FIXME: Time zone value ?
      )
    except:
      ts = util.timestamp_label()
      stack_trace = sys.exc_info()
      reason = f'Error encoding AMF response'
      msg = f'RPC({self.RPC_ID}) reference : {ts}'
      util.logging.rpcerror(self.log, f'{msg}\n\n{reason}', exc_info=stack_trace)

      errmsg = f'{reason}\n\n{msg}'
      self._send_response(req, errmsg, 'text/plain', status=500)
    else:
      self._send_response(req, stream.getvalue())

  def _send_response(self, req, content,
                     content_type=remoting.CONTENT_TYPE, charset=None,
                     status=200):
    if content_type == 'text/plain':
      msg_status = HTTP_STATUS.get(status, 'Unexpected protocol error')
      content = f'{status} {msg_status}\n\n{content}'
    is_text = isinstance(content, str)
    ctype_value = content_type
    if is_text:
      charset = charset or 'utf-8'
      ctype_value += '; charset=' + charset
      content = content.encode(charset)

    req.send_response(status)
    req.send_header('Cache-Control', 'must-revalidate')
    req.send_header('Content-Type', ctype_value)
    req.send_header('Content-Length', len(content))
    req.end_headers()

    if req.method != 'HEAD':
      req.write(content)
    raise RequestDone

