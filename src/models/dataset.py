from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import BaseModel


class DatasetFormat(Enum):
    """Enumeration of supported dataset formats."""

    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    HDF5 = "hdf5"
    IMAGES = "images"
    VIDEO = "video"
    OTHER = "other"


class Dataset(BaseModel):
    """
    Dataset Model - represents a research dataset.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        source: str = "",
        format: DatasetFormat = DatasetFormat.CSV,
        size_mb: float = 0.0,
        num_samples: int = 0,
        features: Optional[List[str]] = None,
        path: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
    ):
        """
        Initialize a Dataset instance.
        """
        super().__init__(id=id)

        self._name: str = name
        self._description: str = description
        self._source: str = source
        self._format: DatasetFormat = (
            format if isinstance(format, DatasetFormat) else DatasetFormat(format)
        )
        self._size_mb: float = size_mb
        self._num_samples: int = num_samples
        self._features: List[str] = features or []
        self._path: str = path
        self._metadata: Dict[str, Any] = metadata or {}

        self.validate()

    # Properties
    @property
    def name(self) -> str:
        """Get dataset name."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Set dataset name."""
        if not value or not value.strip():
            raise ValueError("Dataset name cannot be empty")
        self._name = value.strip()
        self.touch()

    @property
    def description(self) -> str:
        """Get dataset description."""
        return self._description

    @property
    def source(self) -> str:
        """Get dataset source."""
        return self._source

    @property
    def format(self) -> DatasetFormat:
        """Get dataset format."""
        return self._format

    @property
    def size_mb(self) -> float:
        """Get dataset size in MB."""
        return self._size_mb

    @property
    def num_samples(self) -> int:
        """Get number of samples."""
        return self._num_samples

    @property
    def features(self) -> List[str]:
        """Get list of features."""
        return self._features.copy()

    @property
    def path(self) -> str:
        """Get dataset path."""
        return self._path

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get dataset metadata."""
        return self._metadata.copy()

    # Methods
    def add_feature(self, feature: str) -> None:
        """Add a feature to the dataset."""
        if feature and feature not in self._features:
            self._features.append(feature)
            self.touch()

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata field."""
        self._metadata[key] = value
        self.touch()

    def update_stats(self, size_mb: float, num_samples: int) -> None:
        """Update dataset statistics."""
        self._size_mb = size_mb
        self._num_samples = num_samples
        self.touch()

    # Abstract method implementations
    def to_dict(self) -> Dict[str, Any]:
        """Convert dataset to dictionary representation."""
        data = self._base_dict()
        data.update(
            {
                "name": self._name,
                "description": self._description,
                "source": self._source,
                "format": self._format.value,
                "size_mb": self._size_mb,
                "num_samples": self._num_samples,
                "features": self._features,
                "path": self._path,
                "metadata": self._metadata,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dataset":
        """Create a Dataset instance from a dictionary."""
        dataset = cls(
            name=data.get("name", "Untitled"),
            description=data.get("description", ""),
            source=data.get("source", ""),
            format=data.get("format", "csv"),
            size_mb=data.get("size_mb", 0.0),
            num_samples=data.get("num_samples", 0),
            features=data.get("features", []),
            path=data.get("path", ""),
            metadata=data.get("metadata", {}),
            id=data.get("_id"),
        )

        if "created_at" in data:
            dataset._created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            dataset._updated_at = datetime.fromisoformat(data["updated_at"])

        return dataset

    def validate(self) -> bool:
        """Validate dataset data."""
        if not self._name or not self._name.strip():
            raise ValueError("Dataset name is required")

        if self._size_mb < 0:
            raise ValueError("Dataset size cannot be negative")

        if self._num_samples < 0:
            raise ValueError("Number of samples cannot be negative")

        return True

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Dataset(id={self._id}, name='{self._name}', "
            f"format={self._format.value}, samples={self._num_samples})"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self._name} ({self._format.value}, {self._num_samples} samples)"
