#!/usr/bin/env python
# -*- coding: UTF-8 -*-

r"""Initialize Trac project files.

Fill values in `project.ini` file and run this tool before creating 
a Trac project.

Copyright 2009-2011 Olemis Lang <olemis at gmail.com>
Licensed under the General Public License, Version 2.0
"""

from ConfigParser import RawConfigParser as Parser
from genshi.template import NewTextTemplate as T
from os import listdir, mkdir
from os.path import dirname, join, isdir
from shutil import copytree

thisdir = dirname(__file__)

prjcfg = Parser()
prjcfg.read(join(thisdir, '_project.ini'))
prjcfg = dict([s, dict(prjcfg.items(s))] for s in prjcfg.sections())
prjcfg['deps'] = dict([s[5:], opts] for s, opts in prjcfg.iteritems() \
                      if s.startswith('deps/'))

f = None
try :
  try :
    f = open(join(thisdir, '_licenses', 'HDR_' + prjcfg['project']['license']))
    header = f.read()
  except :
    header = '# License: Unknown'
finally :
  if f : f.close()
prjcfg['project']['license_header'] = header

destdir = join(thisdir, '..', prjcfg['project']['folder'])
mkdir(destdir)

def license_cats(license):
  r"""Return categories from license IDs.
  """
  license = license.split(',')
  return [{
            'Apache' : "License :: OSI Approved :: Apache Software License",
            'GPL' : "License :: OSI Approved :: GNU General Public License",
            'LGPL' : "License :: OSI Approved :: GNU Library General Public License",
            'BSD' : "License :: OSI Approved :: BSD License",
          }.get(l, 'License :: Unknown') for l in license]

def expand_file(src, dst):
  ifile = ofile = None
  try :
    ifile = open(src, 'rb')
    ofile = open(dst, 'wb')
    
    tmpl = T(ifile)
    stream = tmpl.generate(license_cats=license_cats, **prjcfg)
    ofile.write(stream.render('text'))
  finally :
    for f in (ifile, ofile):
      if f : f.close()

for fnm in listdir(thisdir) :
  if fnm[0] not in ('_', '.'):
    src = join(thisdir, fnm)
    dst = join(destdir, fnm)
    if isdir(src) :
      copytree(src, dst)
    else :
      expand_file(src, dst)

expand_file(join(thisdir, '_licenses', prjcfg['project']['license']), 
          join(destdir, 'COPYRIGHT'))

destdir = join(destdir, prjcfg['project']['topmod'])
mkdir(destdir)
expand_file(join(thisdir, '__init__.py'), join(destdir, '__init__.py'))