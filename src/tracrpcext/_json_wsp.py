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


r"""JSON-WSP support for Trac.

[https://en.wikipedia.org/wiki/JSON-WSP JavaScript Object Notation Web-Service Protocol]
(a.k.a JSON-WSP) is a web-service protocol that uses JSON for service description,
requests and responses. It is inspired from JSON-RPC.

Copyright 2010 Olemis Lang <olemis at gmail.com>
Licensed under the Apache version 2 License
"""
__author__ = 'Olemis Lang'

import json

from trac.core import Component, implements
from trac.util.text import empty, exception_to_unicode, to_unicode
from trac.web.api import RequestDone

from tracrpc.api import IRPCProtocol, Binary, MethodNotFound, ProtocolException
from tracrpc.json_rpc import TracRpcJSONDecoder, TracRpcJSONEncoder
from tracrpc.util import cleandoc_, gettext, izip

from . import exc, util

__all__ = ['JsonWspProtocol']


# TODO : Implement multipart attachments


class JsonWspProtocol(Component):

    _descritpion = cleandoc_(r"""
    [https://en.wikipedia.org/wiki/JSON-WSP JavaScript Object Notation Web-Service Protocol]
    (a.k.a JSON-WSP) is a web-service protocol that uses JSON for service description,
    requests and responses. It is inspired from JSON-RPC.

    Example `POST` request using `curl` with `Content-Type` header
    and body:

    {{{
    user: ~ > cat body.json
    {
      "type": "jsonwsp/request",
      "version": "1.0",
      "methodname": "wiki.getPage",
      "args": {
        "pagename": "WikiStart"
      },
      "mirror": {
        "id": 2
      }
    }
    user: ~ > curl -H "Content-Type: application/json" --data @body.json "(url_anon)s/json-wsp
    {
      "type": "jsonwsp/response",
      "version": "1.0",
      "servicename": "wiki",
      "methodname": "wiki.getPage",
      "result": ""= Welcome to...",
      "reflection": {
        "id": 2
      }
    }
    }}}

    Implementation details:

      * JSON-RPC has no formalized type system, so a class-hint system is used
        for input and output of non-standard types:
        * `{"__jsonclass__": ["datetime", "YYYY-MM-DDTHH:MM:SS"]} => DateTime (UTC)`
        * `{"__jsonclass__": ["binary", "<base64-encoded>"]} => Binary`
      * The optional `cmirror` value can be used to send information from the client
        which will then be reflected by the server and returned unchanged in the
        response object's `reflection` value.
    """)

    implements(IRPCProtocol)

    # IRPCProtocol methods

    RPC_PROTO = 'JSON-WSP'
    RPC_ID = 'json-wsp'

    def rpc_info(self):
        return self.RPC_PROTO, gettext(self._descritpion)

    def rpc_match(self):
        yield 'rpc', 'application/x-json-wsp'
        # Provided for avoiding clashes with JSON-RPC
        yield 'jsonwsp', 'application/json'

    def parse_rpc_request(self, req, content_type):
        """Parse JSON-WSP requests"""
        try:
            data = json_load(req)
        except Exception as e:
            # Abort with exception - no data can be read
            self.log.warning("RPC(json) decode error: %s",
                             exception_to_unicode(e))
            raise ProtocolException(e)

        version = data.get('version').strip()
        if not self._check_version(version):
            raise exc.RPCVersionException(f'Unsupported version {version}',
                                          title='incompatible',
                                          proto_id=self.PROTO_ID)
        
        self.log.info(f"RPC({self.PROTO_ID}) JSON-WSP mirror : %s.",
                      repr(data.get('mirror')))
        try:
            methodname = data['methodname']
        except KeyError as e:
            raise ProtocolException('Missing RPC method name')
        try:
            if '.' not in methodname:
                # Includes only last mile, try finding service name
                service_name = data.get('servicename')
                if service_name is not None:
                    method_name = service_name + '.' + method_name 
            if methodname == 'system.multicall':
                # Prepare for multicall
                self.log.debug(f"RPC({self.PROTO_ID}) Multicall request %s", data)
                params = data.get('args', {})
                nparams = len(params)
                if nparams == 0:
                    raise exc.ContractViolation(
                        'Missing required argument',
                        title='client',
                        proto_id=self.PROTO_ID
                    )
                elif nparams > 1:
                    arg_names = params.keys()
                    argnm = next(arg_names)
                    if argnm == 'signatures':
                        argnm = next(arg_names)
                    raise InvalidArgument(
                        methodname, argnm, title='client',
                        proto_id=self.RPC_ID
                    )
                for signature in params,get('signatures'):
                    signature.setdefault('methodName',
                                         signature.get('methodname', ''))
                    signature.setdefault('params',
                                         signature.get('args', {}))
                data['params'] = [params]
            else:
                try:
                    data['params'] = util.parse_rpc_kwargs(
                        self.env, methodname, params
                    )
                except RuntimeError as e:
                    raise ServiceException(e)
                except KeyError as e:
                    raise exc.ContractViolation(
                        f"{methodname}() missing required positional argument: '{e.args[0]}'",
                        title='client', proto_id=self.RPC_ID,
                    )
                except NameError as e:
                    raise exc.InvalidArgument(
                        methodname, e.args[0], title='client',
                        proto_id=self.RPC_ID
                    )
            data['method'] = data['methodname']
            return data
        except RPCError:
            raise
        except Exception as e:
            raise ServiceError(e)

    def send_rpc_result(self, req, result):
        """Send JSON-RPC response back to the caller."""
        rpcreq = req.rpc
        mirror = rpcreq.get('mirror')
        try:
            if rpcreq.get('method') == 'system.multicall':
                # Custom multicall
                args = (rpcreq.get('params') or [[]])[0]
                mcresults = [self._json_result(
                    sig,
                    value if isinstance(value, Exception) else value[0],
                    sig.get('mirror') or mirror
                ) for sig, value in izip(args, result)]

                response = self._json_result(rpcreq, mcresults, mirror)
            else:
                response = self._json_result(rpcreq, result, mirror)
            self.log.debug(f"RPC({self.RPC_ID}) result: %r", response)
            try:  # JSON encoding
                response = json.dumps(response, cls=TracRpcJSONEncoder)
            except Exception as e:
                self.log.warning(f"RPC({self.RPC_ID}) dumps error: %s",
                                 exception_to_unicode(e))
                e = exc.RPCEncodingException(e,
                                             title='server',
                                             proto_id=self.RPC_ID)
                response = json.dumps(
                   self._json_error(rpcreq, e, mirror=mirror),
                   cls=TracRpcJSONEncoder
                )
        except Exception as e:
            self.log.error(f"RPC({self.RPC_ID}) error%s",
                           exception_to_unicode(e, traceback=True))
            response = json.dumps(
                self._json_error(rpcreq, e, mirror=mirror),
                cls=TracRpcJSONEncoder
            )
        self._send_response(req, response + '\n', rpcreq['mimetype'])

    def send_rpc_error(self, req, e):
        """Send a JSON-RPC fault message back to the caller. """
        rpcreq = req.rpc
        mirror = rpcreq.get('mirror')
        response = json.dumps(self._json_error(rpcreq, e, r_id=r_id),
                              cls=TracRpcJSONEncoder)
        self._send_response(req, response + '\n', rpcreq['mimetype'])

    # Internal methods

    def _check_version(self, version):
        return version == '1.0'

    def _send_response(self, req, response, content_type='application/json'):
        self.log.debug("RPC(json) encoded response: %s", response)
        response = to_unicode(response).encode("utf-8")
        req.send_response(200)
        req.send_header('Content-Type', content_type)
        req.send_header('Content-Length', len(response))
        req.end_headers()
        req.write(response)
        raise RequestDone()

    def _json_result(self, rpcreq, result, mirror=None):
        """ Create JSON-RPC response dictionary. """
        method_name = rpcreq.get('method') or rpcreq.get('methodName')
        if not isinstance(result, Exception):
            svcnm, methnm = (method_name or '.').rsplit('.', 1)
            resp = {'type': 'jsonwsp/response',
                    'version': '1.0',
                    'servicename': svcnm,
                    'methodname': methnm,
                    'result': result}
            if mirror is not None:
                resp['reflection'] = mirror
            return resp
        else:
            return self._json_error(result, r_id=r_id)

    def _json_error(self, rpcreq, exc, mirror=None):
        """ Makes a response dictionary that is an error. """
        e = util.to_rpc_error(exc)
        # Ensure there is a reference to ID in the log
        stack_trace = type(exc), exc, exc.__traceback__
        util.logging.rpcerror(self.log,
                              f'{e.details}|n|n{e.message}',
                              exc_info=stack_trace)
        fault = {'code': getattr(e.title) or 'server',
                 'string': to_unicode(e),
                 'detail': e.details}
        resp = {"type": "jsonwsp/fault",
                "version": "1.0",
                "fault": fault}
        if mirror is not None:
            resp['reflection'] = mirror
        return resp

