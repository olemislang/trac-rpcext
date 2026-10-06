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

[https://www.w3.org/TR/ws-gloss/#webservice Web services] are considered to be
a software system designed to support interoperable machine-to-machine interaction
over a network. They has an interface described in a machine-processable format
(e.g. WSDL, ...). Other systems interact with the web service in a manner
prescribed by its description using messages (e.g. SOAP, ...), typically conveyed
using a transport layer (e.g. HTTP, ...) with a serialization format (e.g. SOAP)
possibly in conjunction with other Web-related standards.

Trac web services differ from RPC in that:

  - Web services are identified by the URI RPC namespace methods
    are exported at,
  - Web services rely on interface description languages to expose
    full details of endpoints, URIs, signatures, types, and maybe
    other sophisticated aspects of service contract.

Trac web services are similar to RPC since:

  - both rely on serialization formats,
  - both expect messages transmitted through application (e.g. HTTP)
    or transport layer (e.g. TCP) protocols

Copyright 2010 Olemis Lang <olemis at gmail.com>
Licensed under the Apache version 2 License
"""
__author__ = 'Olemis Lang'

import inspect
from datetime import datetime
from itertools import chain, zip_longest

from trac.core import Component, ExtensionPoint, implements

from tracrpc.api import Binary, IXMLRPCHandler, XMLRPCSystem
from tracrpc.ticket import TicketRPC

from . import api, exc

__all__ = ['WebServiceSystem']


class WebServiceSystem(Component):
    """Core of the web services system."""
    implements(api.IWebServiceDescriptor)

    descriptors = ExtensionPoint(api.IWebServiceDescriptor)

    # IWebServiceDescriptor methods
    def namespaces_described(self):
        # Describe namespaces defined by XmlRpcPlugin components.
        yield 'system'
        yield 'search'
        yield 'ticket'
        yield 'ticket.component'
        yield 'ticket.milestone'
        yield 'ticket.priority'
        yield 'ticket.resolution'
        yield 'ticket.severity'
        yield 'ticket.status'
        yield 'ticket.type'
        yield 'ticket.version'
        yield 'wiki'
        # Describe protocols namespace
        yield 'protocols'

    typedefs = {
        'SearchResult': (
            tuple, (('href',   str),
                    ('title',  str),
                    ('date',   datetime),
                    ('author',  str),
                    ('excerpt', str))
        ),
        'MulticallResult': {
            Exception,
            (tuple, ('result', object))
        },
        'RpcCall': (
            dict,
            {'methodName': str,
             'params': (list, object),
             'id': int,}
        ),
        'TicketInputField': (
            tuple,
            (('name', str),
             ('value', str),
             ('options', (list, object)))
        ),
        'TicketAction': (
            tuple,
            (('action', str),
             ('label', str),
             ('hints', str),
             ('input_fields', (list, 'TicketInputField')))
        ),
        'Ticket': (
            tuple, (('id', int),
                    ('time_created', datetime),
                    ('time_changed', datetime),
                    ('attributes',   'TicketAttrs'))
        ),
        'TicketChange': (
            tuple, (('time', datetime),
                    ('author', str),
                    ('field', str),
                    ('oldvalue', object),
                    ('newvalue', object),
                    ('permanent', bool))
        ),
        'TicketField': (
            dict, {'name': str,
                   'type': str,
                   'label': str,
                   'format': str,
                   'value': str,
                   'options': (list, str),
                   'optional': bool,
                   }
        ),
        'Attachment': (
            tuple, (('filename', str),
                    ('description', str),
                    ('size', int),
                    ('time', datetime),
                    ('author', str))
        ),
        'TicketComponent': (
            dict, {k: str
                   for k in ('name',
                             'owner',
                             'description',)}
        ),
        'TicketMilestone': (
            dict, {'name': str,
                   'due': int,
                   'completed': int,
                   'description': str,}
        ),
        'TicketVersion': (
            dict, {'name': str,
                   'time': int,
                   'description': str,}
        ),
        'WikiPageInfo': (
            dict, {'name': str,
                   'lastModified': datetime,
                   'author': str,
                   'version': int,
                   'comment': str,}
        ),
        'WikiPageAttrs': (
                dict, {'readonly': bool,
                       'author': str,}
        ),
    }

    def get_data_contracts(self, typenames):
        return {typenm: self._get_typedef(typenm)
                for typenm in typenames}

    sigdefs = {
        'search.getSearchFilters': (
            # Return value
            (list, str),
            # Args
        ),
        'search.performSearch': (
            # Return value
            (list, 'SearchResult'),
            # Args
            None,
            (list, str),
        ),
        'system.multicall': (
            # Return type
            (list, 'MulticallResult'),
            # Args
            (list, 'RpcCall'),
        ),
        'system.listMethods': (
            # Return type
            (list, str),
            # Args
        ),
        'system.methodSignature': (
            # Return type
            (list, (list, str)),
            # Args
            None,
        ),
        'system.getAPIVersion': (
            # Return value
            (list, int),
            # Args
        ),
        'ticket.query': (
            # Return value
            (list, int),
            # Args
            None,
        ),
        'ticket.getRecentChanges': (
            # Return value
            (list, int),
            # Args
            None,
        ),
        'ticket.getActions': (
            # Return value
            (list, 'TicketAction'),
            # Args
            None,
        ),
        'ticket.get': (
            # Return value
            'Ticket',
            # Args
            None,
        ),
        'ticket.create': (
            # Return value
            None,
            # Args
            None, None,
            'TicketAttrs',
            None, None,
        ),
        'ticket.update': (
            # Return type
            'Ticket',
            # Args
            None, None,
            (dict, {'action': 'TicketAction', # FIXME: Add ticket attributes
                    '_ts': datetime}),
        ),
        'ticket.changeLog': (
            # Return type
            (list, 'TicketChange'),
            # Args
            None, None,
        ),
        'ticket.listAttachments' : (
            # Return type
            (list, 'Attachment'),
            # Args
            None,
        ),
        'ticket.getTicketFields': (
            # Return value
            (list, str),
            # Args
        ),
        'ticket.component.getAll': (
            # Return value
            (list, str),
            # Args
        ),
        'iticket.component.get': (
            # Return value
            'TicketComponent',
            # Args
            None,
        ),
        'ticket.component.create': (
            # Return value
            None,
            # Args
            None,
            'TicketComponent',
        ),
        'ticket.component.update': (
            # Return value
            None,
            # Args
            None,
            'TicketComponent',
        ),
        'ticket.milestone.getAll': (
            # Return value
            (list, str),
            # Args
        ),
        'ticket.milestone.get': (
            # Return value
            'TicketMilestone',
            # Args
            None,
        ),
        'ticket.milestone.create': (
            # Return value
            None,
            # Args
            None,
            'TicketMilestone',
        ),
        'ticket.milestone.update': (
            # Return value
            None,
            # Args
            None,
            'TicketMilestone',
        ),
        'ticket.version.getAll': (
            # Return value
            (list, str),
            # Args
        ),
        'iticket.version.get': (
            # Return value
            'TicketVersion',
            # Args
            None,
        ),
        'ticket.version.create': (
            # Return value
            None,
            # Args
            None,
            'TicketVersion',
        ),
        'ticket.version.update': (
            # Return value
            None,
            # Args
            None,
            'TicketVersion',
        ),
        'wiki.getRecentChanges': (
            # Return value
            (list, 'WikiPageInfo'),
            # Args
            None
        ),
        'wiki.getAllPages': (
            # Return value
            (list, str),
            # Args
        ),
        'wiki.getPageInfo': (
            # Return value
            'WikiPageInfo',
            # Args
            None, None,
        ),
        'wiki.getPageInfoVersion': (
            # Return value
            'WikiPageInfo',
            # Args
            None, None,
        ),
        'listAttachments': (
            # Return value
            (list, str),
            # Args
            None,
        ),
        '': (
            # Return value
            # Args
        ),
        '': (
            # Return value
            # Args
        ),
        '': (
            # Return value
            # Args
        ),
    }

    def detail_signatures(self, ns):
        ns_sigs = {x: self.sigdefs[x]
                   for x in self.sigdefs
                   if x.startswith(ns) and '.' not in x[len(ns)+1:]}
        # FIXME : Return only typedefs needed by RPC namespace
        ns_typenms = chain(self.typedefs.keys(), ('TicketAttrs',))
        return {'sigdefs': ns_sigs,
                'type_names': tuple(ns_typenms),}

    def generate_service_desc(self, service_name):
        # Enumerate service
        rpc_sys = XMLRPCSystem(self.env)
        for provider in rpc_sys.method_handlers:
            # Web service name matches RPC namespace ID
            if service_name == provider.xmlrpc_namespace():
                # Lookup service descriptor
                ws_hints = {}
                for wsd in self.descriptors:
                    if service_name in wsd.namespaces_described():
                        # Found \o/ !
                        ws_hints = wsd.detail_signatures(service_name)
                        ws_hints['typedefs'] = wsd.get_data_contracts(
                            ws_hints.get('type_names')
                        )
                        break
                ws_desc = {'name': service_name,
                           'types': ws_hints.get('typedefs'),
                           'methods': {
                               c.__name__ : self._describe_method(
                                   provider, sigs, c,
                                   ws_hints['sigdefs'].get(
                                       service_name + '.' + c.__name__,
                                   )
                               ) for _, sigs, c in provider.xmlrpc_methods()}
                          }
                return ws_desc
        else:
            raise exc.NoSuchObjectException(f'Unknown service {service_name}')

    # Internal methods

    ticket_field_types = {'test': str,
                          'textarea': str,
                          'select': str,
                          'radio': str,
                          'time': datetime,}

    def _ticket_field_type(self, f):
        return self.ticket_field_types.get(f['type'], str)

    def _get_typedef(self, typenm):
        if typenm == 'TicketAttrs':
            # Ticket attributes, including custom ticket fields
            rpc_ticket = TicketRPC(self.env)
            fields = rpc_ticket.getTicketFields(None)
            types_for_rpc = {f['name'] : self._ticket_field_type(f)
                             for f in fields}
            types_for_rpc['_ts'] = int
            return (dict, types_for_rpc)
        else:
            return self.typedefs[typenm]

    def _describe_method(self, provider, sigs, c, method_hints):
        """Generate method description.

        provider:       Component declaring RPC method;
        sigs:           Method signatures;
        c:              Callable object encapsulating service logic.
        method_hints:   Type hints
        """
        long_sig = small_sig = ()
        # FIXME: Any signature with more than 99999 params ?
        small_len = 99999
        long_len = 0
        for s in sigs:
            l = len(s)
            if l >= long_len:
                long_len, long_sig = l, s
            elif l <= small_len:
                small_len, small_sig = l, s

        def _describe_param(sigtype, param_hint, param=None,
                            i=None, opt=None):
            primitive = (int, str, datetime, Binary)
            param_type = None
            if sigtype in primitive:
                param_type = sigtype
            elif param_hint is None:
                # No hints for complex type
                param_type = (sigtype, None)
            elif isinstance(param_hint, str):
                # Custom typedef
                param_type = param_hint
            else:
                # Generics and struct
                gtype, base_type = param_hint
                if (sigtype, gtype) not in {
                    (dict, dict),
                    (list, list),
                    (list, tuple),
                }:
                    nm = '' if param is None else param.name
                    raise exc.ServerConfigException(
                        f'Type mismatch for {nm} RPC {sigtype} WS {gtype}',
                        title='',
                    )
                param_type = param_hint
            param_desc = {'type': param_type,
                          'doc': None,}
                          
            if param is not None:
                param_desc['name'] = param.name
            if i is not None:
                param_desc['def_order'] = i
            if opt is not None: 
                param_desc['optional'] = opt
            return param_desc

        csig = inspect.signature(c)
        def rpc_params(params):
            # Skip leading params
            _params = iter(params)
            for p in _params:
                if p.name not in ('self', 'req'):
                    break
            else:
                # No params
                return
            # Params found
            yield p
            yield from _params

        method_sig = {'params': [_describe_param(sigtype, hint, p, i, i >= small_len)
                                 for i, (sigtype, hint, p) in enumerate(
                                     zip_longest(
                                         long_sig[1:],
                                         method_hints and method_hints[1:] or (),
                                         rpc_params(csig.parameters.values())),
                                     1
                                 )],
                      'return' : _describe_param(
                          long_sig[0],
                          None if method_hints is None else method_hints[0],
                      ),
                      'doc': inspect.getdoc(c),}
        return method_sig

