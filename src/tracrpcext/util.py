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

import logging
try:
  from threading import get_native_id as get_thread_id
except ImportError:
  from threading import get_ident as get_thread_id
import types

from trac.util.datefmt import format_datetime

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


