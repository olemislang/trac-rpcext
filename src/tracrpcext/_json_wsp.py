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

from datetime import datetime
import io
import json
import os

try:
    import babel
except ImportError:
    babel = None

from trac.core import Component, implements
from trac.util.datefmt import utc
from trac.util.html import Fragment, Markup
from trac.util.text import empty, exception_to_unicode, to_unicode
from trac.web.api import RequestDone

from tracrpc.api import IRPCProtocol, Binary, MethodNotFound, ProtocolException
from tracrpc.json_rpc import json_load
from tracrpc.util import cleandoc_, gettext, unicode, izip

from . import api, exc, util

__all__ = ['JsonWspProtocol']

# Encoding

class TracJsonWspEncoder(json.JSONEncoder):
    """ Extending the JSON encoder to support some additional types:
    1. datetime.datetime => {"rfc3339", "<str>"}
    2. tracrpc.api.Binary => {"cid:": "<attachment_id>"}
    3. empty => ''
    4. Fragment|Markup => unicode
    5. babel.support.LazyProxy => unicode
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            # http://www.ietf.org/rfc/rfc3339.txt
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=utc)
            elif obj.tzinfo is not utc:
                obj = obj.astimezone(utc)
            value = obj.strftime('%Y-%m-%dT%H:%M:%S')
            if obj.microsecond != 0:
                value += '.%06d' % obj.microsecond
            return {'rfc3339': value}
        if isinstance(obj, Binary):
            # TODO : Implement multipart attachments
            raise NotImplementedError('Binary attachments not supported yet')
        if obj is empty:
            return ''
        if isinstance(obj, (Fragment, Markup)):
            return unicode(obj)
        if babel and isinstance(obj, babel.support.LazyProxy):
            return unicode(obj)
        return super(TracJsonWspEncoder, self).default(obj)


# Trac components

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
    user: ~ > curl -H "Content-Type: application/x-jsonwsp" --data @body.json "(url_auth)s
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

      * Non-standard `ContentType : application/x-jsonwsp` header is used to
        select JSON-WSP for requests sent to /rpc path  to cope with JSON-RPC.
      * For RPC clients not supporting setting custom HTTP headers JSON-WSP
        may be selected for HTTP requests sent to `/rpc/jsonwsp` path with
        `Content-Type: application/json` header set.
      * JSON-WSP has no formalized type system, so a class-hint system is used
        for input and output of non-standard types:
        * `{"__jsonclass__": ["datetime", "YYYY-MM-DDTHH:MM:SS"]} => DateTime (UTC)`
        * `{"__jsonclass__": ["binary", "<base64-encoded>"]} => Binary`
      * Binary data may be attached to multipart HTTP messages.
      * The optional `mirror` value can be used to send information from the client
        which will then be reflected by the server and returned unchanged in the
        response object's `reflection` value.
    """)

    implements(api.IWebServiceProtocol)

    RPC_PROTO = 'JSON-WSP'
    RPC_ID = 'jsonwsp'
    RPC_CONTENT_TYPE = 'application/x-jsonwsp'
    WS_CONTENT_TYPE  = 'application/json'

    # IRPCProtocol methods

    def rpc_info(self):
        return self.RPC_PROTO, gettext(self._descritpion)

    def rpc_match(self):
        yield 'rpc', self.RPC_CONTENT_TYPE

    def parse_rpc_request(self, req, content_type):
        """Parse JSON-WSP requests"""
        try:
            data = json_load(req)
        except Exception as e:
            # Abort with exception - no data can be read
            self.log.warning("RPC(json) decode error: %s",
                             exception_to_unicode(e))
            raise ProtocolException(e)

        version = data.get('version', '1.0').strip()
        if not self._check_version(version):
            raise exc.RPCVersionException(f'Unsupported version {version}',
                                          title='incompatible',
                                          proto_id=self.RPC_ID)

        self.log.info(f"RPC({self.RPC_ID}) JSON-WSP mirror : %s.",
                      repr(data.get('mirror')))
        try:
            methnm = data['methodname']
        except KeyError as e:
            raise ProtocolException('Missing RPC method name')
        try:
            service_name = req.environ.get('tracrpc.service', '')
            method_name = service_name + '.' + methnm 
            params = data.get('args', {})
            if method_name == 'system.multicall':
                # Prepare for multicall
                self.log.debug(f"RPC({self.PROTO_ID}) Multicall request %s", data)
                nparams = len(params)
                if nparams == 0:
                    raise exc.ContractViolation(
                        'Missing required argument "signatures"',
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
                        self.env, method_name, params
                    )
                except RuntimeError as e:
                    raise ServiceException(e)
                except KeyError as e:
                    raise exc.ContractViolation(
                        f"{method_name}() missing required positional argument: '{e.args[0]}'",
                        title='client', proto_id=self.RPC_ID,
                    )
                except NameError as e:
                    raise exc.InvalidArgument(
                        method_name, e.args[0], title='client',
                        proto_id=self.RPC_ID
                    )
            data['method'] = method_name
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
                response = json.dumps(response, cls=TracJsonWspEncoder)
            except Exception as e:
                self.log.warning(f"RPC({self.RPC_ID}) dumps error: %s",
                                 exception_to_unicode(e))
                e = exc.RPCEncodingException(e,
                                             title='server',
                                             proto_id=self.RPC_ID)
                response = json.dumps(
                   self._json_error(rpcreq, e, mirror=mirror),
                   cls=TracJsonWspEncoder
                )
        except Exception as e:
            self.log.error(f"RPC({self.RPC_ID}) error%s",
                           exception_to_unicode(e, traceback=True))
            response = json.dumps(
                self._json_error(rpcreq, e, mirror=mirror),
                cls=TracJsonWspEncoder
            )
        self._send_response(req, response + '\n', rpcreq['mimetype'])

    def send_rpc_error(self, req, e):
        """Send a JSON-RPC fault message back to the caller. """
        rpcreq = req.rpc
        mirror = rpcreq.get('mirror')
        response = json.dumps(self._json_error(rpcreq, e, mirror=mirror),
                              cls=TracJsonWspEncoder)
        self._send_response(req, response + '\n', rpcreq['mimetype'])

    # IWebServiceProtocol methods

    def ws_init(self, mapper, url):
        """Register URI routes and claim JSON-WSP IDL
        """
        self.url = url
        mapper.connect('jsonwsp_call', '/{service}/jsonwsp',
                       controller='jsonwsp', action='call',
                       content_type=self.WS_CONTENT_TYPE,)
        mapper.connect('jsonwsp_desc', '/{service}/jsonwsp/description',
                       controller='jsonwsp', action='describe',
                       idl='jsonwsp',)
        return {'idl': ('jsonwsp',),
                'ctlid': 'jsonwsp',}

    def start_idl_response(self, req, lang_id):
        """Add HTTP headers in JSON-WSP service description response.
        """
        if lang_id == 'jsonwsp':
            req.send_header('Content-Type', f'{self.WS_CONTENT_TYPE} charset=utf-8')

    def encode_ws_idl(self, description, lang_id, writer):
        """Encode service meta-data in JSON-WSP description language.
        """
        service_name = description['name']
        typedefs = {
            typenm: self._jsonwsp_typedef(f'type {typenm}', typedef)
            for typenm, typedef in description['types'].items()
        }

        # Add aliases for primitive types not supported by JSON-WSP.
        typedefs.update({
            '_DateTime' : {'rfc3339': 'string'},
            '_Exception': {'code': 'string',
                           'string': 'string',
                           'detail': 'string',},
        })

        desc_obj = {
            "type": "jsonwsp/description",
            "version": "1.0",
            "servicename": service_name,
            "url": self.env.abs_href(self.url(controller='jsonwsp',
                                              service=service_name,
                                              action='call',
                                              content_type=self.WS_CONTENT_TYPE,)),
            "types": typedefs,
            'methods': {
                methnm: {
                    'doc_lines': sigdef.get('doc', '').splitlines(),
                    'params': {
                        p['name']: self._jsonwsp_paramdef(
                            p, f'arg {methnm}.{p["name"]}'
                        ) for p in sigdef['params']},
                    'ret_info': self._jsonwsp_paramdef(
                        sigdef['return'], f'{methnm} return'
                    ),
                }
                for methnm, sigdef in description['methods'].items()
            },
        }
        try:  # JSON encoding
            response = json.dumps(desc_obj, cls=TracJsonWspEncoder)
            writer.write(response.encode('utf-8'))
        except Exception as e:
            raise exc.RpcEncodingException(e,
                                           title='server',
                                           proto_id=self.RPC_ID)

    # Internal methods

    def _jsonwsp_paramdef(self, paramdef, reason=None):
        if reason is None:
            reason = f'arg {paramdef["name"]}' \
                         if 'name' in paramdef else \
                     'return'
        p = {'type': self._jsonwsp_typedef(reason,
                                           paramdef['type']),
             'doc_lines': (),} # TODO: Param docs ?
        def_order = paramdef.get('def_order')
        if def_order is not None:
            p['def_order'] = def_order
        opt = paramdef.get('optional')
        if opt is not None:
            p['optional'] = opt
        doc = paramdef.get('doc')
        if doc is not None:
            p['doc_lines'] = doc.splitlines()
        return p

    TYPE_NAMES = {str: 'string',
                  bool: 'number', # 0 or 1
                  int: 'integer',
                  float: 'float',
                  object: 'any',
                  datetime: '_DateTime',
                  Binary: 'attachment'}

    def _jsonwsp_multitype(self, typedef):
        # FIXME: Translate types and merge
        return 'any'

    def _jsonwsp_typedef(self, what, typedef):
        if typedef is None:
            raise exc.ServerConfigException(
                f'Missing typedef for {what}',
                title='', proto_id=self.RPC_ID
            )
        if isinstance(typedef, str):
            return typedef
        if isinstance(typedef, type):
            typenm = self.TYPE_NAMES.get(typedef)
            if typenm is not None:
                return typenm
            if typedef == list:
                # FIXME: Figure out how to describe list of anything
                return ["string"]
            if typedef == dict:
                # FIXME: Figure out how to describe dict of anything
                return {}
            if typedef is Exception:
                return '_Exception'
            raise exc.ServerConfigException(
                f'Unsupported type {typedef.__name__}',
                title='', proto_id=self.RPC_ID
            )
        if isinstance(typedef, set):
            # Option type
            return self._jsonwsp_multitype(typedef)
        gtype, base_type = typedef
        if gtype == list:
            return [self._jsonwsp_typedef(what, base_type)]
        if gtype == dict:
            return {member: self._jsonwsp_typedef(what, field_type)
                    for member, field_type in base_type.items()}
        if gtype == tuple:
            return {member: self._jsonwsp_typedef(what, field_type)
                    for member, field_type in base_type}
        raise exc.ServerConfigException(
            f'Unexpected type {typedef} for {what}',
            title='', proto_id=self.RPC_ID
        )

    def _check_version(self, version):
        # FIXME: Multiple versions ?
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

    def _json_error(self, rpcreq, e, mirror=None):
        """ Makes a response dictionary that is an error. """
        _e = exc.to_rpc_error(e)
        # Ensure there is a reference to ID in the log
        stack_trace = type(e), e, e.__traceback__
        util.logging.rpcerror(self.log,
                              f'{_e.details}|n|n{_e.message}',
                              exc_info=stack_trace)
        fault = {'code': _e.title or 'server',
                 'string': to_unicode(_e),
                  "filename": '_json_wsp.py',
                 'lineno': 0,
                 'detail': _e.details}
        resp = {"type": "jsonwsp/fault",
                "version": "1.0",
                "fault": fault,}
        if mirror is not None:
            resp['reflection'] = mirror
        return resp

