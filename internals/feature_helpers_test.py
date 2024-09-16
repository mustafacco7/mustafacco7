# Copyright 2020 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
import testing_config  # Must be imported before the module under test.

from api import converters
from framework import rediscache
from internals.core_enums import *
from internals import feature_helpers
from internals import stage_helpers
from internals.core_models import FeatureEntry, MilestoneSet, Stage


class FeatureHelpersTest(testing_config.CustomTestCase):

  def setUp(self):
    self.feature_2 = FeatureEntry(
        name='feature b', summary='sum',
        owner_emails=['feature_owner@example.com'], category=1,
        updated=datetime(2020, 4, 1), feature_type=1)
    self.feature_2.put()

    self.feature_1 = FeatureEntry(
        name='feature a', summary='sum', impl_status_chrome=3,
        owner_emails=['feature_owner@example.com'], category=1,
        updated=datetime(2020, 3, 1), feature_type=0)
    self.feature_1.put()

    self.feature_3 = FeatureEntry(
        name='feature c', summary='sum', category=1, impl_status_chrome=2,
        owner_emails=['feature_owner@example.com'],
        updated=datetime(2020, 1, 1), feature_type=2)
    self.feature_3.put()

    self.feature_4 = FeatureEntry(
        name='feature d', summary='sum', category=1, impl_status_chrome=2,
        owner_emails=['feature_owner@example.com'],
        updated=datetime(2020, 2, 1), feature_type=3)
    self.feature_4.put()

    fe_1_stage_types = [110, 120, 130, 140, 150, 151, 160]
    fe_2_stage_types = [220, 230, 250, 251, 260]
    fe_3_stage_types = [320, 330, 360]
    fe_4_stage_types = [410, 430, 450, 451, 460]
    self.stages: list[Stage] = []
    for s_type in fe_1_stage_types:
      stage = Stage(
          feature_id=self.feature_1.key.integer_id(), stage_type=s_type)
      stage.put()
    for s_type in fe_2_stage_types:
      stage = Stage(
          feature_id=self.feature_2.key.integer_id(), stage_type=s_type)
      stage.put()
    for s_type in fe_3_stage_types:
      stage = Stage(
          feature_id=self.feature_3.key.integer_id(), stage_type=s_type)
      stage.put()
    for s_type in fe_4_stage_types:
      stage = Stage(
          feature_id=self.feature_4.key.integer_id(), stage_type=s_type)
      stage.put()
    self.fe_1_stages_dict = stage_helpers.get_feature_stages(
        self.feature_1.key.integer_id())
    self.fe_2_stages_dict = stage_helpers.get_feature_stages(
        self.feature_2.key.integer_id())
    self.fe_3_stages_dict = stage_helpers.get_feature_stages(
        self.feature_3.key.integer_id())
    self.fe_4_stages_dict = stage_helpers.get_feature_stages(
        self.feature_4.key.integer_id())

  def tearDown(self):
    for kind in [FeatureEntry, Stage]:
      for entity in kind.query():
        entity.key.delete()

    rediscache.flushall()

  def test_get_all__normal(self):
    """We can retrieve a list of all features with no filter."""
    actual = feature_helpers.get_all(update_cache=True)
    names = [f['name'] for f in actual]
    self.assertEqual(
        ['feature b', 'feature a', 'feature d', 'feature c'],
        names)

    self.feature_1.summary = 'revised summary'
    self.feature_1.put()  # Changes updated field.
    actual = feature_helpers.get_all(update_cache=True)
    names = [f['name'] for f in actual]
    self.assertEqual(
        ['feature b', 'feature a', 'feature d', 'feature c'],
        names)

  def test_get_all__category(self):
    """We can retrieve a list of all features of a given category."""
    actual = feature_helpers.get_all(
        filterby=('category', CSS), update_cache=True)
    names = [f['name'] for f in actual]
    self.assertEqual(
        [],
        names)

    self.feature_1.category = CSS
    self.feature_1.put()  # Changes updated field.
    actual = feature_helpers.get_all(
        filterby=('category', CSS), update_cache=True)
    names = [f['name'] for f in actual]
    self.assertEqual(
        ['feature a'],
        names)

  def test_get_all__owner(self):
    """We can retrieve a list of all features with a given owner."""
    actual = feature_helpers.get_all(
        filterby=('owner_emails', 'owner@example.com'), update_cache=True)
    names = [f['name'] for f in actual]
    self.assertEqual(
        [],
        names)

    self.feature_1.owner_emails = ['owner@example.com']
    self.feature_1.put()  # Changes updated field.
    actual = feature_helpers.get_all(
        filterby=('owner_emails', 'owner@example.com'), update_cache=True)
    names = [f['name'] for f in actual]
    self.assertEqual(
        ['feature a'],
        names)

  def test_get_all__owner_unlisted(self):
    """Unlisted features should still be visible to their owners."""
    self.feature_2.unlisted = True
    self.feature_2.owner_emails = ['feature_owner@example.com']
    self.feature_2.put()
    testing_config.sign_in('feature_owner@example.com', 1234567890)
    actual = feature_helpers.get_all(update_cache=True)
    names = [f['name'] for f in actual]
    testing_config.sign_out()
    self.assertEqual(
      ['feature b', 'feature a', 'feature d', 'feature c'], names)

  def test_get_all__editor_unlisted(self):
    """Unlisted features should still be visible to feature editors."""
    self.feature_2.unlisted = True
    self.feature_2.editor_emails = ['feature_editor@example.com']
    self.feature_2.put()
    testing_config.sign_in("feature_editor@example.com", 1234567890)
    actual = feature_helpers.get_all(update_cache=True)
    names = [f['name'] for f in actual]
    testing_config.sign_out()
    self.assertEqual(
      ['feature b', 'feature a', 'feature d', 'feature c'], names)

  def test_get_by_ids__empty(self):
    """A request to load zero features returns zero results."""
    actual = feature_helpers.get_by_ids([])
    self.assertEqual([], actual)

  def test_get_by_ids__cache_miss(self):
    """We can load features from datastore, and cache them for later."""
    actual = feature_helpers.get_by_ids([
        self.feature_1.key.integer_id(),
        self.feature_2.key.integer_id()])

    self.assertEqual(2, len(actual))
    self.assertEqual('feature a', actual[0]['name'])
    self.assertEqual('feature b', actual[1]['name'])

    lookup_key_1 = '%s|%s' % (FeatureEntry.DEFAULT_CACHE_KEY,
                              self.feature_1.key.integer_id())
    lookup_key_2 = '%s|%s' % (FeatureEntry.DEFAULT_CACHE_KEY,
                              self.feature_2.key.integer_id())
    self.assertEqual('feature a', rediscache.get(lookup_key_1)['name'])
    self.assertEqual('feature b', rediscache.get(lookup_key_2)['name'])

  def test_get_by_ids__cache_hit(self):
    """We can load features from rediscache."""
    cache_key = '%s|%s' % (
        FeatureEntry.DEFAULT_CACHE_KEY, self.feature_1.key.integer_id())
    cached_feature = {
      'name': 'fake cached_feature',
      'id': self.feature_1.key.integer_id(),
      'unlisted': False
    }
    rediscache.set(cache_key, cached_feature)

    actual = feature_helpers.get_by_ids([self.feature_1.key.integer_id()])

    self.assertEqual(1, len(actual))
    self.assertEqual(cached_feature, actual[0])

  def test_get_by_ids__batch_order(self):
    """Features are returned in the order of the given IDs."""
    actual = feature_helpers.get_by_ids([
        self.feature_4.key.integer_id(),
        self.feature_1.key.integer_id(),
        self.feature_3.key.integer_id(),
        self.feature_2.key.integer_id(),
    ])

    self.assertEqual(4, len(actual))
    self.assertEqual('feature d', actual[0]['name'])
    self.assertEqual('feature a', actual[1]['name'])
    self.assertEqual('feature c', actual[2]['name'])
    self.assertEqual('feature b', actual[3]['name'])

  def test_get_by_ids__cached_correctly(self):
    """We should no longer be able to trigger bug #1647."""
    # Cache one to try to trigger the bug.
    feature_helpers.get_by_ids([self.feature_2.key.integer_id()])

    # Now do the lookup, but it would cache feature_2 at the key for feature_3.
    feature_helpers.get_by_ids([
        self.feature_4.key.integer_id(),
        self.feature_1.key.integer_id(),
        self.feature_3.key.integer_id(),
        self.feature_2.key.integer_id(),
    ])

    # This would read the incorrect cache entry and use it.
    actual = feature_helpers.get_by_ids([
        self.feature_4.key.integer_id(),
        self.feature_1.key.integer_id(),
        self.feature_3.key.integer_id(),
        self.feature_2.key.integer_id(),
    ])

    self.assertEqual(4, len(actual))
    self.assertEqual('feature d', actual[0]['name'])
    self.assertEqual('feature a', actual[1]['name'])
    self.assertEqual('feature c', actual[2]['name'])
    self.assertEqual('feature b', actual[3]['name'])

  def test_get_in_milestone__normal(self):
    """We can retrieve a list of features."""
    self.feature_1.impl_status_chrome = 5
    # Set shipping milestone to 1.
    self.fe_1_stages_dict[160][0].milestones = MilestoneSet(desktop_first=1)
    self.feature_1.put()
    self.fe_1_stages_dict[160][0].put()

    self.feature_2.impl_status_chrome = 7
    # Set shipping milestone to 1.
    self.fe_2_stages_dict[260][0].milestones = MilestoneSet(desktop_first=1)
    self.feature_2.put()
    self.fe_2_stages_dict[260][0].put()

    self.feature_3.impl_status_chrome = 5
    # Set shipping milestone to 1.
    self.fe_3_stages_dict[360][0].milestones = MilestoneSet(desktop_first=1)
    self.feature_3.put()
    self.fe_3_stages_dict[360][0].put()

    self.feature_4.impl_status_chrome = 7
    # Set shipping milestone to 1.
    self.fe_4_stages_dict[460][0].milestones = MilestoneSet(desktop_first=2)
    self.feature_4.put()
    self.fe_4_stages_dict[460][0].put()

    actual = feature_helpers.get_in_milestone(milestone=1)
    removed = [f['name'] for f in actual['Removed']]
    enabled_by_default = [f['name'] for f in actual['Enabled by default']]
    self.assertEqual(
        ['feature b'],
        removed)
    self.assertEqual(
        ['feature a', 'feature c'],
        enabled_by_default)
    self.assertEqual(6, len(actual))

    cache_key = '%s|%s|%s' % (
        FeatureEntry.DEFAULT_CACHE_KEY, 'milestone', 1)
    cached_result = rediscache.get(cache_key)
    self.assertEqual(cached_result, actual)

  def test_get_in_milestone__unlisted(self):
    """Unlisted features should not be listed for users who can't edit."""
    self.feature_1.impl_status_chrome = 5
    self.fe_1_stages_dict[160][0].milestones = MilestoneSet(desktop_first=1)
    self.feature_1.put()
    self.fe_1_stages_dict[160][0].put()

    self.feature_2.unlisted = True
    self.feature_2.impl_status_chrome = 7
    self.fe_2_stages_dict[260][0].milestones = MilestoneSet(desktop_first=1)
    self.feature_2.put()
    self.fe_2_stages_dict[260][0].put()

    self.feature_3.impl_status_chrome = 5
    self.fe_3_stages_dict[360][0].milestones = MilestoneSet(desktop_first=1)
    self.feature_3.put()
    self.fe_3_stages_dict[360][0].put()

    self.feature_4.impl_status_chrome = 7
    self.fe_4_stages_dict[460][0].milestones = MilestoneSet(desktop_first=2)
    self.feature_4.put()
    self.fe_4_stages_dict[460][0].put()

    actual = feature_helpers.get_in_milestone(milestone=1)
    self.assertEqual(
        0,
        len(actual['Removed']))

  def test_get_in_milestone__unlisted_shown(self):
    """Unlisted features should be listed for users who can edit."""
    self.feature_1.impl_status_chrome = 5
    self.fe_1_stages_dict[160][0].milestones = MilestoneSet(desktop_first=1)
    self.feature_1.put()
    self.fe_1_stages_dict[160][0].put()

    self.feature_2.unlisted = True
    self.feature_2.impl_status_chrome = 7
    self.fe_2_stages_dict[260][0].milestones = MilestoneSet(desktop_first=1)
    self.feature_2.put()
    self.fe_2_stages_dict[260][0].put()

    self.feature_3.impl_status_chrome = 5
    self.fe_3_stages_dict[360][0].milestones = MilestoneSet(desktop_first=1)
    self.feature_3.put()
    self.fe_3_stages_dict[360][0].put()

    self.feature_4.impl_status_chrome = 7
    self.fe_4_stages_dict[460][0].milestones = MilestoneSet(desktop_first=2)
    self.feature_4.put()
    self.fe_4_stages_dict[460][0].put()

    actual = feature_helpers.get_in_milestone(
        milestone=1, show_unlisted=True)
    self.assertEqual(
        1,
        len(actual['Removed']))

  def test_get_in_milestone__no_enterprise(self):
    """Enterprise features are not shown in the roadmap."""
    # This is not included because STAGE_ENT_ROLLOUT is not considered.
    self.feature_1.impl_status_chrome = ENABLED_BY_DEFAULT
    rollout_stage = Stage(
        feature_id=self.feature_1.key.integer_id(),
        stage_type=STAGE_ENT_ROLLOUT,
        milestones=MilestoneSet(desktop_first=1),
        rollout_milestone=1)
    self.feature_1.put()
    rollout_stage.put()

    # This one is included because it uses a stage that is considered.
    self.feature_2.impl_status_chrome = REMOVED
    self.fe_2_stages_dict[260][0].milestones = MilestoneSet(desktop_first=1)
    self.feature_2.put()
    self.fe_2_stages_dict[260][0].put()

    actual = feature_helpers.get_in_milestone(milestone=1)
    expected_fe_2 = converters.feature_entry_to_json_basic(self.feature_2)
    expected = {
        'Browser Intervention': [],
        'Deprecated': [],
        'Enabled by default': [],
        'In developer trial (Behind a flag)': [],
        'Origin trial': [],
        'Removed': [expected_fe_2]}
    self.assertEqual(expected, actual)

  def test_get_in_milestone__cached(self):
    """If there is something in the cache, we use it."""
    cache_key = '%s|%s|%s' % (
        FeatureEntry.DEFAULT_CACHE_KEY, 'milestone', 1)
    cached_test_feature = {'test': [{'name': 'test_feature', 'unlisted': False}]}
    rediscache.set(cache_key, cached_test_feature)

    actual = feature_helpers.get_in_milestone(milestone=1)
    self.assertEqual(
        cached_test_feature,
        actual)

  def test_get_in_milestone__non_enterprise_features(self):
    """We can retrieve a list of features."""
    self.fe_1_stages_dict[160][0].milestones = MilestoneSet(desktop_first=1)
    self.fe_1_stages_dict[160][0].put()
    self.fe_2_stages_dict[260][0].milestones = MilestoneSet(desktop_last=2)
    self.fe_2_stages_dict[260][0].put()
    self.fe_3_stages_dict[360][0].milestones = MilestoneSet(ios_first=3)
    self.fe_3_stages_dict[360][0].put()
    self.fe_4_stages_dict[460][0].milestones = MilestoneSet(ios_last=4)
    self.fe_4_stages_dict[460][0].put()

    cache_key = '%s|%s|%s' % (
        FeatureEntry.DEFAULT_CACHE_KEY, 'release_notes_milestone', 1)

    # There is no breaking change
    features = feature_helpers.get_features_in_release_notes(milestone=1)
    self.assertEqual(0, len(features))
    cached_result = rediscache.get(cache_key)
    rediscache.delete(cache_key)
    self.assertEqual(cached_result, features)
    
    # Features 1, 2, 3 and 4 are breaking changes
    self.feature_1.enterprise_impact = ENTERPRISE_IMPACT_LOW
    self.feature_1.put()
    self.feature_2.enterprise_impact = ENTERPRISE_IMPACT_MEDIUM
    self.feature_2.put()
    self.feature_3.enterprise_impact = ENTERPRISE_IMPACT_HIGH
    self.feature_3.put()
    self.feature_4.enterprise_impact = ENTERPRISE_IMPACT_LOW
    self.feature_4.put()

    features = feature_helpers.get_features_in_release_notes(milestone=1)
    self.assertEqual(4, len(features))
    self.assertEqual(
      ['feature a', 'feature b', 'feature c', 'feature d'],
      [f['name'] for f in features])
    cached_result = rediscache.get(cache_key)
    rediscache.delete(cache_key)
    self.assertEqual(cached_result, features)
    
    cache_key = '%s|%s|%s' % (
        FeatureEntry.DEFAULT_CACHE_KEY, 'release_notes_milestone', 3)
    features = feature_helpers.get_features_in_release_notes(milestone=3)
    self.assertEqual(2, len(features))
    self.assertEqual(
      ['feature c', 'feature d'],
      [f['name'] for f in features])
    cached_result = rediscache.get(cache_key)
    rediscache.delete(cache_key)
    self.assertEqual(cached_result, features)

    # Features 1, 2, 3 are breaking changes
    # only feature 1, 2 and 4 are planned to be released
    self.feature_4.enterprise_impact = ENTERPRISE_IMPACT_NONE
    self.feature_4.put()
    self.fe_3_stages_dict[360][0].milestones = MilestoneSet()
    self.fe_3_stages_dict[360][0].put()

    features = feature_helpers.get_features_in_release_notes(milestone=3)
    self.assertEqual(0, len(features))
    cached_result = rediscache.get(cache_key)
    rediscache.delete(cache_key)
    self.assertEqual(cached_result, features)

    cache_key = '%s|%s|%s' % (
        FeatureEntry.DEFAULT_CACHE_KEY, 'release_notes_milestone', 1)
    features = feature_helpers.get_features_in_release_notes(milestone=1)
    self.assertEqual(2, len(features))
    self.assertEqual(
      ['feature a', 'feature b'],
      [f['name'] for f in features])
    cached_result = rediscache.get(cache_key)
    rediscache.delete(cache_key)
    self.assertEqual(cached_result, features)

    # Enterprise features are included
    rollout_stage = Stage(
        feature_id=self.feature_4.key.integer_id(),
        stage_type=STAGE_ENT_ROLLOUT,
        rollout_milestone=1)
    rollout_stage.put()
    self.feature_4.feature_type = 4
    self.feature_4.put()

    features = feature_helpers.get_features_in_release_notes(milestone=1)
    self.assertEqual(3, len(features))
    self.assertEqual(
      ['feature a', 'feature b', 'feature d'],
      [f['name'] for f in features])
    cached_result = rediscache.get(cache_key)
    rediscache.delete(cache_key)
    self.assertEqual(cached_result, features)

    # Deleted features are not included
    self.feature_4.deleted = True
    self.feature_4.put()
    features = feature_helpers.get_features_in_release_notes(milestone=1)
    self.assertEqual(2, len(features))
    self.assertEqual(
      ['feature a', 'feature b'],
      [f['name'] for f in features])
    cached_result = rediscache.get(cache_key)
    rediscache.delete(cache_key)
    self.assertEqual(cached_result, features)

