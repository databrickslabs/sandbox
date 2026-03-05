"""Test JudgeResponse with schema_info caching."""

import unittest
from server.models import JudgeResponse, SchemaInfo


class TestJudgeResponseSchema(unittest.TestCase):
    """Test JudgeResponse includes cached schema information."""

    def test_judge_response_with_schema_info(self):
        """Test JudgeResponse creation with schema_info."""
        schema_info = SchemaInfo(
            is_binary=True,
            options=['Pass', 'Fail']
        )
        
        judge = JudgeResponse(
            id='test-judge-123',
            name='Test Judge',
            instruction='Return pass if good, fail if bad.',
            experiment_id='exp123',
            version=1,
            labeling_run_id=None,
            schema_info=schema_info
        )
        
        self.assertEqual(judge.id, 'test-judge-123')
        self.assertEqual(judge.name, 'Test Judge')
        self.assertEqual(judge.version, 1)
        self.assertIsNotNone(judge.schema_info)
        self.assertTrue(judge.schema_info.is_binary)
        self.assertEqual(judge.schema_info.options, ['Pass', 'Fail'])

    def test_judge_response_without_schema_info(self):
        """Test JudgeResponse creation without schema_info (backward compatibility)."""
        judge = JudgeResponse(
            id='test-judge-456',
            name='Legacy Judge',
            instruction='Evaluate this response.',
            experiment_id='exp456',
            version=1,
            labeling_run_id=None,
            schema_info=None
        )
        
        self.assertEqual(judge.id, 'test-judge-456')
        self.assertEqual(judge.name, 'Legacy Judge')
        self.assertIsNone(judge.schema_info)

    def test_judge_response_numeric_schema(self):
        """Test JudgeResponse with numeric schema."""
        schema_info = SchemaInfo(
            is_binary=False,
            options=['1', '2', '3', '4', '5']
        )
        
        judge = JudgeResponse(
            id='numeric-judge-789',
            name='Numeric Judge',
            instruction='Rate from 1 to 5.',
            experiment_id='exp789',
            version=2,
            labeling_run_id='run123',
            schema_info=schema_info
        )
        
        self.assertFalse(judge.schema_info.is_binary)
        self.assertEqual(len(judge.schema_info.options), 5)


if __name__ == '__main__':
    unittest.main()