from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import BaseModel


class ExperimentStatus(Enum):
    """Enumeration of possible experiment statuses."""

    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class Experiment(BaseModel):
    """
    Experiment Model - represents a research experiment.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        author: str = "",
        status: ExperimentStatus = ExperimentStatus.PLANNED,
        tags: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        dataset_id: Optional[str] = None,
        id: Optional[str] = None,
    ):
        """
        Initialize an Experiment instance.
        """
        # Call parent constructor
        super().__init__(id=id)

        # Encapsulated attributes
        self._name: str = name
        self._description: str = description
        self._author: str = author
        self._status: ExperimentStatus = (
            status if isinstance(status, ExperimentStatus) else ExperimentStatus(status)
        )
        self._tags: List[str] = tags or []
        self._parameters: Dict[str, Any] = parameters or {}
        self._metrics: Dict[str, Any] = metrics or {}
        self._dataset_id: Optional[str] = dataset_id

        # Validate on creation
        self.validate()

    # Properties for encapsulation
    @property
    def name(self) -> str:
        """Get experiment name."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Set experiment name with validation."""
        if not value or not value.strip():
            raise ValueError("Experiment name cannot be empty")
        self._name = value.strip()
        self.touch()

    @property
    def description(self) -> str:
        """Get experiment description."""
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        """Set experiment description."""
        self._description = value
        self.touch()

    @property
    def author(self) -> str:
        """Get experiment author."""
        return self._author

    @author.setter
    def author(self, value: str) -> None:
        """Set experiment author."""
        self._author = value
        self.touch()

    @property
    def status(self) -> ExperimentStatus:
        """Get experiment status."""
        return self._status

    @status.setter
    def status(self, value: ExperimentStatus) -> None:
        """Set experiment status."""
        if isinstance(value, str):
            value = ExperimentStatus(value)
        self._status = value
        self.touch()

    @property
    def tags(self) -> List[str]:
        """Get experiment tags."""
        return self._tags.copy()  # Return copy to prevent direct modification

    @property
    def parameters(self) -> Dict[str, Any]:
        """Get experiment parameters."""
        return self._parameters.copy()

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get experiment metrics."""
        return self._metrics.copy()

    @property
    def dataset_id(self) -> Optional[str]:
        """Get associated dataset ID."""
        return self._dataset_id

    # Methods for managing collections
    def add_tag(self, tag: str) -> None:
        """Add a tag to the experiment."""
        if tag and tag not in self._tags:
            self._tags.append(tag)
            self.touch()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the experiment."""
        if tag in self._tags:
            self._tags.remove(tag)
            self.touch()

    def set_parameter(self, key: str, value: Any) -> None:
        """Set an experiment parameter."""
        self._parameters[key] = value
        self.touch()

    def set_metric(self, key: str, value: Any) -> None:
        """Set an experiment metric/result."""
        self._metrics[key] = value
        self.touch()

    def start(self) -> None:
        """Mark the experiment as running."""
        self._status = ExperimentStatus.RUNNING
        self.touch()

    def complete(self, metrics: Optional[Dict[str, Any]] = None) -> None:
        """Mark the experiment as completed with optional final metrics."""
        self._status = ExperimentStatus.COMPLETED
        if metrics:
            self._metrics.update(metrics)
        self.touch()

    def fail(self, error_message: str = "") -> None:
        """Mark the experiment as failed."""
        self._status = ExperimentStatus.FAILED
        if error_message:
            self._metrics["error"] = error_message
        self.touch()

    # Abstract method implementations (Polymorphism)
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert experiment to dictionary representation.

        Overrides abstract method from BaseModel.

        Returns:
            Dict[str, Any]: Dictionary representation
        """
        data = self._base_dict()
        data.update(
            {
                "name": self._name,
                "description": self._description,
                "author": self._author,
                "status": self._status.value,
                "tags": self._tags,
                "parameters": self._parameters,
                "metrics": self._metrics,
                "dataset_id": self._dataset_id,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Experiment":
        """
        Create an Experiment instance from a dictionary.

        Overrides abstract class method from BaseModel.

        Args:
            data: Dictionary containing experiment data

        Returns:
            Experiment: New Experiment instance
        """
        experiment = cls(
            name=data.get("name", "Untitled"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            status=data.get("status", "planned"),
            tags=data.get("tags", []),
            parameters=data.get("parameters", {}),
            metrics=data.get("metrics", {}),
            dataset_id=data.get("dataset_id"),
            id=data.get("_id"),
        )

        # Restore timestamps if present
        if "created_at" in data:
            experiment._created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            experiment._updated_at = datetime.fromisoformat(data["updated_at"])

        return experiment

    def validate(self) -> bool:
        """
        Validate experiment data.

        Overrides abstract method from BaseModel.

        Returns:
            bool: True if valid

        Raises:
            ValueError: If validation fails
        """
        if not self._name or not self._name.strip():
            raise ValueError("Experiment name is required")

        if len(self._name) > 200:
            raise ValueError("Experiment name must be less than 200 characters")

        return True

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Experiment(id={self._id}, name='{self._name}', "
            f"status={self._status.value}, author='{self._author}')"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self._name} ({self._status.value}) by {self._author}"
