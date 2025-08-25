import unittest
from unittest.mock import patch, MagicMock

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath('./src'))

from src.entities.tables import Table


class TestTable(unittest.TestCase):
    
    def setUp(self):
        # Create a patch for the TableInfo class
        self.table_info_patcher = patch('entities.tables.sdk.service.catalog.TableInfo')
        self.mock_table_info_class = self.table_info_patcher.start()
        
        # Create mock uc_table with the proper class type
        self.mock_uc_table = MagicMock()
        self.mock_uc_table.full_name = 'catalog1.schema1.table1'
        self.mock_uc_table.name = 'table1'
        self.mock_uc_table.catalog_name = 'catalog1'
        self.mock_uc_table.schema_name = 'schema1'
        
        # Configure the mock TableInfo class to recognize our mock as an instance
        self.mock_table_info_class.side_effect = lambda **kwargs: self.mock_uc_table
        
        # Create table
        self.table = Table(uc_table=self.mock_uc_table)
    
    def tearDown(self):
        self.table_info_patcher.stop()
    
    def test_full_name(self):
        """Test that full_name returns the correct full name from the uc_table."""
        result = self.table.full_name()
        
        # Verify the result
        self.assertEqual(result, 'catalog1.schema1.table1')
    
    def test_name(self):
        """Test that name returns the correct table name from the uc_table."""
        result = self.table.name()
        
        # Verify the result
        self.assertEqual(result, 'table1')
    
    def test_schema(self):
        """Test that schema returns the correct schema name from the uc_table."""
        result = self.table.schema()
        
        # Verify the result
        self.assertEqual(result, 'schema1')
    
    def test_components(self):
        """Test that components returns a tuple with catalog, schema, and table names."""
        result = self.table.components()
        
        # Verify the result
        self.assertEqual(result, ('catalog1', 'schema1', 'table1'))


if __name__ == '__main__':
    unittest.main()
