#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright 2009-2011 Olemis Lang <olemis at gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


r"""Exception classes used to describe generic RPC protocol errors.

Copyright 2009-2011 Olemis Lang <olemis at gmail.com>
Licensed under the GPL License
"""
__author__ = 'Olemis Lang'

from tracrpc.api import RPCError, MethodNotFound as NoSuchMethodException, \
                        ProtocolException, ServiceException

__metaclass__ = type

class NoSuchObjectException(RPCError):
  r"""The requested object (namespace) does not exist. """

class RequireHeaderException(RPCError):
  r"""A required header was not understood by the server"""

