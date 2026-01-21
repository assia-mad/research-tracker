import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional


class BaseModel(ABC):
    """
    Abstract Base Class for all data models.
    """

    def __init__(self, id: Optional[str] = None):
        """
        Initialize the base model with timestamps and ID.

        Args:
            id: Optional existing ID. If None, generates a new UUID.
        """
        # Encapsulation: Private attributes
        self._id: str = id or self._generate_id()
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @staticmethod
    def _generate_id() -> str:
        """
        Generate a unique identifier.

        Returns:
            str: A unique UUID string
        """
        return str(uuid.uuid4())

    # Properties for encapsulation - controlled access to private attributes
    @property
    def id(self) -> str:
        """Get the unique identifier."""
        return self._id

    @property
    def created_at(self) -> datetime:
        """Get the creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Get the last update timestamp."""
        return self._updated_at

    def touch(self) -> None:
        """Update the last modified timestamp."""
        self._updated_at = datetime.now()

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary representation.

        This abstract method must be implemented by all subclasses.
        Demonstrates polymorphism - each subclass provides its own implementation.

        Returns:
            Dict[str, Any]: Dictionary representation of the model
        """
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        """
        Create a model instance from a dictionary.

        This abstract class method must be implemented by all subclasses.

        Args:
            data: Dictionary containing model data

        Returns:
            BaseModel: An instance of the model
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate the model data.

        This abstract method must be implemented by all subclasses.

        Returns:
            bool: True if valid, raises ValueError if invalid
        """
        pass

    def _base_dict(self) -> Dict[str, Any]:
        """
        Get base dictionary representation with common fields.

        Returns:
            Dict[str, Any]: Dictionary with id and timestamps
        """
        return {
            "_id": self._id,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"{self.__class__.__name__}(id={self._id})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on ID."""
        if not isinstance(other, BaseModel):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Hash based on ID for use in sets and dicts."""
        return hash(self._id)
