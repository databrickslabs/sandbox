"""Abstract base class for judges."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


class BaseJudge(ABC):
    """Abstract base class for all judge implementations."""

    def __init__(
        self,
        name: str,
        user_instructions: str,
        experiment_id: Optional[str] = None,
    ):
        """Initialize judge with required parameters."""
        self.id = str(uuid4())
        self.name = name
        self.user_instructions = user_instructions  # Original user instructions (for display)
        self.system_instructions = (
            user_instructions  # Current system instructions (used for evaluation, can be optimized)
        )
        self.version = 1  # Always start at version 1
        self.experiment_id = experiment_id
        self.labeling_run_id: Optional[str] = None  # MLflow run ID for labeling session

        # Create the custom scorer implementation
        self.scorer_func = self._create_scorer()

    @abstractmethod
    def _create_scorer(self) -> Callable:
        """Create the scorer function for this judge implementation."""

    @abstractmethod
    def evaluate(self, inputs: Dict[str, Any], outputs: Dict[str, Any], trace=None) -> Any:
        """Evaluate using the scorer function and return MLflow Feedback object."""

    @abstractmethod
    def register_scorer(self) -> Any:
        """Register the judge as an MLflow scorer."""

    @abstractmethod
    def optimize(self, labeled_records: List[Any]) -> bool:
        """Optimize the judge using labeled dataset records.

        Args:
            labeled_records: List of labeled records with human feedback labels

        Returns:
            bool: True if optimization succeeded, False otherwise
        """
