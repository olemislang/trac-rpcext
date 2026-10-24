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


r"""Helper classes and functions.

Copyright 2010 Olemis Lang <olemis at gmail.com>
Licensed under the Apache version 2 License
"""
__author__ = 'Olemis Lang'

__metaclass__ = type

import inspect
import logging
try:
  from threading import get_native_id as get_thread_id
except ImportError:
  from threading import get_ident as get_thread_id
import types

from trac.util.datefmt import format_datetime
from trac.util.text import to_unicode

from tracrpc.api import XMLRPCSystem

#------------------------------
# Reusable RPC helpers
#------------------------------

def multicall_result(value, r_id=None, proto_id=None, log=None):
    if not isinstance(value, Exception):
        return {'result': value, 'error': None, 'id': r_id}
    else:
        return multicall_error(value, r_id=r_id,
                               proto_id=proto_id, log=log)

def multicall_error(e, c=None, r_id=None, proto_id=None, log=None):
    # Import in local namespace to prevent circular reference
    from . import exc

    stack_trace = e.__class__, e, e.__traceback__
    e = exc.to_rpc_error(e)
    e.proto_id = proto_id
    # Log error for reference included in e.details
    log.exception(e.details, exc_info=e)
    result = {'result': None,
              'error': {'name': e.__class__.__name__,
                        'message': to_unicode(e),
                        'detail': e.details,}}
    if c is not None:
        result['error']['code'] = c
    if r_id is not None:
        result['id']= r_id
    return result

#------------------------------
# Logging
#------------------------------

logging = types.SimpleNamespace(
  RPCERROR = (logging.WARNING + logging.ERROR) // 2,
  rpcerror = lambda log, msg, *args, **kwargs: log.log(logging.RPCERROR,
                                                       msg,
                                                       *args, **kwargs),
)

def timestamp_label():
  '''Label to identify a moment in time.

  Currently formed by joining current date and time plus native thread ID.
  '''
  return ':'.join([
    format_datetime(format='%Y%m%d%H%M%S%f'),
    str(get_thread_id())
  ])

#------------------------------
# Functions and callable
#------------------------------

POS_PARAM_KINDS = {
    inspect.Parameter.POSITIONAL_ONLY,
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
}

def parse_rpc_kwargs(env, method_name, params):
  '''Parse RPC method parameters by argument name.

  Considers positional arguments only.
  '''
  rpc_sys = env[XMLRPCSystem]
  if rpc_sys is None:
    raise RuntimeError('Unable to load XMLRPCSystem. Disabled?')
  method = rpc_sys.get_method(method_name)
  sig = inspect.signature(method.callable)
  # Create copy
  params = dict(params)
  new_params = []

  def iter_sig_params(sig_params):
    sig_params = iter(sig_params)
    p = None
    for p in sig_params:
      # Skip leading Trac-specific args
      if p.name not in {'self', 'req'}:
          break
      p = None
    if p is not None:
      # First arg in exposed RPC signature
      yield p
      yield from sig_params

  for p in iter_sig_params(sig.parameters.values()):
    if p.kind not in POS_PARAM_KINDS:
      break
    try:
      new_params.append(params.pop(p.name))
    except KeyError:
      # Try to fallback to default argument value
      if p.default is not p.empty:
        if len(params) == 0:
          # No more params left to match.
          # Leave the rest to Python call semantics
          break
        new_params.append(p.default)
      else:
        raise
  if len(params) > 0:
    # Unknown argument name
    argnm = next(iter(params.keys()))
    raise NameError(argnm)
  return new_params

