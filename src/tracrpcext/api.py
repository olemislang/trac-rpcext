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


r"""Extensions points to Trac API for RPC and web services.

Copyright 2010 Olemis Lang <olemis at gmail.com>
Licensed under the Apache version 2 License
"""
__author__ = 'Olemis Lang'

from trac.core import Interface

from tracrpc.api import IRPCProtocol

__all__ = ['IWebServiceDescriptor']

__metaclass__ = type

class IWebServiceDescriptor(Interface):
    """Provider of meta-data describing web services by leveraging
    exsiting signatures in RPC namespaces.
    """
    def namespaces_described():
        """RPC namespaces described by this component."""

    def get_data_contracts(type_names):
        """Enumerate complex types"""

    def detail_signatures(ns):
        """Describe complex types of RPC methods
        """


class IWebServiceProtocol(IRPCProtocol):
    """Web service protocol provider.
    """
    def ws_init(mapper):
        """Define routes for matching web services URI.

        mapper: routes.Mapper instance

        Web service providers must implement IRPCProtocol as well.
        Parsed routes are provided in request's `ws_` attribute
        and shall include the following variables:

        service:      (required) target web service name
        action:       (optional) action to be performed such as:
                      - 'call' for invoking target web service method,
                        which is the default if omitted,
                      - 'describe' for retrieving web service description
                        in some Interface Definition Language (IDL).
        rpc_proto:    (required for 'call') target RPC protocol ID
                      (as registered via `rpc_info`);
        rpc_pàth:     (required for 'call') path item as registered in 
                      `rpc_match`, usually 'rpc';
        content_type: (required) expected content type of the request
        rpc_content:  (required for 'call') content type as registered
                      in `rpc_match`.
        idl:          (required for 'describe') ID of target IDL 

        Return a dictionary with the following keys

        idl:          a list of identifiers, one for each supported IDL.
        """

    def start_idl_response(req, lang_id):
        """Prepare to respond to 'describe' request.

        lang_id:        Description language ID (as registered in `ws_init`).
        """

    def encode_ws_idl(description, lang_id, writer):
        """Serialize service description into IDL syntax selected by ID

        description:    WebServiceSystem description of the service;
        lang_id:        Description language ID (as registered in `ws_init`);
        writer:         Stream writer.
        """

