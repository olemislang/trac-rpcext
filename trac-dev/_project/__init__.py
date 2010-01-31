#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright 2009-2011 Olemis Lang <olemis at gmail.com>
#
${project.license_header}

r"""${project.summary}

${project.desc}

Copyright 2009-2011 Olemis Lang <olemis at gmail.com>
Licensed under the ${project.license} License
"""
__author__ = 'Olemis Lang'

# Ignore errors to avoid Internal Server Errors
from trac.core import TracError
TracError.__str__ = lambda self: unicode(self).encode('ascii', 'ignore')

try:
    from ${project.topmod} import *
    msg = 'Ok'
except Exception, exc:
#    raise
    msg = "Exception %s raised: '%s'" % (exc.__class__.__name__, str(exc))
