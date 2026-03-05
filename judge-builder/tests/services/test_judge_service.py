"""Unit tests for JudgeService."""

import unittest
from unittest import TestCase
from unittest.mock import patch

from server.models import JudgeCreateRequest, JudgeResponse
from server.services.judge_service import JudgeService


class TestJudgeService(TestCase):
    """Test cases for JudgeService class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.service = JudgeService()

    def test_judge_service_initialization(self):
        """Test JudgeService initializes with empty storage."""
        self.assertIsInstance(self.service._judges, dict)
        self.assertIsInstance(self.service._versions, dict)
        self.assertEqual(len(self.service._judges), 0)
        self.assertEqual(len(self.service._versions), 0)

    def test_create_judge_basic(self):
        """Test basic judge creation."""
        request = JudgeCreateRequest(
            name='Quality Judge', instruction='Check if response is helpful', experiment_id='exp123'
        )

        response = self.service.create_judge(request)

        # Verify response structure
        self.assertIsInstance(response, JudgeResponse)
        self.assertEqual(response.name, 'Quality Judge')
        self.assertEqual(response.instruction, 'Check if response is helpful')
        self.assertEqual(response.experiment_id, 'exp123')
        self.assertEqual(response.version, 1)
        self.assertIsNotNone(response.id)

        # Verify internal storage
        self.assertEqual(len(self.service._judges), 1)
        self.assertIn(response.id, self.service._judges)
        self.assertIn(response.id, self.service._versions)
        self.assertIn(1, self.service._versions[response.id])

    def test_create_judge_without_sme_emails(self):
        """Test judge creation without SME emails."""
        request = JudgeCreateRequest(
            name='Simple Judge', instruction='Basic evaluation', experiment_id='exp456'
        )

        response = self.service.create_judge(request)

        self.assertEqual(response.name, 'Simple Judge')
        self.assertEqual(response.instruction, 'Basic evaluation')
        self.assertEqual(response.experiment_id, 'exp456')

    def test_create_multiple_judges(self):
        """Test creating multiple judges."""
        request1 = JudgeCreateRequest(
            name='Judge 1', instruction='First judge', experiment_id='exp1'
        )
        request2 = JudgeCreateRequest(
            name='Judge 2', instruction='Second judge', experiment_id='exp2'
        )

        response1 = self.service.create_judge(request1)
        response2 = self.service.create_judge(request2)

        # Verify both judges are stored
        self.assertEqual(len(self.service._judges), 2)
        self.assertNotEqual(response1.id, response2.id)
        self.assertIn(response1.id, self.service._judges)
        self.assertIn(response2.id, self.service._judges)

    def test_get_judge_existing(self):
        """Test getting an existing judge."""
        # Create a judge first
        request = JudgeCreateRequest(
            name='Test Judge', instruction='Test instruction', experiment_id='exp123'
        )
        created_response = self.service.create_judge(request)

        # Retrieve the judge
        retrieved_response = self.service.get_judge(created_response.id)

        self.assertIsNotNone(retrieved_response)
        self.assertEqual(retrieved_response.id, created_response.id)
        self.assertEqual(retrieved_response.name, created_response.name)
        self.assertEqual(retrieved_response.instruction, created_response.instruction)
        self.assertEqual(retrieved_response.experiment_id, created_response.experiment_id)
        self.assertEqual(retrieved_response.version, created_response.version)

    def test_get_judge_nonexistent(self):
        """Test getting a nonexistent judge."""
        response = self.service.get_judge('nonexistent_id')
        self.assertIsNone(response)

    def test_list_judges_empty(self):
        """Test listing judges when none exist."""
        judges = self.service.list_judges()
        self.assertEqual(judges, [])

    def test_list_judges_with_data(self):
        """Test listing judges with multiple judges."""
        # Create multiple judges
        request1 = JudgeCreateRequest(
            name='Judge A', instruction='Instruction A', experiment_id='expA'
        )
        request2 = JudgeCreateRequest(
            name='Judge B', instruction='Instruction B', experiment_id='expB'
        )

        response1 = self.service.create_judge(request1)
        response2 = self.service.create_judge(request2)

        # List judges
        judges = self.service.list_judges()

        self.assertEqual(len(judges), 2)
        judge_ids = [j.id for j in judges]
        self.assertIn(response1.id, judge_ids)
        self.assertIn(response2.id, judge_ids)

    def test_delete_judge_existing(self):
        """Test deleting an existing judge."""
        # Create a judge first
        request = JudgeCreateRequest(
            name='Delete Me Judge', instruction='To be deleted', experiment_id='exp123'
        )
        response = self.service.create_judge(request)

        # Verify judge exists
        self.assertIn(response.id, self.service._judges)
        self.assertIn(response.id, self.service._versions)

        # Delete the judge
        result = self.service.delete_judge(response.id)

        self.assertTrue(result)
        self.assertNotIn(response.id, self.service._judges)
        self.assertNotIn(response.id, self.service._versions)

    def test_delete_judge_nonexistent(self):
        """Test deleting a nonexistent judge."""
        result = self.service.delete_judge('nonexistent_id')
        self.assertFalse(result)

    def test_delete_judge_removes_from_both_storages(self):
        """Test that deleting a judge removes it from both _judges and _versions."""
        # Create a judge
        request = JudgeCreateRequest(
            name='Storage Test Judge', instruction='Test storage removal', experiment_id='exp123'
        )
        response = self.service.create_judge(request)

        # Verify it's in both storages
        self.assertIn(response.id, self.service._judges)
        self.assertIn(response.id, self.service._versions)

        # Delete the judge
        self.service.delete_judge(response.id)

        # Verify it's removed from both storages
        self.assertNotIn(response.id, self.service._judges)
        self.assertNotIn(response.id, self.service._versions)

    def test_create_new_version_basic(self):
        """Test creating a new version of an existing judge."""
        # Create original judge
        request = JudgeCreateRequest(
            name='Versioned Judge', instruction='Original instruction', experiment_id='exp123'
        )
        original_response = self.service.create_judge(request)

        # Create new version
        aligned_instruction = 'Optimized instruction from alignment'
        new_version_response = self.service.create_new_version(
            original_response.id, aligned_instruction
        )

        # Verify new version
        self.assertEqual(new_version_response.id, original_response.id)  # Same ID
        self.assertEqual(new_version_response.name, original_response.name)  # Same name
        self.assertEqual(
            new_version_response.instruction, original_response.instruction
        )  # Original user instruction preserved
        self.assertEqual(new_version_response.version, 2)  # Incremented version

        # Verify version history
        self.assertIn(original_response.id, self.service._versions)
        self.assertIn(1, self.service._versions[original_response.id])  # Original version
        self.assertIn(2, self.service._versions[original_response.id])  # New version

        # Verify current judge is the new version
        current_judge = self.service._judges[original_response.id]
        self.assertEqual(current_judge.version, 2)
        self.assertEqual(current_judge.system_instructions, aligned_instruction)

    def test_create_new_version_multiple(self):
        """Test creating multiple versions of a judge."""
        # Create original judge
        request = JudgeCreateRequest(
            name='Multi-Version Judge', instruction='Original instruction', experiment_id='exp123'
        )
        response = self.service.create_judge(request)

        # Create version 2
        v2_response = self.service.create_new_version(response.id, 'Second version instruction')

        # Create version 3
        v3_response = self.service.create_new_version(response.id, 'Third version instruction')

        # Verify versions
        self.assertEqual(v2_response.version, 2)
        self.assertEqual(v3_response.version, 3)

        # Verify version history has all versions
        versions = self.service._versions[response.id]
        self.assertEqual(len(versions), 3)
        self.assertIn(1, versions)
        self.assertIn(2, versions)
        self.assertIn(3, versions)

        # Verify current judge is latest version
        current_judge = self.service._judges[response.id]
        self.assertEqual(current_judge.version, 3)
        self.assertEqual(current_judge.system_instructions, 'Third version instruction')

    def test_create_new_version_nonexistent_judge(self):
        """Test creating new version for nonexistent judge raises error."""
        with self.assertRaises(ValueError) as context:
            self.service.create_new_version('nonexistent_id', 'Some instruction')

        self.assertIn('Judge nonexistent_id not found', str(context.exception))

    def test_create_new_version_preserves_user_instructions(self):
        """Test that new version preserves original user instructions."""
        # Create original judge
        request = JudgeCreateRequest(
            name='User Instruction Test',
            instruction='Original user instruction',
            experiment_id='exp123',
        )
        response = self.service.create_judge(request)

        # Create new version with different system instruction
        new_version_response = self.service.create_new_version(
            response.id, 'Completely different system instruction'
        )

        # User instruction should be preserved
        self.assertEqual(new_version_response.instruction, 'Original user instruction')

        # System instruction should be updated (internal check)
        current_judge = self.service._judges[response.id]
        self.assertEqual(
            current_judge.system_instructions, 'Completely different system instruction'
        )
        self.assertEqual(current_judge.user_instructions, 'Original user instruction')

    def test_judge_to_response_conversion(self):
        """Test _judge_to_response helper method."""
        # Create a judge
        request = JudgeCreateRequest(
            name='Conversion Test Judge', instruction='Test conversion', experiment_id='exp123'
        )
        response = self.service.create_judge(request)

        # Get the internal judge object
        judge = self.service._judges[response.id]

        # Convert to response
        converted_response = self.service._judge_to_response(judge)

        # Verify conversion
        self.assertEqual(converted_response.id, judge.id)
        self.assertEqual(converted_response.name, judge.name)
        self.assertEqual(
            converted_response.instruction, judge.user_instructions
        )  # Uses user_instructions
        self.assertEqual(converted_response.experiment_id, judge.experiment_id)
        self.assertEqual(converted_response.version, judge.version)

    @patch('server.services.judge_service.logger')
    def test_logging_create_judge(self, mock_logger):
        """Test that create_judge logs appropriately."""
        request = JudgeCreateRequest(
            name='Logging Test Judge', instruction='Test logging', experiment_id='exp123'
        )

        response = self.service.create_judge(request)

        # Verify logging calls
        mock_logger.info.assert_any_call('Creating judge: Logging Test Judge')
        mock_logger.info.assert_any_call(
            f"Created judge {response.id} with name 'Logging Test Judge'"
        )

    @patch('server.services.judge_service.logger')
    def test_logging_get_judge(self, mock_logger):
        """Test that get_judge logs appropriately."""
        # Test existing judge
        request = JudgeCreateRequest(
            name='Get Test Judge', instruction='Test get', experiment_id='exp123'
        )
        response = self.service.create_judge(request)

        # Reset mock to clear create_judge logs
        mock_logger.reset_mock()

        self.service.get_judge(response.id)
        mock_logger.info.assert_called_with(f'Retrieved judge {response.id}')

        # Test nonexistent judge
        mock_logger.reset_mock()
        self.service.get_judge('nonexistent')
        mock_logger.warning.assert_called_with('Judge nonexistent not found')

    @patch('server.services.judge_service.logger')
    def test_logging_delete_judge(self, mock_logger):
        """Test that delete_judge logs appropriately."""
        # Create judge
        request = JudgeCreateRequest(
            name='Delete Test Judge', instruction='Test delete', experiment_id='exp123'
        )
        response = self.service.create_judge(request)

        # Reset mock to clear create_judge logs
        mock_logger.reset_mock()

        # Delete existing judge
        self.service.delete_judge(response.id)
        mock_logger.info.assert_called_with(f'Deleting judge {response.id} (Delete Test Judge)')

        # Delete nonexistent judge
        mock_logger.reset_mock()
        self.service.delete_judge('nonexistent')
        mock_logger.warning.assert_called_with('Cannot delete judge nonexistent: not found')


if __name__ == '__main__':
    unittest.main()
