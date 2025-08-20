import unittest
from unittest.mock import patch, MagicMock

import sys
import os

# Tell where to source included imports by adding `./src` in import path
# For example `FeatureFilters` will import Feature from entities.features package.
sys.path.insert(0, os.path.abspath('./src'))

from src.services.filters import FeatureFilters

from .mock_session_state import SessionStateMock

class TestFeatureFilters(unittest.TestCase):

    def setUp(self):
        # Mock the streamlit session state
        self.mock_session_state = SessionStateMock()
        self.patcher = patch('src.services.filters.st.session_state', self.mock_session_state)
        self.mock_st_session_state = self.patcher.start()

        # Mock streamlit rerun
        self.rerun_patcher = patch('src.services.filters.st.rerun')
        self.mock_rerun = self.rerun_patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.rerun_patcher.stop()

    def test_init_first_time(self):
        """Test initialization when filters are not in session state."""
        self.mock_session_state.clear()

        filters = FeatureFilters()

        # Check that filters were initialized
        self.assertIn('name_filter', self.mock_session_state)
        self.assertIn('table_filter', self.mock_session_state)
        self.assertIn('description_filter', self.mock_session_state)
        self.assertIn('reset_filters_on_init', self.mock_session_state)

        self.assertEqual(self.mock_session_state['name_filter'], '')
        self.assertEqual(self.mock_session_state['table_filter'], '')
        self.assertEqual(self.mock_session_state['description_filter'], '')
        self.assertEqual(self.mock_session_state['reset_filters_on_init'], False)

    def test_init_with_reset_flag(self):
        """Test initialization when reset flag is set."""
        self.mock_session_state['reset_filters_on_init'] = True
        self.mock_session_state['name_filter'] = 'old_name'
        self.mock_session_state['table_filter'] = 'old_table'
        self.mock_session_state['description_filter'] = 'old_description'

        filters = FeatureFilters()

        # Check that filters were reset
        self.assertEqual(self.mock_session_state['name_filter'], '')
        self.assertEqual(self.mock_session_state['table_filter'], '')
        self.assertEqual(self.mock_session_state['description_filter'], '')
        self.assertEqual(self.mock_session_state['reset_filters_on_init'], False)

    def test_substring_match(self):
        """Test substring matching functionality."""
        filters = FeatureFilters()

        # Test with empty needle (should always match)
        self.assertTrue(filters.substring_match('haystack', ''))

        # Test with matching substring
        self.assertTrue(filters.substring_match('haystack', 'hay'))
        self.assertTrue(filters.substring_match('haystack', 'stack'))
        self.assertTrue(filters.substring_match('haystack', 'yst'))

        # Test with non-matching substring
        self.assertFalse(filters.substring_match('haystack', 'needle'))

        # Test case insensitivity
        self.assertTrue(filters.substring_match('haystack', 'HAY'))
        self.assertTrue(filters.substring_match('HAYSTACK', 'hay'))

    def test_clear(self):
        """Test clearing filters."""
        self.mock_session_state['reset_filters_on_init'] = False

        filters = FeatureFilters()
        filters.clear()

        # Check that reset flag was set and rerun was called
        self.assertTrue(self.mock_session_state['reset_filters_on_init'])
        self.mock_rerun.assert_called_once()

    def test_enabled(self):
        """Test enabled method."""
        filters = FeatureFilters()

        # Test when all filters are empty
        self.mock_session_state['name_filter'] = ''
        self.mock_session_state['table_filter'] = ''
        self.mock_session_state['description_filter'] = ''
        self.assertFalse(filters.enabled())

        # Test when name filter is set
        self.mock_session_state['name_filter'] = 'test'
        self.assertTrue(filters.enabled())

        # Test when table filter is set
        self.mock_session_state['name_filter'] = ''
        self.mock_session_state['table_filter'] = 'test'
        self.assertTrue(filters.enabled())

        # Test when description filter is set
        self.mock_session_state['table_filter'] = ''
        self.mock_session_state['description_filter'] = 'test'
        self.assertTrue(filters.enabled())

    def test_include(self):
        """Test include method."""
        filters = FeatureFilters()

        # Create mock feature
        mock_feature = MagicMock()
        mock_feature.name = 'test_feature'
        mock_table = MagicMock()
        mock_table.name.return_value = 'test_table'
        mock_feature.table = mock_table
        mock_feature.description.return_value = 'test description'

        # Test with no filters (should include)
        self.mock_session_state['name_filter'] = ''
        self.mock_session_state['table_filter'] = ''
        self.mock_session_state['description_filter'] = ''
        self.assertTrue(filters.include(mock_feature))

        # Test with matching name filter
        self.mock_session_state['name_filter'] = 'test'
        self.assertTrue(filters.include(mock_feature))

        # Test with non-matching name filter
        self.mock_session_state['name_filter'] = 'nonexistent'
        self.assertFalse(filters.include(mock_feature))

        # Test with matching table filter
        self.mock_session_state['name_filter'] = ''
        self.mock_session_state['table_filter'] = 'test'
        self.assertTrue(filters.include(mock_feature))

        # Test with non-matching table filter
        self.mock_session_state['table_filter'] = 'nonexistent'
        self.assertFalse(filters.include(mock_feature))

        # Test with matching description filter
        self.mock_session_state['table_filter'] = ''
        self.mock_session_state['description_filter'] = 'test'
        self.assertTrue(filters.include(mock_feature))

        # Test with non-matching description filter
        self.mock_session_state['description_filter'] = 'nonexistent'
        self.assertFalse(filters.include(mock_feature))

        # Test with multiple matching filters
        self.mock_session_state['name_filter'] = 'test'
        self.mock_session_state['table_filter'] = 'test'
        self.mock_session_state['description_filter'] = 'test'
        self.assertTrue(filters.include(mock_feature))

        # Test with some matching and some non-matching filters
        self.mock_session_state['name_filter'] = 'test'
        self.mock_session_state['table_filter'] = 'nonexistent'
        self.assertFalse(filters.include(mock_feature))


if __name__ == '__main__':
    unittest.main()
