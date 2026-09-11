# -*- coding: utf-8 -*-

# Copyright 2026 Olemis Lang <olemis at gmail.com>
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


"""
Test suite for Trac Hessian compliance with wiki API.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

import datetime
import time
import unittest

from trac.util.datefmt import to_datetime, to_utimestamp, utc

from tracrpc.util import unicode, xmlrpclib
from tracrpc.tests import Request, b64encode, urlopen, makeSuite
from tracrpc.tests.wiki import RpcWikiTestCase

from tracrpcext._hessian import HessianProtocol

from ..util import TracRpcProtocolTestSuite
from . import PyHessianTestCase

from pyhessian.protocol import Binary, Fault

class PyHessianWikiTestCase(PyHessianTestCase):
  image_in = RpcWikiTestCase.image_in

  def test_attachments(self):
    # Create attachment
    getattr(self.admin, 'wiki.putAttachmentEx')(
      'TitleIndex', 'feed2.png', 'test image',
      Binary(self.image_in)
    )
    self.assertEqual(
      self.image_in,
      getattr(self.admin, 'wiki.getAttachment')(
        'TitleIndex/feed2.png'
      ).value
    )

    # Update attachment (adding new)
    getattr(self.admin, 'wiki.putAttachmentEx')(
      'TitleIndex', 'feed2.png', 'test image',
      Binary(self.image_in), False)
    self.assertEqual(
      self.image_in,
      getattr(self.admin, 'wiki.getAttachment')(
        'TitleIndex/feed2.2.png'
      ).value
    )

    # List attachments
    self.assertEqual(
      ['TitleIndex/feed2.2.png', 'TitleIndex/feed2.png'],
      sorted(
        getattr(self.admin, 'wiki.listAttachments')('TitleIndex')
    ))
    # Delete both attachments
    getattr(self.admin, 'wiki.deleteAttachment')('TitleIndex/feed2.png')
    getattr(self.admin, 'wiki.deleteAttachment')('TitleIndex/feed2.2.png')
    # List attachments again
    self.assertEqual(
      (),
      getattr(self.admin, 'wiki.listAttachments')('TitleIndex')
    )

  def test_getRecentChanges(self):
    getattr(self.admin, 'wiki.putPage')(
      'WikiOne', 'content one', {}
    )
    time.sleep(1)
    getattr(self.admin, 'wiki.putPage')(
      'WikiTwo', 'content two', {}
    )
    attrs2 = getattr(self.admin, 'wiki.getPageInfo')(
      'WikiTwo'
    )
    changes = getattr(self.admin, 'wiki.getRecentChanges')(
      attrs2['lastModified']
    )
    self.assertEqual(1, len(changes))
    self.assertEqual('WikiTwo', changes[0]['name'])
    self.assertEqual('admin', changes[0]['author'])
    self.assertEqual(1, changes[0]['version'])
    getattr(self.admin, 'wiki.deletePage')('WikiOne')
    getattr(self.admin, 'wiki.deletePage')('WikiTwo')

  def test_getPageHTMLWithImage(self):
    # Create the wiki page (absolute image reference)
    getattr(self.admin, 'wiki.putPage')(
      'ImageTest', '[[Image(wiki:ImageTest:feed.png, nolink)]]\n', {}
    )
                        
    # Create attachment
    getattr(self.admin, 'wiki.putAttachmentEx')(
      'ImageTest', 'feed.png', 'test image',
      Binary(self.image_in)
    )
    # Check rendering absolute
    markup_1 = getattr(self.admin, 'wiki.getPageHTML')(
      'ImageTest'
    )
    self.assertIn((' src="%s/raw-attachment/wiki/ImageTest/feed.png"' %
                       self._testenv.url), markup_1)
    # Change to relative image reference and check again
    getattr(self.admin, 'wiki.putPage')(
      'ImageTest', '[[Image(feed.png, nolink)]]\n', {}
    )
    markup_2 = getattr(self.admin, 'wiki.getPageHTML')(
      'ImageTest'
    )
    self.assertEqual(markup_2, markup_1)


def test_suite():
  suite = TracRpcProtocolTestSuite()
  suite.addTest(makeSuite(PyHessianWikiTestCase))
  return suite


if __name__ == '__main__':
  unittest.main(defaultTest='test_suite')

