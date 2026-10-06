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


r"""Web services API for Trac.

Copyright 2010 Olemis Lang <olemis at gmail.com>
Licensed under the Apache version 2 License
"""
__author__ = 'Olemis Lang'

from io import BytesIO
from shutil import copyfileobj

from trac.api import IEnvironmentSetupParticipant
from trac.core import Component, ExtensionPoint, implements
from trac.web.api import IRequestHandler, RequestDone

from tracrpc.web_ui import RPCWeb

from . import api, ws

from routes import Mapper


class WebServicesModule(Component):
    implements(IEnvironmentSetupParticipant, IRequestHandler)

    ws_protocols = ExtensionPoint(api.IWebServiceProtocol)

    def __init__(self):
        self.mapper = Mapper()
        self.idl_map = {}
        self.controllers = {'sys': self,}
        # Repeat match for login prefix
        self.mapper.connect('login', r'/login/{path_info:.*}',
                            controller='sys', action='match')

    # IEnvironmentSetupParticipant methods

    def environment_created(self):
        pass

    def environment_needs_upgrade(self):
        # Connect them protocol routes
        with self.mapper.submapper(path_prefix='/ws') as ws_mapper:
            for p in self.ws_protocols:
                ws_caps = p.ws_init(ws_mapper, self.mapper.generate)
                self.controllers[ws_caps['ctlid']] = p
                for lang_id in ws_caps.get('idl', ()):
                    if lang_id in self.idl_map:
                        cls1 = self.__class__.__name__
                        cls2 = self.idl_map[lang_id].__class__.__name__
                        self.log.warning(
                            f'WS : {cls1} claimed IDL {lang_id} owned by {cls2}'
                        )
                        continue
                    self.idl_map[lang_id] = self 
        self.mapper.create_regs()
        self.log.info('RPC: Web services routes ' + self.mapper._master_reg)
        return False

    def upgrade_environment(self):
        pass

    # IRequestHandler methods

    def match_request(self, req):
        """Look for matching web service URI route
        """
        r = self._match_route(req)
        if r is None:
            return False
        req.args['ws.route'] = r
        return True

    def process_request(self, req):
        r = req.args['ws.route']
        ctlid, action, service_name = (
            r.get(k) for k in ('controller', 'action', 'service')
        )
        protocol = self.controllers.get(ctlid)
        try:
            proto_id = None
            if protocol is not None:
                try:
                    # Try getting short protocol ID
                    proto_id = protocol.RPC_ID
                except AttributeError:
                    # Fall back to protocol name
                    proto_id, _ = protocol.rpc_info()
            rpc_label = f'RPC({proto_id})' if proto_id is not None else 'RPC'
            if None in (protocol, action, service_name):
                raise exc.ServerConfigException(
                    f'{rpc_label} Unable to determine ' + ', '.join(
                        k for k,v in (('protocol', protocol),
                                      ('action', action),
                                      ('service name', service_name),)
                          if v is None
                    ), title='', proto_id=proto_id
                )
            if action == 'call':
                newreq = self._rewrite_ws_call(req)
                RPCWeb(self.env).process_request(newreq)
            elif action == 'describe':
                lang_id = r.get('idl')
                if lang_id is None:
                    raise exc.ServerConfigException(
                        f'{rpc_label} No interface description language',
                        title='', proto_id=proto_id
                    )
                wsys = ws.WebServiceSystem(self.env)
                desc = wsys.generate_service_desc(service_name)
                with BytesIO() as stream:
                    protocol.encode_ws_idl(desc, lang_id, stream)
                    # Determine content length
                    clen = stream.seek(0, 2)
                    # Rewind back to the beginning
                    stream.seek(0)
                    self._send_description(req, protocol, lang_id,
                                           stream, clen)
            else:
                raise exc.ServerConfigException(
                    f'{rpc_label} Unexpected action {action}',
                    title='', proto_id=proto_id
                )
        except RequestDone:
            raise
        except:
            # TODO: Handle errors
            raise

    # Internal methods

    def _match_route(self, req):
        """Match URI route while path_info is set. Merge results along the way.
        """
        r = self.mapper.match(req.path_info)
        if r is None:
            # No match
            return None
        acc = {}
        while [r.get(k)
               for k in ('controller', 'action')] == ('sys', 'match'):
            # Accumulate variable values
            acc.update({k: v for k.v in r.iteritems()
                             if k not in ('controller', 'action',
                                          'path_info',)
                       })
            r = self.mapper.match('/' + r['path_info'])
        r.update(acc)
        return r

    def _rewrite_ws_call(self, req):
        """Rewrite parsed web service invocation request for RPC system.
        """
        # TODO: Implement
        raise NotImplementedError('_reerite_ws_call')

    def _send_description(self, req, protocol, lang_id, stream, clen):
        req.send_response(200)
        protocol.start_idl_response(req, lang_id)
        req.send_header('Content-Length', clen)
        req.end_headers()
        copyfileobj(stream, req)
        # TODO: FLush request write buffers ?
        raise RequestDone()

        

