from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseModel


class Result(BaseModel):
    """
    Result Model - represents experiment results and metrics.
    """

    def __init__(
        self,
        experiment_id: str,
        run_number: int = 1,
        metrics: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[str]] = None,
        notes: str = "",
        duration_seconds: float = 0.0,
        id: Optional[str] = None,
    ):
        """
        Initialize a Result instance.
        """
        super().__init__(id=id)

        self._experiment_id: str = experiment_id
        self._run_number: int = run_number
        self._metrics: Dict[str, Any] = metrics or {}
        self._artifacts: List[str] = artifacts or []
        self._notes: str = notes
        self._duration_seconds: float = duration_seconds

        self.validate()

    # Properties
    @property
    def experiment_id(self) -> str:
        """Get parent experiment ID."""
        return self._experiment_id

    @property
    def run_number(self) -> int:
        """Get run number."""
        return self._run_number

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get metrics dictionary."""
        return self._metrics.copy()

    @property
    def artifacts(self) -> List[str]:
        """Get list of artifacts."""
        return self._artifacts.copy()

    @property
    def notes(self) -> str:
        """Get notes."""
        return self._notes

    @notes.setter
    def notes(self, value: str) -> None:
        """Set notes."""
        self._notes = value
        self.touch()

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return self._duration_seconds

    # Methods
    def set_metric(self, key: str, value: Any) -> None:
        """Set a metric value."""
        self._metrics[key] = value
        self.touch()

    def add_artifact(self, path: str) -> None:
        """Add an artifact path."""
        if path and path not in self._artifacts:
            self._artifacts.append(path)
            self.touch()

    def set_duration(self, seconds: float) -> None:
        """Set the execution duration."""
        self._duration_seconds = seconds
        self.touch()

    def get_metric(self, key: str, default: Any = None) -> Any:
        """Get a specific metric value."""
        return self._metrics.get(key, default)

    # Common metric helpers
    @property
    def accuracy(self) -> Optional[float]:
        """Get accuracy metric if present."""
        return self._metrics.get("accuracy")

    @property
    def loss(self) -> Optional[float]:
        """Get loss metric if present."""
        return self._metrics.get("loss")

    @property
    def f1_score(self) -> Optional[float]:
        """Get F1 score if present."""
        return self._metrics.get("f1_score")

    # Abstract method implementations
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        data = self._base_dict()
        data.update(
            {
                "experiment_id": self._experiment_id,
                "run_number": self._run_number,
                "metrics": self._metrics,
                "artifacts": self._artifacts,
                "notes": self._notes,
                "duration_seconds": self._duration_seconds,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Result":
        """Create a Result instance from a dictionary."""
        result = cls(
            experiment_id=data.get("experiment_id", ""),
            run_number=data.get("run_number", 1),
            metrics=data.get("metrics", {}),
            artifacts=data.get("artifacts", []),
            notes=data.get("notes", ""),
            duration_seconds=data.get("duration_seconds", 0.0),
            id=data.get("_id"),
        )

        if "created_at" in data:
            result._created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            result._updated_at = datetime.fromisoformat(data["updated_at"])

        return result

    def validate(self) -> bool:
        """Validate result data."""
        if not self._experiment_id:
            raise ValueError("Experiment ID is required")

        if self._run_number < 1:
            raise ValueError("Run number must be positive")

        if self._duration_seconds < 0:
            raise ValueError("Duration cannot be negative")

        return True

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Result(id={self._id}, experiment_id={self._experiment_id}, "
            f"run={self._run_number})"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        metrics_str = ", ".join(f"{k}={v}" for k, v in list(self._metrics.items())[:3])
        return f"Run {self._run_number}: {metrics_str}"
