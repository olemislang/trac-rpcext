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
from . import JsonWspTestCase

from jsonwspclient,jsonwspexceptions import JsonWspFault

class JsonWspWikiTestCase(JsonWspTestCase):
  jsonwsp_services = ('wiki',)
  image_in = RpcWikiTestCase.image_in

  def test_attachments(self):
    # Create attachment
    ws_wiki = self.admin.service('wiki')

    ws_wiki.putPage('TestJsonWsp/Attachments', 'content', {})
    ws_wiki.putAttachmentEx(
      'TestJsonWsp/Attachments', 'feed2.png', 'test image',
      self.image_in
    )
    rv = ws_wiki.getAttachment(f'TestJsonWsp/Attachments/feed2.png')
    self.assertEqual(
      self.image_in,
      rv.getvalue()
    )

    # Update attachment (adding new)
    ws_wiki.putAttachmentEx(
      'TestJsonWsp/Attachments', 'feed2.png', 'test image',
      self.image_in, False
    )
    rv = ws_wiki.getAttachment(f'TestJsonWsp/Attachments/feed2.2.png')
    self.assertEqual(
      self.image_in,
      rv.getvalue()
    )

    # List attachments
    self.assertEqual(
      [f'TestJsonWsp/Attachments/feed2.2.png',
       f'TestJsonWsp/Attachments/feed2.png'],
      sorted(
        ws_wiki.listAttachments('TestJsonWsp/Attachments')
    ))
    # Delete both attachments
    ws_wiki.deleteAttachment(f'TestJsonWsp/Attachments/feed2.png')
    ws_wiki.deleteAttachment(f'TestJsonWsp/Attachments/feed2.2.png')
    # List attachments again
    self.assertEqual(
      [],
      ws_wiki.listAttachments('TestJsonWsp/Attachments')
    )

  def test_getRecentChanges(self):
    ws_wiki = self.admin.service('wiki')
    ws_wiki.putPage('TestAmf/WikiOne', 'content one', {})
    time.sleep(1)
    ws_wiki.putPage('TestAmf/WikiTwo', 'content two', {})
    attrs2 = ws_wiki.getPageInfo('TestAmf/WikiTwo')
    changes = ws_wiki.getRecentChanges(attrs2['lastModified'])
    self.assertEqual(1, len(changes))
    self.assertEqual('TestAmf/WikiTwo', changes[0]['name'])
    self.assertEqual('admin', changes[0]['author'])
    self.assertEqual(1, changes[0]['version'])
    ws_wiki.deletePage('TestAmf/WikiOne')
    ws_wiki.deletePage('TestAmf/WikiTwo')


def test_suite():
  suite = TracRpcProtocolTestSuite()
  suite.addTest(makeSuite(JsonWspWikiTestCase))
  return suite


if __name__ == '__main__':
  unittest.main(defaultTest='test_suite')

