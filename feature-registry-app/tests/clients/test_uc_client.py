import unittest
from unittest.mock import patch, MagicMock

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from src.clients.uc_client import UcClient


class TestUcClient(unittest.TestCase):
    
    def setUp(self):
        # Create a patch for the WorkspaceClient
        self.workspace_client_patcher = patch('src.clients.uc_client.WorkspaceClient')
        self.mock_workspace_client_class = self.workspace_client_patcher.start()
        
        # Create mock WorkspaceClient instance
        self.mock_workspace_client = MagicMock()
        self.mock_workspace_client_class.return_value = self.mock_workspace_client
        
        # Create mock catalog, schema, table, and function resources
        self.mock_catalogs = MagicMock()
        self.mock_schemas = MagicMock()
        self.mock_tables = MagicMock()
        self.mock_functions = MagicMock()
        
        # Assign mocks to the WorkspaceClient instance
        self.mock_workspace_client.catalogs = self.mock_catalogs
        self.mock_workspace_client.schemas = self.mock_schemas
        self.mock_workspace_client.tables = self.mock_tables
        self.mock_workspace_client.functions = self.mock_functions

        self.user_access_token = "test_user_access_token"
        
        # Create UcClient instance
        self.uc_client = UcClient(self.user_access_token)
    
    def tearDown(self):
        self.workspace_client_patcher.stop()
    
    def test_init(self):
        """Test that UcClient initializes with a WorkspaceClient."""
        # Verify that WorkspaceClient was called
        self.mock_workspace_client_class.assert_called_with(token=self.user_access_token, auth_type="pat")
        # Verify that the client was assigned
        self.assertEqual(self.uc_client.w, self.mock_workspace_client)
    
    def test_get_catalogs(self):
        """Test that get_catalogs calls the WorkspaceClient.catalogs.list method with the correct parameters."""
        # Setup mock return value
        mock_catalog1 = MagicMock(name='catalog1')
        mock_catalog2 = MagicMock(name='catalog2')
        mock_catalogs_list = [mock_catalog1, mock_catalog2]
        self.mock_catalogs.list.return_value = mock_catalogs_list
        
        # Call the method
        result = self.uc_client.get_catalogs()
        
        # Verify the result
        self.assertEqual(result, mock_catalogs_list)
        self.mock_catalogs.list.assert_called_once_with(include_browse=False)
    
    def test_get_schemas(self):
        """Test that get_schemas calls the WorkspaceClient.schemas.list method with the correct parameters."""
        # Setup mock return value
        mock_schema1 = MagicMock(name='schema1')
        mock_schema2 = MagicMock(name='schema2')
        mock_schemas_list = [mock_schema1, mock_schema2]
        self.mock_schemas.list.return_value = mock_schemas_list
        
        # Call the method
        result = self.uc_client.get_schemas('test_catalog')
        
        # Verify the result
        self.assertEqual(result, mock_schemas_list)
        self.mock_schemas.list.assert_called_once_with(catalog_name='test_catalog')
    
    def test_get_tables(self):
        """Test that get_tables calls the WorkspaceClient.tables.list method with the correct parameters."""
        # Setup mock return value
        mock_table1 = MagicMock(name='table1')
        mock_table2 = MagicMock(name='table2')
        mock_tables_list = [mock_table1, mock_table2]
        self.mock_tables.list.return_value = mock_tables_list
        
        # Call the method
        result = self.uc_client.get_tables('test_catalog', 'test_schema')
        
        # Verify the result
        self.assertEqual(result, mock_tables_list)
        self.mock_tables.list.assert_called_once_with(
            catalog_name='test_catalog', 
            schema_name='test_schema'
        )
    
    def test_get_table(self):
        """Test that get_table calls the WorkspaceClient.tables.get method with the correct parameters."""
        # Setup mock return value
        mock_table = MagicMock(name='table1')
        self.mock_tables.get.return_value = mock_table
        
        # Call the method
        result = self.uc_client.get_table('test_catalog.test_schema.test_table')
        
        # Verify the result
        self.assertEqual(result, mock_table)
        self.mock_tables.get.assert_called_once_with(
            full_name='test_catalog.test_schema.test_table'
        )
    
    def test_get_functions(self):
        """Test that get_functions calls the WorkspaceClient.functions.list method with the correct parameters."""
        # Setup mock return value
        mock_function1 = MagicMock(name='function1')
        mock_function2 = MagicMock(name='function2')
        mock_functions_list = [mock_function1, mock_function2]
        self.mock_functions.list.return_value = mock_functions_list
        
        # Call the method
        result = self.uc_client.get_functions('test_catalog', 'test_schema')
        
        # Verify the result
        self.assertEqual(result, mock_functions_list)
        self.mock_functions.list.assert_called_once_with(
            catalog_name='test_catalog', 
            schema_name='test_schema'
        )
    
    def test_get_function(self):
        """Test that get_function calls the WorkspaceClient.functions.get method with the correct parameters."""
        # Setup mock return value
        mock_function = MagicMock(name='function1')
        self.mock_functions.get.return_value = mock_function
        
        # Call the method
        result = self.uc_client.get_function('test_catalog.test_schema.test_function')
        
        # Verify the result
        self.assertEqual(result, mock_function)
        self.mock_functions.get.assert_called_once_with(
            name='test_catalog.test_schema.test_function'
        )


if __name__ == '__main__':
    unittest.main()
