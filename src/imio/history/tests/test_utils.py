from DateTime import DateTime

from zope.component import getAdapter
from zope.component import ComponentLookupError
from plone import api

from imio.history.interfaces import IImioHistory
from imio.history.testing import IntegrationTestCase
from imio.history.utils import add_event_to_history
from imio.history.utils import getLastAction
from imio.history.utils import getPreviousEvent


class TestUtils(IntegrationTestCase):

    def test_getPreviousEvent(self):
        """Test the getPreviousEvent method.
           It should return the previous event for a given event if it exists."""
        doc = api.content.create(type='Document',
                                 id='doc',
                                 container=self.portal)
        adapter = getAdapter(doc, IImioHistory, 'workflow')
        history = adapter.getHistory()
        firstEvent = history[0]
        # this is the 'creation' event
        self.assertTrue(firstEvent['action'] is None)
        self.assertTrue(getPreviousEvent(doc, firstEvent) is None)

        # now publish the doc so we have an new event in the workflow_history
        api.content.transition(doc, 'publish', comment='My comment')
        history = adapter.getHistory()
        lastEvent = history[-1]
        self.assertTrue(lastEvent['action'] == 'publish')
        self.assertTrue(getPreviousEvent(doc, lastEvent) == firstEvent)

        # if the event is not found, None is returned
        wrongEvent = {'action': 'wrong',
                      'review_state': 'wrong',
                      'comments': 'My wrong comment',
                      'actor': 'wrong',
                      'time': DateTime('2015/01/01 13:30:0.0 GMT+2')}
        self.assertTrue(getPreviousEvent(doc, wrongEvent) is None)

    def test_getLastAction(self):
        """Test the utils.getLastAction method.
           It should return the action passed in parameter for the given history name."""
        doc = api.content.create(type='Document',
                                 id='doc',
                                 container=self.portal)
        # publish the doc so we have an new event in the workflow_history
        api.content.transition(doc, 'publish', comment='First publication comment')
        self.assertEqual(getLastAction(doc)['action'], 'publish')
        # same as getting action with that name
        publish_action = getLastAction(doc, action='publish')
        self.assertEqual(publish_action['action'], 'publish')
        self.assertEqual(publish_action['comments'], 'First publication comment')

        # publish again, check that we correctly get last action
        api.content.transition(doc, 'retract')
        api.content.transition(doc, 'publish', comment='Second publication comment')
        publish_action = getLastAction(doc, action='publish')
        self.assertEqual(publish_action['action'], 'publish')
        self.assertEqual(publish_action['comments'], 'Second publication comment')

        # the creation event is stored with a None action
        self.assertEqual(getLastAction(doc, action=None)['review_state'], 'private')

        # if action not found, None is returned
        self.assertIsNone(getLastAction(doc, action='unknown_action'))

    def test_getLastAction_unknown_history(self):
        """Breaks if unknown history."""
        self.assertRaises(
            ComponentLookupError,
            getLastAction, self.portal.folder, history_name='unknown_history')

    def test_getLastAction_history_empty(self):
        """Does not breaks and returns None if history empty."""
        self.assertIsNone(getLastAction(self.portal.folder, history_name='revision'))

    def test_add_event_to_history(self):
        """Add an event to an history following an action."""
        folder = self.portal.folder
        # if history attr does not exist, it is created
        DUMMY_HISTORY_ATTR = 'dummy_history'
        self.assertFalse(hasattr(folder, DUMMY_HISTORY_ATTR))

        # action1 with default values
        add_event_to_history(folder, DUMMY_HISTORY_ATTR, 'action1')
        added_action1 = getattr(folder, DUMMY_HISTORY_ATTR)[0]
        self.assertEqual(added_action1['action'], 'action1')
        # current user id in actor
        self.assertEqual(added_action1['actor'], 'test_user_1_')
        self.assertEqual(added_action1['actor'], api.user.get_current().getId())
        self.assertEqual(added_action1['comments'], '')
        self.assertTrue(isinstance(added_action1['time'], DateTime))

        # action2 with parameters
        new_user = api.user.create(username='dummy_user', email='dummy@user.org')
        add_event_to_history(folder,
                             DUMMY_HISTORY_ATTR,
                             'action2',
                             actor=new_user,
                             time=DateTime('2018/01/12'),
                             comments=u'My comments',
                             extra_infos={'dummy_info1': u'Information 1',
                                          'dummy_info2': u'Information 2'})
        added_action2 = getattr(folder, DUMMY_HISTORY_ATTR)[1]
        self.assertEqual(added_action2['action'], 'action2')
        self.assertEqual(added_action2['actor'], new_user.getId())
        self.assertEqual(added_action2['comments'], u'My comments')
        self.assertEqual(added_action2['time'], DateTime('2018/01/12'))
        # extra infos
        self.assertEqual(added_action2['dummy_info1'], u'Information 1')
        self.assertEqual(added_action2['dummy_info2'], u'Information 2')
