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
        f'Ticket {tid} does not exist.',
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

    # Hessian client returns tuples instead of list
    def tuplify(l):
        return tuple(tuplify(x) if isinstance(x, list) else x
                     for x in l
        )
    default = tuplify(default)
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

  def test_FineGrainedSecurity(self):
    tid1 = getattr(self.admin, 'ticket.create')('abc', '123', {})
    tid2 = getattr(self.admin, 'ticket.create')('def', '456', {})
    self.assertEqual(tid2, tid1 + 1)
    # First some non-restricted tests for comparison:
    self.assertRaises(
      Fault,
      getattr(self.anon, 'ticket.create'),
      'abc', 'def'
    )
    self.assertEqual(
      (tid1, tid2),
      getattr(self.user, 'ticket.query')()
    )
    self.assertTrue(getattr(self.user, 'ticket.get')(tid2))
    self.assertTrue(getattr(self.user, 'ticket.update')(tid1, "ok"))
    self.assertTrue(getattr(self.user, 'ticket.update')(tid2, "ok"))
    # Enable security policy and test
    source = rf"""# -*- coding: utf-8 -*-
from trac.core import Component, implements
from trac.perm import IPermissionPolicy
class TicketPolicy(Component):
    implements(IPermissionPolicy)
    def check_permission(self, action, username, resource, perm):
        if username == 'user' and resource and resource.id == {tid2}:
            return False
        if username == 'anonymous' and action == 'TICKET_CREATE':
            return True
"""
    env = self._testenv.get_trac_environment()
    _old_conf = env.config.get('trac', 'permission_policies')
    env.config.set('trac', 'permission_policies',
                       'TicketPolicy,' + _old_conf)
    env.config.save()
    try:
      with self._plugin(source, 'TicketPolicy.py'):
        self._testenv.restart()
        self.assertEqual(
          (tid1,),
          getattr(self.user, 'ticket.query')()
        )
        self.assertTrue(getattr(self.user, 'ticket.get')(tid1))
        self.assertRaises(
          Fault,
          getattr(self.user, 'ticket.get'),
          tid2
        )
        self.assertTrue(getattr(self.user, 'ticket.update')(tid1, "ok"))
        self.assertRaises(
          Fault,
          getattr(self.user, 'ticket.update'),
          tid2, "not ok"
        )
        tid3 = getattr(self.anon, 'ticket.create')('efg', '789', {})
        self.assertEqual(tid3, tid2 + 1)
    finally:
      # Clean, reset and simple verification
      env.config.set('trac', 'permission_policies', _old_conf)
      env.config.save()

    self.assertEqual(
      (tid1, tid2, tid3),
      getattr(self.user, 'ticket.query')()
    )
    self.assertEqual(
      0,
      getattr(self.admin, 'ticket.delete')(tid1)
    )
    self.assertEqual(
      0,
      getattr(self.admin, 'ticket.delete')(tid2)
    )
    self.assertEqual(
      0,
      getattr(self.admin, 'ticket.delete')(tid3)
    )

  def test_getRecentChanges(self):
    tid1 = getattr(self.admin, 'ticket.create')(
      "ticket_getRecentChanges", "one", {}
    )
    time.sleep(1)
    tid2 = getattr(self.admin, 'ticket.create')(
      "ticket_getRecentChanges", "two", {}
    )
    try:
      _id, created, modified, attributes = getattr(
        self.admin, 'ticket.get'
      )(tid2)
      changes = getattr(self.admin, 'ticket.getRecentChanges')(created)
      self.assertEqual(changes, (tid2,))
    finally:
      getattr(self.admin, 'ticket.delete')(tid1)
      getattr(self.admin, 'ticket.delete')(tid2)

  def test_query_group_order_col(self):
    t1 = getattr(self.admin, 'ticket.create')(
      "1", "", {'type': 'enhancement', 'owner': 'A'}
    )
    t2 = getattr(self.admin, 'ticket.create')(
      "2", "", {'type': 'task', 'owner': 'B'}
    )
    t3 = getattr(self.admin, 'ticket.create')(
      "3", "", {'type': 'defect', 'owner': 'A'}
    )
    # order
    self.assertEqual(
      (t3, t1, t2),
      getattr(self.admin, 'ticket.query')("order=type")
    )
    self.assertEqual(
      (t1, t3, t2),
      getattr(self.admin, 'ticket.query')("order=owner")
    )
    self.assertEqual(
      (t2, t1, t3),
      getattr(self.admin, 'ticket.query')("order=owner&desc=1")
    )
    # group
    self.assertEqual(
      (t1, t3, t2),
      getattr(self.admin, 'ticket.query')("group=owner")
    )
    self.assertEqual(
      (t2, t1, t3),
      getattr(self.admin, 'ticket.query')("group=owner&groupdesc=1")
    )
    # group + order
    self.assertEqual(
      (t2, t3, t1),
      getattr(self.admin, 'ticket.query')("group=owner&groupdesc=1&order=type")
    )
    # col should just be ignored
    self.assertEqual(
      (t3, t1, t2),
      getattr(self.admin, 'ticket.query')("order=type&col=status&col=reporter")
    )
    # clean
    self.assertEqual(
      0,
      getattr(self.admin, 'ticket.delete')(t1)
    )
    self.assertEqual(
      0,
      getattr(self.admin, 'ticket.delete')(t2)
    )
    self.assertEqual(
      0,
      getattr(self.admin, 'ticket.delete')(t3)
    )

  def test_query_special_character_escape(self):
    summary = ("here&now", "maybe|later", r"back\slash")
    search = (r"here\&now", r"maybe\|later", r"back\slash")
    tids = []
    for s in summary:
      tids.append(
        getattr(self.admin, 'ticket.create')(
          s, "test_special_character_escape", {}
        )
      )
                          
    try:
      sorted_tids = sorted(tids)
      for i in range(0, 3):
        self.assertEqual(
          (tids[i],),
          getattr(self.admin, 'ticket.query')(
            "summary=%s" % search[i]
          )
        )
        self.assertEqual(
          sorted_tids,
          sorted(
            getattr(self.admin, 'ticket.query')(
              "summary=%s" % "|".join(search)
        )))
    finally:
      for tid in tids:
        getattr(self.admin, 'ticket.delete')(tid)

  def test_update_author(self):
    tid = getattr(self.admin, 'ticket.create')(
      "ticket_update_author", "one", {}
    )
    getattr(self.admin, 'ticket.update')(
      tid, 'comment1', {}
    )
    time.sleep(1)
    getattr(self.admin, 'ticket.update')(
      tid, 'comment2', {}, False, 'foo'
    )
    time.sleep(1)
    getattr(self.user, 'ticket.update')(
      tid, 'comment3', {}, False, 'should_be_rejected'
    )
    changes = getattr(self.admin, 'ticket.changeLog')(tid)
    self.assertEqual(3, len(changes))
    for when, who, what, cnum, comment, _tid in changes:
      self.assertIn(comment, ('comment1', 'comment2', 'comment3'))
      if comment == 'comment1':
        self.assertEqual('admin', who)
      if comment == 'comment2':
        self.assertEqual('foo', who)
      if comment == 'comment3':
        self.assertEqual('user', who)
    getattr(self.admin, 'ticket.delete')(tid)


def test_suite():
  suite = TracRpcProtocolTestSuite()
  suite.addTest(makeSuite(PyHessianTicketTestCase))
  return suite


if __name__ == '__main__':
  unittest.main(defaultTest='test_suite')

