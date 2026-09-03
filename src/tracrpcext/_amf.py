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

from io import StringIO
import sys
from traceback import format_exc
from types import GeneratorType

from trac.core import Component, implements, TracError
from trac.perm import PermissionError
from trac.resource import ResourceNotFound
from trac.web.api import HTTPBadRequest, HTTPInternalServerError, \
                          HTTPUnauthorized, RequestDone
from tracrpc.api import IRPCProtocol, XMLRPCSystem, ProtocolException
from tracrpc.util import cleandoc_, gettext

import pyamf as amf
from pyamf import remoting
from pyamf.remoting import gateway

from tracrpcext.exc import *

__all__ = 'AMFProtocol',

__metaclass__ = type

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
  >>> url = '${req.abs_href.login('rpc')}'
  >>> gw = RemotingService(url)
  >>> auth = base64.encodestring('%s:%s' % (username, password))[:-1]
  >>> gw.addHTTPHeader("Authorization", "Basic %s" % auth)
  >>> service = gw.getService('system')
  >>> print service.getAPIVersion()
  [${', '.join(rpc.version.split('.'))}]
  }}}

  Implementation details:

    * Request `"id"` is required, as stated in section 4.1.3 of AMF0 specification,
      and therefore any marker value received with a request is returned with the response.
  """)
  implements(IRPCProtocol)

  # IRPCProtocol methods
  def rpc_info(self):
    r"""Protocol description.
    """
    return 'AMF', gettext(self._description)

  def rpc_match(self):
    r"""URL mapping for this protocol.
    """
    yield 'rpc', 'application/x-amf'
    yield 'amfrpc', 'application/x-amf'

  def parse_rpc_request(self, req, content_type):
    """ Parse AMF RPC requests"""
    self.debug = False
    body = req.read(int(req.get_header('Content-Length')))
    stream = None

    # Decode the request
    try:
      request = remoting.decode(body, strict=False, logger=self.log)
    except (amf.DecodeError, IOError) as exc:
      raise ProtocolException("400 Bad Request\n\nThe request body " \
                              "was unable to be successfully decoded.")
    except Exception as e:
      raise
    else :
      # TODO: What about multicall ?
      # TODO: Hmmm ... Suspicious loop. Review !
      args = []
      for d in request:
        r_id = d[0]
        method = d[1].target
        for c in d[1].body:
          args.append(c)
      args = args or []
      return {'id' : r_id, 'method' : method, 'params' : args, 
              'request' : request}

  def send_rpc_result(self, req, result):
    request = req.rpc['request']
    response = remoting.Envelope(request.amfVersion, request.clientType)

    for name, message in request:
      response[name] = remoting.Response(result)

    try :
      stream = remoting.encode(response, strict=False)
    except:
        self.log.exception("RPC(amf) Impossible to encode response of "
                            "'%s' invoked by '%s'", 
                            req.rpc['method'], req.authname)
        raise

    response = stream.getvalue()
    self.log.debug("RPC(amf) encoded result: %s", stream)
    self._send_response(req, response, remoting.CONTENT_TYPE)
#    raise RequestDone()

  def send_rpc_error(self, req, e):
    if isinstance(e, ProtocolException):
      self.log.exception("RPC(amf) Could not parse request from '%s'", 
                            req.authname)

      # TODO: Confirm whether HTTPBadRequest should be used or not
      errcode, errmsg = HTTPBadRequest.code, e.message
    elif isinstance(e, (ServiceException, RPCError)):
      self.log.exception("RPC(amf) Call to '%s' by '%s' failed", 
                            req.rpc['method'], req.authname)

      # TODO: Confirm whether HTTPBadRequest should be used or not
      errcode = HTTPInternalServerError.code
      errmsg = "Internal error: Method '%s' failed unexpectedly. " \
                          "Consult log for further details."
    elif isinstance(e, PermissionError):
      errcode, errmsg = HTTPUnauthorized.code, unicode(e)
      self.log.warning("RPC(amf) Call to '%s' by '%s' failed: %s", 
                            req.rpc['method'], req.authname, errmsg)
    elif isinstance(e, ResourceNotFound):
      errcode, errmsg = HTTPInternalServerError.code, unicode(e)
      self.log.warning("RPC(amf) Call to '%s' by '%s' failed: %s", 
                            req.rpc['method'], req.authname, errmsg)
    else :
      self.log.exception("RPC(amf) Call to '%s' by '%s' failed", 
                            req.rpc['method'], req.authname)
      errcode, errmsg = HTTPInternalServerError.code, "Unexpected error."
    req.send_error(None, template='', content_type='text/plain',
                    status=errcode, env=None, data=errmsg)

  # Internal methods
  def _send_response(self, req, content, content_type='text/html', status=200):
    req.send_response(status)
    req.send_header('Cache-control', 'must-revalidate')
    req.send_header('Content-Type', content_type)
    req.send_header('Content-Length', len(content))
    req.end_headers()

    if req.method != 'HEAD':
      req.write(content)
    raise RequestDone

