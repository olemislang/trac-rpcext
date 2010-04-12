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


r"""RPC protocols for Trac.

This project implements RPC protocols not provided by
TracXMLRPC plugin. This could be due to conflicting
dependencies, policies, or maybe other reasons. In the former
case this plugin MIGHT NOT install by default all the
dependencies needed by every protocol implementation. In that
case it will check whether dependencies are available or not
and will display informative messages if it is not possible
to process client requests.

Copyright 2009-2011 Olemis Lang <olemis at gmail.com>
Licensed under the GPL License
"""
__author__ = 'Olemis Lang'

# Ignore errors to avoid Internal Server Errors
from trac.core import TracError
TracError.__str__ = lambda self: unicode(self).encode('ascii', 'ignore')

try:
    from _hessian import *
    msg = 'Ok'
except Exception, exc:
#    raise
    msg = "Exception %s raised: '%s'" % (exc.__class__.__name__, str(exc))
