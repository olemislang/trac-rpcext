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
Test suite for Trac Hessian compliance with ticket API.

License: Apache License 2.0

(c) 2026 ::: Olemis Lang <olemis at gmail.com>
"""

import datetime
import time
import unittest

from trac.util.datefmt import to_datetime, to_utimestamp, utc

from tracrpc.util import unicode, xmlrpclib
from tracrpc.tests import Request, b64encode, urlopen, makeSuite
from tracrpc.tests.ticket import RpcTicketTestCase

from tracrpcext._hessian import HessianProtocol

from ..util import TracRpcProtocolTestSuite
from . import PyHessianTestCase

from pyhessian.protocol import Fault

class PyHessianTicketTestCase(PyHessianTestCase):
  def test_create_get_delete(self):
    tid = getattr(
      self.admin, 'ticket.create'
    )("create_get_delete", "fooy", {})
    tid, time_created, time_changed, attributes = getattr(
      self.admin, 'ticket.get'
    )(tid)
    self.assertEqual('fooy', attributes['description'])
    self.assertEqual('create_get_delete', attributes['summary'])
    self.assertEqual('new', attributes['status'])
    self.assertEqual('admin', attributes['reporter'])
    getattr(
      self.admin, 'ticket.delete'
    )(tid)
    # Check that ticket no longer exists
    try:
      reply = getattr(
        self.admin, 'ticket.get'
      )(tid)
    except Fault as e:
      self.assertFaultMatches(e,
        'NoSuchObjectException',
        'Ticket 1 does not exist.',
        r'RPC\(hessian\) reference : \d+:\d+'
      )
    else:
      self.fail('Unexpected success')

  def test_create_empty_summary(self):
    try:
      getattr(self.admin, 'ticket.create')(
        "", "the description", {}
      )
    except Fault as e:
      self.assertIn("Tickets must contain a summary.", unicode(e))
    else:
      self.fail("Exception not raised creating ticket with empty summary")

  def test_getActions(self):
    tid = getattr(self.admin, 'ticket.create')(
      "ticket_getActions", "kjsald", {'owner': ''}
    )
    try:
      actions = getattr(self.admin, 'ticket.getActions')(tid)
    finally:
      getattr(self.admin, 'ticket.delete')(tid)
    default = [['leave', 'leave', '.', []], ['resolve', 'resolve',
                "The resolution will be set. Next status will be 'closed'.",
               [['action_resolve_resolve_resolution', 'fixed',
               ['fixed', 'invalid', 'wontfix', 'duplicate', 'worksforme']]]],
               ['reassign', 'reassign',
                "The owner will change from (none). Next status will be 'assigned'.",
                [['action_reassign_reassign_owner', 'admin', []]]],
               ['accept', 'accept',
                "The owner will change from (none) to admin. Next status will be 'accepted'.", []]]
    # Adjust for trac:changeset:9041
    if 'will be changed' in actions[2][2]:
      default[2][2] = default[2][2].replace('will change', 'will be changed')
      default[3][2] = default[3][2].replace('will change', 'will be changed')
    # Adjust for trac:changeset:11777
    if not 'from (none).' in actions[2][2]:
      default[2][2] = default[2][2].replace(
        'from (none).',
        'from (none) to the specified user.'
      )
    # Adjust for trac:changeset:11778
    if actions[0][2] != '.':
      default[0][2] = 'The ticket will remain with no owner.'
    # Adjust for trac:changeset:13203 and trac:changeset:14393
    if '<span class=' in actions[2][2]:
      default[2][2] = default[2][2].replace(
        ' (none)',
        ' <span class="trac-author-none">(none)</span>'
      )
      default[3][2] = default[3][2].replace(
        ' (none)',
        ' <span class="trac-author-none">(none)</span>'
      )
      default[3][2] = default[3][2].replace(
        ' admin',
        ' <span class="trac-author-user">admin</span>'
      )
    self.assertEqual(actions, default)

  _delete_ticket_action_controller = RpcTicketTestCase._delete_ticket_action_controller

  def test_getAvailableActions_DeleteTicket(self):
    # Based on http://trac-hacks.org/ticket/5387
    #tktapi = self.admin.ticket
    env = self._testenv.get_trac_environment()
    tid = getattr(self.admin, 'ticket.create')('abc', 'def', {})
    try:
      self.assertNotIn(
        'delete',
        getattr(self.admin, 'ticket.getAvailableActions')(tid)
      )
      env.config.set('ticket', 'workflow',
        'ConfigurableTicketWorkflow,DeleteTicketActionController'
      )
      env.config.save()
      with self._plugin(self._delete_ticket_action_controller,
                        'DeleteTicket.py'):
        self.assertIn(
          'delete',
          getattr(self.admin, 'ticket.getAvailableActions')(tid)
        )
    finally:
      env.config.set('ticket', 'workflow', 'ConfigurableTicketWorkflow')
      env.config.save()
      self.assertEqual(0, getattr(self.admin, 'ticket.delete')(tid))


def test_suite():
  suite = TracRpcProtocolTestSuite()
  suite.addTest(makeSuite(PyHessianTicketTestCase))
  return suite


if __name__ == '__main__':
  unittest.main(defaultTest='test_suite')

