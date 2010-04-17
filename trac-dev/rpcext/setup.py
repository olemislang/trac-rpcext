#!/usr/bin/env python

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


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from tracrpcext.__init__ import __doc__ as DESC

versions = [
    (1, 0, 0),
    ]
    
latest = '.'.join(str(x) for x in versions[-1])

status = {
            'planning' :  "Development Status :: 1 - Planning",
            'pre-alpha' : "Development Status :: 2 - Pre-Alpha",
            'alpha' :     "Development Status :: 3 - Alpha",
            'beta' :      "Development Status :: 4 - Beta",
            'stable' :    "Development Status :: 5 - Production/Stable",
            'mature' :    "Development Status :: 6 - Mature",
            'inactive' :  "Development Status :: 7 - Inactive"
         }
dev_status = status["alpha"]

cats = [
    dev_status,
    
      "Environment :: Plugins", 
      "Environment :: Web Environment", 
      "Framework :: Trac", 
      "Intended Audience :: Developers", 
      "Intended Audience :: Information Technology", 
      "Intended Audience :: Other Audience", 
      "Intended Audience :: System Administrators", 
      "License :: OSI Approved :: GNU General Public License", 
      "Natural Language :: English", 
      "Natural Language :: Spanish", 
      "Operating System :: OS Independent", 
      "Programming Language :: Python", 
      "Programming Language :: Python :: 2.5", 
      "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries", 
      "Topic :: Internet :: WWW/HTTP :: HTTP Servers", 
      "Topic :: Internet :: WWW/HTTP :: WSGI", 
      "Topic :: Software Development :: Bug Tracking", 
      "Topic :: Software Development :: Libraries :: Application Frameworks", 
      "Topic :: Software Development :: Libraries :: Python Modules", 
    ]

# Be compatible with older versions of Python
from sys import version
if version < '2.2.3':
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None

# Add the change log to the package description.
chglog = None
try:
    from os.path import dirname, join
    chglog = open(join(dirname(__file__), "CHANGES"))
    DESC+= ('\n\n' + chglog.read())
finally:
    if chglog:
        chglog.close()

DIST_NM = 'TracRpcProtocols'
PKG_INFO = {'tracrpcext' : ('tracrpcext',                     # Package dir
                            # Package data
                            ['../CHANGES', '../TODO', '../COPYRIGHT', 
                              '../NOTICE', '../README'],
                          ), 
            }

ENTRY_POINTS = r"""
               [trac.plugins]
               tracrpcext = tracrpcext
               """

setup(
	name=DIST_NM,
	version=latest,
	description=DESC.split('\n', 1)[0],
	author='Olemis Lang',
	author_email='olemis+trac@gmail.com',
	maintainer='Olemis Lang',
	maintainer_email='olemis+trac@gmail.com',
	url='https://opensvn.csie.org/traccgi/swlcu/wiki/En/Devel/%s' % (DIST_NM,),
  download_url='http://pypi.python.org/packages/2.5/%s/%s/%s-%s-py2.5.egg' % \
                                (DIST_NM[0], DIST_NM, DIST_NM, latest,),
  requires = ['trac',  'tracrpc',  'hessian', 'pyamf', 
#              'soaplib',  'XMPPXMLRPCServer', 
              ],
  install_requires = [
      'setuptools>=0.6b1',
      'Trac>=0.11',
        'TracXMLRPC>=1.1.0', 
        'HessianPy>=1.0.4', 
        'PyAMF>=0.5',
#        'soaplib>=0.8.1', 
#        'xmppxmlrpc>=0.3', 
    ],
  package_dir = dict([p, i[0]] for p, i in PKG_INFO.iteritems()),
  packages = PKG_INFO.keys(),
  package_data = dict([p, i[1]] for p, i in PKG_INFO.iteritems()),
  include_package_data=True,
  provides = ['%s (%s)' % (p, latest) for p in PKG_INFO.keys()],
  obsoletes = ['%s (>=%s.0.0, <%s)' % (p, versions[-1][0], latest) \
                for p in PKG_INFO.keys()],
  entry_points = ENTRY_POINTS,
  classifiers = cats,
  long_description= DESC
  )
