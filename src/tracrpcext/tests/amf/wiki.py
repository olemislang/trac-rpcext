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

from pyamf.remoting import RemotingError

class Py3AMFWikiTestCase(Py3AMFTestCase):
  image_in = RpcWikiTestCase.image_in

  def test_attachments(self):
    # Create attachment
    rpc_wiki = self.admin.getService('wiki')
    rpc_wiki.putAttachmentEx(
      'TitleIndex', 'feed2.png', 'test image', self.image_in
    )
    self.assertEqual(
      self.image_in,
      rpc_wiki.getAttachment('TitleIndex/feed2.png')
    )

    # Update attachment (adding new)
    rpc_wiki.putAttachmentEx(
      'TitleIndex', 'feed2.png', 'test image',
      self.image_in, False
    )
    self.assertEqual(
      self.image_in,
      rpc_wiki.getAttachment('TitleIndex/feed2.2.png')
    )

    # List attachments
    self.assertEqual(
      ['TitleIndex/feed2.2.png', 'TitleIndex/feed2.png'],
      sorted(
        rpc_wiki.listAttachments('TitleIndex')
    ))
    # Delete both attachments
    rpc_wiki.deleteAttachment('TitleIndex/feed2.png')
    rpc_wiki.deleteAttachment('TitleIndex/feed2.2.png')
    # List attachments again
    self.assertEqual(
      [],
      rpc_wiki.listAttachments('TitleIndex')
    )

  def test_getRecentChanges(self):
    rpc_wiki = self.admin.getService('wiki')
    rpc_wiki.putPage('WikiOne', 'content one', {})
    time.sleep(1)
    rpc_wiki.putPage('WikiTwo', 'content two', {})
    attrs2 = rpc_wiki.getPageInfo('WikiTwo')
    changes = rpc_wiki.getRecentChanges(attrs2['lastModified'])
    self.assertEqual(1, len(changes))
    self.assertEqual('WikiTwo', changes[0]['name'])
    self.assertEqual('admin', changes[0]['author'])
    self.assertEqual(1, changes[0]['version'])
    rpc_wiki.deletePage('WikiOne')
    rpc_wiki.deletePage('WikiTwo')


def test_suite():
  suite = TracRpcProtocolTestSuite()
  suite.addTest(makeSuite(Py3AMFWikiTestCase))
  return suite


if __name__ == '__main__':
  unittest.main(defaultTest='test_suite')

