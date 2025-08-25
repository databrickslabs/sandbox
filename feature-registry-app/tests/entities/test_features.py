import unittest
from unittest.mock import patch, MagicMock

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath('./src'))

from src.entities.features import Feature, MaterializedInfo, SelectableFeature
from src.entities.tables import Table


class TestMaterializedInfo(unittest.TestCase):
    
    def test_initialization(self):
        """Test that MaterializedInfo can be initialized with the correct attributes."""
        info = MaterializedInfo(
            schema_name="schema1",
            table_name="table1",
            primary_keys=["id", "timestamp"],
            timeseries_columns=["timestamp"]
        )
        
        self.assertEqual(info.schema_name, "schema1")
        self.assertEqual(info.table_name, "table1")
        self.assertEqual(info.primary_keys, ["id", "timestamp"])
        self.assertEqual(info.timeseries_columns, ["timestamp"])


class TestFeature(unittest.TestCase):
    
    def setUp(self):
        # Create a patch for the TableInfo class
        self.table_info_patcher = patch('entities.tables.sdk.service.catalog.TableInfo')
        self.mock_table_info_class = self.table_info_patcher.start()
        
        # Create mock uc_table
        self.mock_uc_table = MagicMock()
        self.mock_uc_table.full_name = 'catalog1.schema1.table1'
        self.mock_uc_table.name = 'table1'
        self.mock_uc_table.catalog_name = 'catalog1'
        self.mock_uc_table.schema_name = 'schema1'
        self.mock_uc_table.table_type.name = 'MANAGED'

        # Configure the mock TableInfo class to recognize our mock as an instance
        self.mock_table_info_class.side_effect = lambda **kwargs: self.mock_uc_table
        # The following line was added by llm agent but does not work with MagicMocks
        # ToDo: Identify the right fix
        # self.mock_table_info_class.__instancecheck__.return_value = True

        # Create mock columns
        self.mock_column1 = MagicMock()
        self.mock_column1.name = 'id'
        self.mock_column1.comment = 'Primary key'

        self.mock_column2 = MagicMock()
        self.mock_column2.name = 'feature1'
        self.mock_column2.comment = 'Feature 1 description'

        self.mock_column3 = MagicMock()
        self.mock_column3.name = 'feature2'
        self.mock_column3.comment = 'Feature 2 description'

        self.mock_uc_table.columns = [self.mock_column1, self.mock_column2, self.mock_column3]
        self.mock_uc_table.view_definition = 'SELECT * FROM table1'

        # Create mock table
        self.mock_table = Table(uc_table=self.mock_uc_table)

        # Create feature
        self.feature = Feature(name='feature1', table=self.mock_table, pks=['id'])
    
    def tearDown(self):
        self.table_info_patcher.stop()
    
    def test_get_materialized_info(self):
        """Test that get_materialized_info returns the correct MaterializedInfo object."""
        result = self.feature.get_materialized_info()
        
        # Verify the result
        self.assertIsInstance(result, MaterializedInfo)
        self.assertEqual(result.schema_name, 'schema1')
        self.assertEqual(result.table_name, 'table1')
        self.assertEqual(result.primary_keys, ['id'])
        self.assertEqual(result.timeseries_columns, [])
    
    def test_description(self):
        """Test that description returns the correct comment from the column."""
        result = self.feature.description()
        
        # Verify the result
        self.assertEqual(result, 'Feature 1 description')
        
        # Test with a feature name that doesn't match any column
        feature_unknown = Feature(name='unknown', table=self.mock_table, pks=['id'])
        self.assertEqual(feature_unknown.description(), '')
    
    def test_components(self):
        """Test that components returns the correct tuple."""
        result = self.feature.components()
        
        # Verify the result
        self.assertEqual(result, ('feature1', 'catalog1.schema1.table1', 'id'))
    
    def test_metadata(self):
        """Test that metadata returns the correct dictionary."""
        result = self.feature.metadata()
        
        # Verify the result
        self.assertEqual(result['Table Name'], 'catalog1.schema1.table1')
        self.assertEqual(result['Primary Keys'], ['id'])
        self.assertEqual(result['# of Features'], 2)  # 3 columns - 1 primary key
        self.assertEqual(result['Table Type'], 'MANAGED')
    
    def test_inputs_outputs(self):
        """Test that inputs and outputs methods return None."""
        self.assertIsNone(self.feature.inputs())
        self.assertIsNone(self.feature.outputs())
    
    def test_code(self):
        """Test that code returns the view definition from the table."""
        result = self.feature.code()
        
        # Verify the result
        self.assertEqual(result, 'SELECT * FROM table1')
    
    def test_table_name(self):
        """Test that table_name returns the full name of the table."""
        result = self.feature.table_name()
        
        # Verify the result
        self.assertEqual(result, 'catalog1.schema1.table1')
    
    def test_full_name(self):
        """Test that full_name returns the full qualified name of the feature."""
        result = self.feature.full_name()
        
        # Verify the result
        self.assertEqual(result, 'catalog1.schema1.table1.feature1')


class TestSelectableFeature(unittest.TestCase):
    def setUp(self):
        # Create a patch for the TableInfo class which is needed by Table
        self.table_info_patcher = patch('entities.tables.sdk.service.catalog.TableInfo')
        self.mock_table_info_class = self.table_info_patcher.start()

        # Create mock uc_table with necessary attributes
        self.mock_uc_table = MagicMock()
        self.mock_uc_table.full_name = 'catalog1.schema1.table1'
        self.mock_uc_table.name = 'table1'
        self.mock_uc_table.catalog_name = 'catalog1'
        self.mock_uc_table.schema_name = 'schema1'

        # Configure the mock TableInfo
        self.mock_table_info_class.side_effect = lambda **kwargs: self.mock_uc_table

        # Create an actual Table instance
        self.table = Table(uc_table=self.mock_uc_table)

        # Create an actual Feature instance
        self.feature = Feature(name='feature1', table=self.table, pks=['id'])

    def tearDown(self):
        self.table_info_patcher.stop()

    def test_initialization(self):
        """Test SelectableFeature initialization with various parameters"""
        # Test with selected=True
        selectable = SelectableFeature(feature=self.feature, selected=True)
        self.assertEqual(selectable.feature, self.feature)
        self.assertTrue(selectable.selected)

        # Test with selected=False
        selectable = SelectableFeature(feature=self.feature, selected=False)
        self.assertEqual(selectable.feature, self.feature)
        self.assertFalse(selectable.selected)

        # Test default selected value (should be False)
        selectable = SelectableFeature(feature=self.feature)
        self.assertFalse(selectable.selected)

    def test_components(self):
        """Test that components returns tuple with selection status and feature components"""
        # Test with selected=True
        selectable = SelectableFeature(feature=self.feature, selected=True)
        self.assertEqual(
            selectable.components(),
            (True, 'feature1', 'catalog1.schema1.table1', 'id')
        )

        # Test with selected=False
        selectable = SelectableFeature(feature=self.feature, selected=False)
        self.assertEqual(
            selectable.components(),
            (False, 'feature1', 'catalog1.schema1.table1', 'id')
        )


if __name__ == '__main__':
    unittest.main()
