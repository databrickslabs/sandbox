"""Unit tests for InstructionJudge implementation."""

import unittest
from unittest import TestCase
from unittest.mock import Mock, patch

from server.judges.instruction_judge import InstructionJudge


class TestInstructionJudge(TestCase):
    """Test cases for InstructionJudge class."""

    def test_judge_creation_and_basic_properties(self):
        """Test that judge can be created with proper configuration."""
        judge = InstructionJudge(
            name='Quality Judge', 
            user_instructions='Check if {{ inputs }} is helpful and {{ outputs }} is accurate',
            experiment_id='exp456'
        )

        # Test basic judge properties are set correctly
        self.assertEqual(judge.name, 'Quality Judge')
        self.assertEqual(judge.user_instructions, 'Check if {{ inputs }} is helpful and {{ outputs }} is accurate')
        self.assertEqual(judge.experiment_id, 'exp456')
        self.assertEqual(judge.version, 1)
        self.assertIsNotNone(judge.id)
        self.assertIsNotNone(judge.scorer_func)

    def test_evaluate_returns_feedback_with_version(self):
        """Test that evaluate method returns feedback with version metadata."""
        judge = InstructionJudge(name='Test Judge', user_instructions='Evaluate {{ inputs }} and {{ outputs }}')
        
        # Mock scorer function behavior
        mock_feedback = Mock()
        mock_feedback.metadata = {'existing': 'data'}
        judge.scorer_func = Mock(return_value=mock_feedback)

        inputs = {'request': 'Test question'}
        outputs = {'response': 'Test answer'}
        trace = Mock()

        result = judge.evaluate(inputs, outputs, trace)

        # Test that evaluation returns feedback with correct version
        self.assertIsNotNone(result)
        self.assertEqual(result.metadata['version'], '1')
        
    def test_evaluate_handles_missing_metadata(self):
        """Test evaluate gracefully handles feedback without metadata."""
        judge = InstructionJudge(name='Test Judge', user_instructions='Evaluate {{ inputs }} and {{ outputs }}')
        
        # Mock scorer function behavior with no metadata
        mock_feedback = Mock()
        mock_feedback.metadata = None
        judge.scorer_func = Mock(return_value=mock_feedback)

        result = judge.evaluate({'input': 'test'}, {'output': 'test'})

        # Should add version metadata even when none exists
        self.assertEqual(result.metadata, {'version': '1'})

    def test_scorer_registration_success(self):
        """Test successful scorer registration."""
        judge = InstructionJudge(
            name='Register Test Judge',
            user_instructions='Rate {{ inputs }} and {{ outputs }}',
            experiment_id='exp123',
        )
        
        # Replace scorer_func with a mock that has register method
        mock_scorer = Mock()
        mock_registered = Mock()
        mock_scorer.register.return_value = mock_registered
        judge.scorer_func = mock_scorer
        
        result = judge.register_scorer()

        # Should return registered scorer
        self.assertEqual(result, mock_registered)
        mock_scorer.register.assert_called_once()

    def test_scorer_registration_handles_failure(self):
        """Test scorer registration gracefully handles failures."""
        judge = InstructionJudge(name='Test Judge', user_instructions='Rate {{ inputs }} and {{ outputs }}')
        
        # Replace scorer_func with a mock that fails registration
        mock_scorer = Mock()
        mock_scorer.register.side_effect = Exception("Registration failed")
        judge.scorer_func = mock_scorer
        
        result = judge.register_scorer()

        # Should handle error gracefully and return None
        self.assertIsNone(result)

    def test_judge_optimization_success(self):
        """Test successful judge optimization with training data."""
        judge = InstructionJudge(name='Test Judge', user_instructions='Rate {{ inputs }} and {{ outputs }}')
        
        # Replace scorer_func with a mock that has align method
        mock_scorer = Mock()
        mock_aligned_judge = Mock()
        mock_scorer.align.return_value = mock_aligned_judge
        judge.scorer_func = mock_scorer
        
        # Provide sufficient training traces
        traces = [Mock() for _ in range(12)]
        result = judge.optimize(traces)

        # Should return success and update judge
        self.assertTrue(result)
        self.assertEqual(judge.scorer_func, mock_aligned_judge)
        mock_scorer.align.assert_called_once_with(traces=traces)

    def test_judge_optimization_handles_failure(self):
        """Test judge optimization handles alignment failures."""
        judge = InstructionJudge(name='Test Judge', user_instructions='Rate {{ inputs }} and {{ outputs }}')
        
        # Replace scorer_func with a mock that fails alignment
        mock_scorer = Mock()
        mock_scorer.align.side_effect = Exception("Alignment failed")
        judge.scorer_func = mock_scorer
        
        traces = [Mock() for _ in range(12)]
        result = judge.optimize(traces)

        # Should handle failure gracefully
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()