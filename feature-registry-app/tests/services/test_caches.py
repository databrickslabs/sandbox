import unittest
from unittest.mock import patch, MagicMock

import sys
import os

from .mock_session_state import SessionStateMock

# Tell where to source included imports by adding `./src` in import path
# For example `FeatureFilters` will import Feature from entities.features package.
sys.path.insert(0, os.path.abspath('./src'))

# Import the constant we want to test
from src.services.caches import INTERNAL_SCHEMAS


class TestInternalSchemas(unittest.TestCase):
    """Test the INTERNAL_SCHEMAS constant from CachedUcData."""

    def test_internal_schemas_contains_information_schema(self):
        """Test that INTERNAL_SCHEMAS contains 'information_schema'."""
        self.assertIn('information_schema', INTERNAL_SCHEMAS)

    def test_internal_schemas_is_a_set(self):
        """Test that INTERNAL_SCHEMAS is a set."""
        self.assertIsInstance(INTERNAL_SCHEMAS, set)


class TestCachedUcData(unittest.TestCase):
    """
    Tests for the CachedUcData class.

    Note: Due to the complex dependencies of this class, we're testing
    specific functionality in isolation rather than the entire class.
    """

    def setUp(self):
        # Import the class after mocking its dependencies
        from src.services.caches import CachedUcData
        self.CachedUcData = CachedUcData

        # Mock the streamlit session state
        self.mock_session_state = SessionStateMock()
        self.patcher = patch('src.services.caches.st.session_state', self.mock_session_state)
        self.mock_st_session_state = self.patcher.start()

        # Mock the streamlit cache_data decorator
        self.cache_data_patcher = patch('src.services.caches.st.cache_data')
        self.mock_cache_data = self.cache_data_patcher.start()
        # Make the cache_data decorator just return the function unchanged
        self.mock_cache_data.side_effect = lambda ttl: lambda func: func

    def tearDown(self):
        self.patcher.stop()
        self.cache_data_patcher.stop()

    def test_init_creates_uc_client_if_not_exists(self):
        """Test that __init__ creates a UcClient if it doesn't exist in session state."""
        # Setup: ensure uc_client is not in session state
        self.mock_session_state.clear()

        # Create a mock UcClient
        mock_uc_client_instance = MagicMock()
        with patch('src.services.caches.UcClient') as mock_uc_client:
            mock_uc_client.return_value = mock_uc_client_instance

            # Act: initialize CachedUcData
            cached_data = self.CachedUcData()

            # Assert: UcClient was created and stored in session state
            mock_uc_client.assert_called_once()
        self.assertIs(self.mock_session_state['uc_client'], mock_uc_client_instance)

    def test_init_reuses_existing_uc_client(self):
        """Test that __init__ reuses an existing UcClient if it exists in session state."""
        # Setup: put a mock UcClient in session state
        existing_client = MagicMock()
        self.mock_session_state['uc_client'] = existing_client

        with patch('src.services.caches.UcClient') as mock_uc_client:
            # Act: initialize CachedUcData
            cached_data = self.CachedUcData()

            # Assert: UcClient was not created again
            mock_uc_client.assert_not_called()

        # Assert: verify that the uc_client in session state has not changed
        self.assertIs(self.mock_session_state['uc_client'], existing_client)

    def test_get_tables_calls_uc_client(self):
        """Test that get_tables calls the UcClient's get_tables method with the correct parameters."""
        # Setup: put a mock UcClient in session state
        mock_uc_client_instance = MagicMock()
        self.mock_session_state['uc_client'] = mock_uc_client_instance

        # Setup mock return value for get_tables
        uc_table_1, uc_table_2 = MagicMock(), MagicMock()
        mock_uc_client_instance.get_tables.return_value = [uc_table_1, uc_table_2]

        result = self.CachedUcData.get_tables('test_catalog', 'test_schema')

        # Assert: UcClient's get_tables was called with correct parameters
        mock_uc_client_instance.get_tables.assert_called_once_with(
            catalog_name='test_catalog',
            schema_name='test_schema'
        )

        # Assert: CachedUcData.get_tables returned the list of Table instances
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].uc_table, uc_table_1)
        self.assertEqual(result[1].uc_table, uc_table_2)

    def test_get_catalogs_returns_catalog_names(self):
        """Test that get_catalogs returns a list of catalog names."""
        # Setup: put a mock UcClient in session state
        mock_uc_client_instance = MagicMock()
        self.mock_session_state['uc_client'] = mock_uc_client_instance

        # Setup mock return value for get_catalogs
        mock_catalog1 = MagicMock()
        mock_catalog1.name = 'catalog1'
        mock_catalog2 = MagicMock()
        mock_catalog2.name = 'catalog2'
        mock_uc_client_instance.get_catalogs.return_value = [mock_catalog1, mock_catalog2]

        # Act: call get_catalogs
        result = self.CachedUcData.get_catalogs()

        # Assert: UcClient's get_catalogs was called
        mock_uc_client_instance.get_catalogs.assert_called_once()

        # Assert: get_catalogs returned the list of catalog names
        self.assertEqual(result, ['catalog1', 'catalog2'])

    def test_get_schemas_filters_internal_schemas(self):
        """Test that get_schemas filters out internal schemas."""
        # Setup: put a mock UcClient in session state
        mock_uc_client_instance = MagicMock()
        self.mock_session_state['uc_client'] = mock_uc_client_instance

        # Setup mock return value for get_schemas
        mock_schema1 = MagicMock()
        mock_schema1.name = 'schema1'
        mock_schema2 = MagicMock()
        mock_schema2.name = 'schema2'
        mock_info_schema = MagicMock()
        mock_info_schema.name = 'information_schema'
        mock_uc_client_instance.get_schemas.return_value = [mock_schema1, mock_schema2, mock_info_schema]

        # Act: call get_schemas
        result = self.CachedUcData.get_schemas('test_catalog')

        # Assert: UcClient's get_schemas was called with correct parameters
        mock_uc_client_instance.get_schemas.assert_called_once_with(catalog_name='test_catalog')

        # Assert: get_schemas returned the list of schema names, excluding information_schema
        self.assertEqual(result, ['schema1', 'schema2'])
        self.assertNotIn('information_schema', result)


if __name__ == '__main__':
    unittest.main()
