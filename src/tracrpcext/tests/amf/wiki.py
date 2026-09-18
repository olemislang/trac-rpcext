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
Test suite for Trac AMF compliance with wiki API.

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

from ..util import TracRpcProtocolTestSuite
from . import Py3AMFTestCase

from pyamf import amf3
from pyamf.remoting import RemotingError

class Py3AMFWikiTestCase(Py3AMFTestCase):
  image_in = RpcWikiTestCase.image_in

  def test_attachments(self):
    # Create attachment
    rpc_wiki = self.admin.getService('wiki')

    rpc_wiki.putPage('TestAmf/Attachments', 'content', {})
    rpc_wiki.putAttachmentEx(
      'TestAmf/Attachments', 'feed2.png', 'test image',
      amf3.ByteArray(self.image_in)
    )
    rv = rpc_wiki.getAttachment(f'TestAmf/Attachments/feed2.png')
    self.assertEqual(
      self.image_in,
      rv.getvalue()
    )

    # Update attachment (adding new)
    rpc_wiki.putAttachmentEx(
      'TestAmf/Attachments', 'feed2.png', 'test image',
      amf3.ByteArray(self.image_in), False
    )
    rv = rpc_wiki.getAttachment(f'TestAmf/Attachments/feed2.2.png')
    self.assertEqual(
      self.image_in,
      rv.getvalue()
    )

    # List attachments
    self.assertEqual(
      [f'TestAmf/Attachments/feed2.2.png', f'TestAmf/Attachments/feed2.png'],
      sorted(
        rpc_wiki.listAttachments('TestAmf/Attachments')
    ))
    # Delete both attachments
    rpc_wiki.deleteAttachment(f'TestAmf/Attachments/feed2.png')
    rpc_wiki.deleteAttachment(f'TestAmf/Attachments/feed2.2.png')
    # List attachments again
    self.assertEqual(
      [],
      rpc_wiki.listAttachments('TestAmf/Attachments')
    )

  def test_getRecentChanges(self):
    rpc_wiki = self.admin.getService('wiki')
    rpc_wiki.putPage('TestAmf/WikiOne', 'content one', {})
    time.sleep(1)
    rpc_wiki.putPage('TestAmf/WikiTwo', 'content two', {})
    attrs2 = rpc_wiki.getPageInfo('TestAmf/WikiTwo')
    changes = rpc_wiki.getRecentChanges(attrs2['lastModified'])
    self.assertEqual(1, len(changes))
    self.assertEqual('TestAmf/WikiTwo', changes[0]['name'])
    self.assertEqual('admin', changes[0]['author'])
    self.assertEqual(1, changes[0]['version'])
    rpc_wiki.deletePage('TestAmf/WikiOne')
    rpc_wiki.deletePage('TestAmf/WikiTwo')

  def test_getPageHTMLWithImage(self):
    # Create the wiki page (absolute image reference)
    rpc_wiki = self.admin.getService('wiki')
    rpc_wiki.putPage(
      'TestAmf/ImageTest', '[[Image(wiki:TestAmf/ImageTest:feed.png, nolink)]]\n', {}
    )
                        
    # Create attachment
    rpc_wiki.putAttachmentEx(
      'TestAmf/ImageTest', 'feed.png', 'test image',
      amf3.ByteArray(self.image_in)
    )
    # Check rendering absolute
    markup_1 = rpc_wiki.getPageHTML('TestAmf/ImageTest')
    self.assertIn((' src="%s/raw-attachment/wiki/TestAmf/ImageTest/feed.png"' %
                       self._testenv.url), markup_1)
    # Change to relative image reference and check again
    rpc_wiki.putPage(
      'TestAmf/ImageTest', '[[Image(feed.png, nolink)]]\n', {}
    )
    markup_2 = rpc_wiki.getPageHTML('TestAmf/ImageTest')
    self.assertEqual(markup_2, markup_1)

  def test_getPageHTMLWithManipulator(self):
    rpc_wiki = self.admin.getService('wiki')
    rpc_wiki.putPage('TestAmf/FooBar', 'foo bar', {})

    # Enable wiki manipulator
    source = r"""# -*- coding: utf-8 -*-
from trac.core import *
from trac.wiki.api import IWikiPageManipulator
class WikiManipulator(Component):
    implements(IWikiPageManipulator)
    def prepare_wiki_page(self, req, page, fields):
        fields['text'] = 'foo bar baz'
    def validate_wiki_page(req, page):
        return []
"""
    with self._plugin(source, 'Manipulator.py'):
      self.assertEqual(
        '<html><body><p>\nfoo bar baz\n</p>\n'
        '</body></html>',
        rpc_wiki.getPageHTML('TestAmf/FooBar')
      )


def test_suite():
  suite = TracRpcProtocolTestSuite()
  suite.addTest(makeSuite(Py3AMFWikiTestCase))
  return suite


if __name__ == '__main__':
  unittest.main(defaultTest='test_suite')

